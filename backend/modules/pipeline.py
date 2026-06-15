"""
Unified Discovery Pipeline — the single entry point for opportunity discovery.

Replaces the duplicated fetch → normalize → dedup → rank logic that was
scattered across jobs.py, internships.py, and freelancing.py routers.

Flow:
    Source Registry (DB)
    → Capability Router (with fallback chains)
    → Source Adapters (one per source family)
    → Raw Items
    → Normalizer (common schema)
    → Deduper (hash + signature + description similarity)
    → Eligibility Filter
    → Ranker (role-aware, source-independent)
    → Store to Opportunity table
    → (optional) Enrichment (async)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.source import Source
from backend.models.opportunity import Opportunity, FreelanceDetails
from backend.models.user import UserProfile
from backend.models.application import Application
from backend.models.github import RepoEntry, RepoAnalysis

from backend.modules.source_registry import (
    get_enabled_sources_multi,
    update_fetch_status,
)
from backend.modules.capability_router import (
    get_capability_router,
    FetchResult,
)
from backend.modules.normalizer import normalize_many
from backend.modules.deduper import deduplicate, job_fingerprint, job_signature, canonical_fingerprint
from backend.modules.eligibility_filter import filter_eligible
from backend.modules.ranker import rank_jobs
from backend.modules.classifier import classify
from backend.modules.keyword_expander import expand_keywords, flatten_to_query_list


# ─── Pipeline Result ─────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Summary of a pipeline run."""
    fetched: int = 0
    normalized: int = 0
    deduplicated: int = 0
    eligible: int = 0
    filtered_out: int = 0
    ranked: int = 0
    saved: int = 0
    errors: list[str] = field(default_factory=list)
    fetch_results: list[dict] = field(default_factory=list)
    top_items: list[dict] = field(default_factory=list)
    ranked_items: list[dict] = field(default_factory=list)


# ─── Profile & GitHub Helpers ────────────────────────────────────────────────

async def _load_profile(user_id: str, db: AsyncSession) -> dict:
    """Load user profile as a dict."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {
            "skills": [], "projects": [], "preferred_roles": [],
            "location_rule": {}, "resume_summary": "",
            "preferred_companies": [], "graduation_year": None,
        }
    return {
        "name": "",
        "skills": profile.skills or [],
        "projects": profile.projects or [],
        "research_areas": getattr(profile, "research_areas", []) or [],
        "preferred_roles": profile.preferred_roles or [],
        "location_rule": profile.location_rule or {},
        "resume_summary": profile.resume_summary or "",
        "preferred_companies": getattr(profile, "preferred_companies", []) or [],
        "graduation_year": getattr(profile, "graduation_year", None),
    }


async def _load_github_repos(user_id: str, db: AsyncSession) -> list[dict]:
    """Load GitHub repos with analysis signals for project matching."""
    try:
        repos_result = await db.execute(
            select(RepoEntry).where(
                RepoEntry.user_id == user_id,
                RepoEntry.is_archived == False,
            )
        )
        repos = repos_result.scalars().all()
        if not repos:
            return []

        repo_ids = [r.id for r in repos]
        analyses_result = await db.execute(
            select(RepoAnalysis).where(RepoAnalysis.repo_id.in_(repo_ids))
        )
        analyses_map = {a.repo_id: a for a in analyses_result.scalars().all()}

        return [
            {
                "id": repo.id,
                "name": repo.name,
                "description": repo.description,
                "language": repo.language,
                "languages_all": repo.languages_all or {},
                "topics": repo.topics or [],
                "analysis_signals": (
                    analyses_map[repo.id].analysis_signals
                    if repo.id in analyses_map else {}
                ),
                "readme_content": (
                    analyses_map[repo.id].readme_content
                    if repo.id in analyses_map else None
                ),
            }
            for repo in repos
        ]
    except Exception as e:
        logger.warning(f"[Pipeline] GitHub repos load failed: {e}")
        return []


async def _get_applied_fingerprints(user_id: str, db: AsyncSession) -> tuple[set[str], set[str]]:
    """Get sets of already-applied fingerprints and URLs."""
    result = await db.execute(
        select(Application.job_fingerprint, Application.canonical_url)
        .where(Application.user_id == user_id)
    )
    rows = result.fetchall()
    fingerprints = {r[0] for r in rows if r[0]}
    urls = {r[1] for r in rows if r[1]}
    return fingerprints, urls


# ─── Source Group → Opportunity Type Mapping ─────────────────────────────────

SOURCE_GROUP_TO_OPP_TYPE = {
    "internship": "internship",
    "startup": "internship",
    "remote": "internship",
    "notice": "notice",
    "freelance": "freelance",
}


# ─── Main Pipeline ───────────────────────────────────────────────────────────

async def run_pipeline(
    user_id: str,
    source_groups: list[str],
    db: AsyncSession,
    *,
    force_refresh: bool = False,
    enrich: bool = False,
    limit: int = 50,
) -> PipelineResult:
    """
    Run the full discovery pipeline:
      Source Registry → Capability Router → Adapters → Normalize
      → Dedup → Eligibility Filter → Rank → Store → (Enrich)
    """
    result = PipelineResult()

    # 1. Load user profile and GitHub repos
    profile_dict = await _load_profile(user_id, db)
    github_repos = await _load_github_repos(user_id, db)
    applied_fps, applied_urls = await _get_applied_fingerprints(user_id, db)

    # 2. Build search keywords from profile
    keyword_groups = expand_keywords(
        skills=profile_dict.get("skills") or [],
        preferred_roles=profile_dict.get("preferred_roles") or [],
        max_groups=6,
    )
    keywords = flatten_to_query_list(keyword_groups)
    if not keywords:
        keywords = (profile_dict.get("preferred_roles") or [])[:3] + \
                   (profile_dict.get("skills") or [])[:3]
    if not keywords:
        keywords = ["internship", "python", "web development"]

    # Determine search locations
    location_rule = profile_dict.get("location_rule") or {}
    search_locations = []
    if location_rule.get("remote_allowed", False):
        search_locations.append("Remote")
    offline_allowed = location_rule.get("offline_allowed", [])
    if offline_allowed:
        search_locations.append(offline_allowed[0])
    if not search_locations:
        search_locations.append("India")

    logger.info(
        f"[Pipeline] Running for user={user_id}, groups={source_groups}, "
        f"keywords={keywords[:5]}, locations={search_locations}"
    )

    # 3. Get enabled sources for requested groups
    sources = await get_enabled_sources_multi(db, source_groups)
    if not sources:
        result.errors.append(f"No enabled sources found for groups: {source_groups}")
        return result

    logger.info(f"[Pipeline] {len(sources)} enabled sources: {[s.name for s in sources]}")

    # 4. Fetch from all sources via CapabilityRouter
    router = get_capability_router()
    all_raw = []

    for loc in search_locations:
        fetch_results = await router.fetch_sources(
            sources=sources,
            keywords=keywords,
            location=loc,
            applied_fingerprints=applied_fps,
            applied_urls=applied_urls,
            force_refresh=force_refresh,
            max_concurrency=5,
        )

        for fr in fetch_results:
            result.fetch_results.append({
                "source": fr.source_name,
                "status": fr.status,
                "count": len(fr.items),
                "mode_used": fr.mode_used,
                "duration_ms": fr.duration_ms,
                "error": fr.error,
            })
            all_raw.extend(fr.items)

            # Update source fetch status in DB
            await update_fetch_status(
                db, fr.source_name, fr.status, count=len(fr.items)
            )

    result.fetched = len(all_raw)

    if not all_raw:
        await db.commit()
        return result

    # 5. Normalize
    normalized = normalize_many(all_raw)
    result.normalized = len(normalized)

    # 6. Deduplicate against existing opportunities
    existing_result = await db.execute(
        select(Opportunity.content_hash, Opportunity.title, Opportunity.organization, Opportunity.location)
    )
    existing_items = existing_result.fetchall()
    existing_hashes = {row[0] for row in existing_items if row[0]}
    existing_signatures = {
        job_signature({
            "title": row[1],
            "company": row[2],
            "organization": row[2],
            "location": row[3],
        })
        for row in existing_items
    }

    unique = deduplicate(
        normalized,
        existing_hashes=existing_hashes,
        existing_signatures=existing_signatures,
        use_description_similarity=True,
        similarity_threshold=0.85,
    )
    result.deduplicated = len(unique)

    # 7. Filter out already-applied
    unique = [
        item for item in unique
        if canonical_fingerprint({
            "title": item.get("title"),
            "company": item.get("company") or item.get("organization"),
            "location": item.get("location"),
            "apply_link": item.get("apply_link"),
        }) not in applied_fps
    ]

    # 8. Classify opportunity type
    for item in unique:
        opp_type = classify(item, item.get("source", ""))
        item["opportunity_type"] = opp_type

    # 9. Eligibility filter
    # For freelance items, skip experience/duration checks
    internship_items = [i for i in unique if i.get("opportunity_type") != "freelance"]
    freelance_items = [i for i in unique if i.get("opportunity_type") == "freelance"]

    eligible_intern, filtered_intern = filter_eligible(
        internship_items, profile_dict,
        check_experience=True,
        check_duration=True,
        check_location=True,
    )
    eligible_freelance, filtered_freelance = filter_eligible(
        freelance_items, profile_dict,
        check_experience=False,
        check_duration=False,
        check_location=False,
    )

    eligible = eligible_intern + eligible_freelance
    result.eligible = len(eligible)
    result.filtered_out = len(filtered_intern) + len(filtered_freelance)

    # 10. Rank (fit score)
    ranked = rank_jobs(eligible, profile_dict, github_repos)

    # 10b. Competition estimation
    from backend.modules.competition_estimator import estimate_competition
    for item in ranked:
        comp = estimate_competition(item)
        item["competition_score"] = comp["competition_score"]
        item["competition_label"] = comp["competition_label"]
        item["competition_reasons"] = comp["competition_reasons"]
        
        # Combined opportunity score (0.6 * Fit + 0.4 * Competition Advantage)
        fit = item.get("score", 0)
        item["opportunity_score"] = round(0.6 * fit + 0.4 * comp["competition_score"], 4)

    # Re-sort by opportunity_score
    ranked.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
    result.ranked = len(ranked)

    # 11. Enrich (optional, async)
    if enrich and ranked:
        try:
            from backend.modules.enrichment import enrich_batch
            # Only enrich top items to keep it fast
            top_to_enrich = ranked[:min(limit, 20)]
            ranked[:len(top_to_enrich)] = await enrich_batch(
                top_to_enrich, max_concurrency=3, timeout=10
            )
        except Exception as e:
            logger.warning(f"[Pipeline] Enrichment failed: {e}")

    # 12. Store as Opportunity rows
    saved = 0
    for item in ranked[:limit]:
        source_name = item.get("source", "Unknown")

        # Determine source_group from source name
        source_group = None
        for src in sources:
            if src.name == source_name:
                source_group = src.source_group
                break

        opp = Opportunity(
            id=item.get("id") or None,
            opportunity_type=item.get("opportunity_type", "internship"),
            source=source_name,
            source_group=source_group,
            title=item.get("title", "Untitled"),
            organization=item.get("organization") or item.get("company", "Unknown"),
            location=item.get("location"),
            mode=item.get("mode"),
            description=item.get("description"),
            apply_link=item.get("apply_link"),
            canonical_url=item.get("canonical_url"),
            raw_text=item.get("raw_text") or item.get("description"),
            fingerprint=item.get("fingerprint"),
            content_hash=item.get("content_hash"),
            score=item.get("score"),
            score_breakdown=item.get("score_breakdown"),
            matched_skills=item.get("matched_skills"),
            matched_projects=item.get("matched_projects"),
            competition_score=item.get("competition_score"),
            competition_label=item.get("competition_label"),
            competition_reasons=item.get("competition_reasons"),
            opportunity_score=item.get("opportunity_score"),
            status="new",
            posted_at=item.get("posted_date") or item.get("posted_at"),
            enriched_at=item.get("enriched_at"),
            eligibility_text=item.get("eligibility_text"),
            eligibility_status=item.get("eligibility_status"),
            deadline=item.get("deadline"),
            stipend=item.get("stipend"),
        )
        db.add(opp)

        # Store freelance details if applicable
        if item.get("opportunity_type") == "freelance" and any(
            item.get(k) is not None
            for k in ("budget_min", "budget_max", "client_rating")
        ):
            details = FreelanceDetails(
                opportunity_id=opp.id,
                budget_min=item.get("budget_min"),
                budget_max=item.get("budget_max"),
                budget_type=item.get("budget_type"),
                currency=item.get("currency", "USD"),
                deliverables=item.get("deliverables"),
                deadline=item.get("deadline"),
                client_type=item.get("client_type"),
                client_rating=item.get("client_rating"),
                client_reviews_count=item.get("client_reviews_count"),
                required_skills=item.get("required_skills"),
                project_length=item.get("project_length"),
                payment_verified=item.get("payment_verified", False),
                delivery_time_days=item.get("delivery_time_days"),
                remote_only=item.get("remote_only", True),
            )
            db.add(details)

        saved += 1

    await db.commit()
    result.saved = saved

    # Top items for API response
    result.ranked_items = ranked
    result.top_items = []
    for r in ranked[:5]:
        source_name = r.get("source", "Unknown")
        sg = None
        for src in sources:
            if src.name == source_name:
                sg = src.source_group
                break
        result.top_items.append({
            "title": r.get("title"),
            "organization": r.get("organization") or r.get("company"),
            "source": source_name,
            "score": r.get("score"),
            "competition_label": r.get("competition_label"),
            "opportunity_score": r.get("opportunity_score"),
            "source_group": sg,
            "opportunity_type": r.get("opportunity_type", "internship"),
        })

    logger.info(
        f"[Pipeline] Complete: fetched={result.fetched} normalized={result.normalized} "
        f"deduped={result.deduplicated} eligible={result.eligible} "
        f"ranked={result.ranked} saved={result.saved}"
    )

    return result
