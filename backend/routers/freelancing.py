"""
Freelancing Router — Lane 3 of the three-lane opportunity engine.

Handles fetch, rank, detail, and status tracking for freelance gigs.
Uses separate scoring brain (freelance_scorer) from Ranked Jobs (ranker).
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models.opportunity import Opportunity, FreelanceDetails, ApplicationTracker
from backend.models.user import UserProfile
from backend.models.github import RepoEntry, RepoAnalysis
from backend.modules.normalizer import normalize_many
from backend.modules.deduper import deduplicate
from backend.modules.classifier import classify
from backend.modules.freelance_scorer import rank_freelance
from backend.modules.fetchers import (
    UpworkFetcher,
    FiverrFetcher,
    FreelancerComFetcher,
    GuruFetcher,
    ToptalFetcher,
    ContraFetcher,
    PeoplePerHourFetcher,
    ArcFetcher,
    TuringFetcher,
    LemonioFetcher,
    GunioFetcher,
    NinetyNineDesignsFetcher,
    DribbbleFetcher,
    BehanceFetcher,
)
from loguru import logger

router = APIRouter(prefix="/freelance", tags=["Freelancing"])

# ─── Fetcher Registry ───────────────────────────────────────────────────────

FETCHERS = {
    "upwork":       UpworkFetcher,
    "fiverr":       FiverrFetcher,
    "freelancer":   FreelancerComFetcher,
    "guru":         GuruFetcher,
    "toptal":       ToptalFetcher,
    "contra":       ContraFetcher,
    "peopleperhour": PeoplePerHourFetcher,
    "arc":          ArcFetcher,
    "turing":       TuringFetcher,
    "lemonio":      LemonioFetcher,
    "gunio":        GunioFetcher,
    "99designs":    NinetyNineDesignsFetcher,
    "dribbble":     DribbbleFetcher,
    "behance":      BehanceFetcher,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _load_profile(user_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return {
            "skills": [], "projects": [], "preferred_roles": [],
            "location_rule": {}, "resume_summary": "",
        }
    return {
        "skills": profile.skills or [],
        "projects": profile.projects or [],
        "preferred_roles": profile.preferred_roles or [],
        "location_rule": profile.location_rule or {},
        "resume_summary": profile.resume_summary or "",
    }


async def _load_github_repos(user_id: str, db: AsyncSession) -> list[dict]:
    repos_result = await db.execute(
        select(RepoEntry).where(RepoEntry.user_id == user_id, RepoEntry.is_archived == False)
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
            "name": repo.name,
            "description": repo.description,
            "language": repo.language,
            "languages_all": repo.languages_all or {},
            "topics": repo.topics or [],
            "analysis_signals": analyses_map.get(repo.id, None) and analyses_map[repo.id].analysis_signals or {},
            "readme_content": analyses_map.get(repo.id, None) and analyses_map[repo.id].readme_content or None,
        }
        for repo in repos
    ]


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/fetch")
async def fetch_freelance_jobs(
    user_id: str,
    sources: list[str] = Query(default=["upwork", "freelancer"]),
    db: AsyncSession = Depends(get_db),
):
    """Fetch, normalize, dedup, classify, score, and store freelance gigs."""
    profile_dict = await _load_profile(user_id, db)
    github_repos = await _load_github_repos(user_id, db)

    # Build keywords from profile
    keywords = (profile_dict.get("preferred_roles") or [])[:3] + (profile_dict.get("skills") or [])[:5]
    if not keywords:
        keywords = ["python", "web development", "ai"]

    # Fetch from selected sources
    import asyncio
    all_raw = []
    fetch_tasks = []
    for source in sources:
        cls = FETCHERS.get(source.lower())
        if not cls:
            continue
        fetcher = cls()
        fetch_tasks.append(fetcher.fetch(keywords))

    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            logger.warning(f"[Freelance] Fetch error: {res}")
            continue
        all_raw.extend(res)

    # Normalize
    normalized = normalize_many(all_raw)

    # Dedup against existing opportunities
    existing_result = await db.execute(
        select(Opportunity.content_hash).where(Opportunity.opportunity_type == "freelance")
    )
    existing_hashes = {row[0] for row in existing_result.fetchall() if row[0]}
    unique = deduplicate(normalized, existing_hashes)

    # Score and store
    # Classify (should all be freelance, but classifier confirms)
    freelance_items = [item for item in unique if classify(item, item.get("source", "")) == "freelance"]

    # Rank using freelance scoring engine
    ranked = rank_freelance(freelance_items, profile_dict, github_repos)

    # Store in DB
    saved = 0
    for item in ranked:
        opp = Opportunity(
            id=item["id"],
            opportunity_type="freelance",
            source=item.get("source", "Unknown"),
            source_group="freelance",
            title=item.get("title", "Untitled"),
            organization=item.get("organization") or item.get("company", "Unknown"),
            description=item.get("description"),
            apply_link=item.get("apply_link"),
            raw_text=item.get("description"),
            score=item.get("score"),
            score_breakdown=item.get("score_breakdown"),
            content_hash=item.get("content_hash"),
            posted_at=item.get("posted_date"),
        )
        db.add(opp)

        # Store freelance-specific details
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

    logger.info(f"[Freelance] Fetched {len(all_raw)} raw → {len(unique)} unique → {len(ranked)} ranked → {saved} saved")

    return {
        "fetched": len(all_raw),
        "unique": len(unique),
        "ranked": len(ranked),
        "saved": saved,
        "top_5": [
            {
                "title": r.get("title"),
                "organization": r.get("organization") or r.get("company"),
                "score": r.get("score"),
                "source": r.get("source"),
            }
            for r in ranked[:5]
        ],
    }


@router.get("/ranked/{user_id}")
async def get_ranked_freelance(
    user_id: str,
    limit: int = 30,
    sources: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """Get ranked freelance gigs for a user."""
    profile_dict = await _load_profile(user_id, db)
    github_repos = await _load_github_repos(user_id, db)

    # Build query
    query = select(Opportunity).where(Opportunity.opportunity_type == "freelance")

    if sources:
        source_names = [s.capitalize() for s in sources]
        query = query.where(Opportunity.source.in_(source_names + sources))

    result = await db.execute(query.order_by(Opportunity.fetched_at.desc()).limit(200))
    opportunities = result.scalars().all()

    # Re-score with current profile
    opp_dicts = []
    for opp in opportunities:
        # Load freelance details
        fd_result = await db.execute(
            select(FreelanceDetails).where(FreelanceDetails.opportunity_id == opp.id)
        )
        fd = fd_result.scalar_one_or_none()

        d = {
            "id": opp.id,
            "title": opp.title,
            "organization": opp.organization,
            "description": opp.description,
            "apply_link": opp.apply_link,
            "source": opp.source,
            "posted_at": opp.posted_at,
            "status": opp.status,
        }
        if fd:
            d.update({
                "budget_min": fd.budget_min,
                "budget_max": fd.budget_max,
                "budget_type": fd.budget_type,
                "currency": fd.currency,
                "deliverables": fd.deliverables,
                "deadline": fd.deadline,
                "client_type": fd.client_type,
                "client_rating": fd.client_rating,
                "client_reviews_count": fd.client_reviews_count,
                "required_skills": fd.required_skills,
                "project_length": fd.project_length,
                "payment_verified": fd.payment_verified,
                "delivery_time_days": fd.delivery_time_days,
                "remote_only": fd.remote_only,
            })
        opp_dicts.append(d)

    ranked = rank_freelance(opp_dicts, profile_dict, github_repos)

    # Update scores in DB
    for item in ranked:
        opp_id = item["id"]
        await db.execute(
            select(Opportunity).where(Opportunity.id == opp_id)
        )
        # Simple approach: we already have the scores in the dict
        pass

    # Check tracking status for each
    tracking_result = await db.execute(
        select(ApplicationTracker).where(
            ApplicationTracker.user_id == user_id,
            ApplicationTracker.lane_type == "freelance",
        )
    )
    tracked = {t.opportunity_id: t.status for t in tracking_result.scalars().all()}

    out = []
    for item in ranked[:limit]:
        budget_display = _format_budget(
            item.get("budget_min"), item.get("budget_max"),
            item.get("budget_type"), item.get("currency", "USD"),
        )
        out.append({
            "id": item["id"],
            "title": item["title"],
            "organization": item.get("organization"),
            "source": item.get("source"),
            "apply_link": item.get("apply_link"),
            "score": item.get("score"),
            "score_breakdown": item.get("score_breakdown"),
            "matched_skills": item.get("matched_skills", []),
            "matched_projects": item.get("matched_projects", []),
            "budget_display": budget_display,
            "budget_min": item.get("budget_min"),
            "budget_max": item.get("budget_max"),
            "budget_type": item.get("budget_type"),
            "currency": item.get("currency", "USD"),
            "required_skills": item.get("required_skills") or [],
            "client_rating": item.get("client_rating"),
            "payment_verified": item.get("payment_verified", False),
            "delivery_time_days": item.get("delivery_time_days"),
            "deadline": item.get("deadline").isoformat() if isinstance(item.get("deadline"), datetime) else item.get("deadline"),
            "remote_only": item.get("remote_only", True),
            "status": tracked.get(item["id"], item.get("status", "new")),
        })

    return out


@router.get("/{opportunity_id}")
async def get_freelance_detail(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    """Get full detail for a freelance gig including FreelanceDetails."""
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    fd_result = await db.execute(
        select(FreelanceDetails).where(FreelanceDetails.opportunity_id == opportunity_id)
    )
    fd = fd_result.scalar_one_or_none()

    return {
        "id": opp.id,
        "title": opp.title,
        "organization": opp.organization,
        "description": opp.description,
        "raw_text": opp.raw_text,
        "apply_link": opp.apply_link,
        "source": opp.source,
        "score": opp.score,
        "score_breakdown": opp.score_breakdown,
        "status": opp.status,
        "posted_at": opp.posted_at,
        "fetched_at": opp.fetched_at,
        "freelance_details": {
            "budget_min": fd.budget_min,
            "budget_max": fd.budget_max,
            "budget_type": fd.budget_type,
            "currency": fd.currency,
            "deliverables": fd.deliverables,
            "deadline": fd.deadline,
            "client_type": fd.client_type,
            "client_rating": fd.client_rating,
            "client_reviews_count": fd.client_reviews_count,
            "required_skills": fd.required_skills,
            "project_length": fd.project_length,
            "payment_verified": fd.payment_verified,
            "delivery_time_days": fd.delivery_time_days,
            "remote_only": fd.remote_only,
        } if fd else None,
    }


class StatusUpdateRequest(BaseModel):
    status: str  # saved / applied / in_progress / completed / dismissed
    notes: str | None = None


@router.post("/{opportunity_id}/status")
async def update_freelance_status(
    opportunity_id: str,
    user_id: str,
    req: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save / apply / mark in-progress / complete / dismiss a freelance gig."""
    VALID = {"saved", "applied", "in_progress", "completed", "dismissed"}
    if req.status not in VALID:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID}")

    # Check opportunity exists
    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    # Upsert tracker
    existing = await db.execute(
        select(ApplicationTracker).where(
            ApplicationTracker.opportunity_id == opportunity_id,
            ApplicationTracker.user_id == user_id,
        )
    )
    tracker = existing.scalar_one_or_none()

    now = datetime.utcnow()
    if tracker:
        tracker.status = req.status
        tracker.notes = req.notes or tracker.notes
        if req.status == "saved":
            tracker.saved_at = now
        elif req.status == "applied":
            tracker.applied_at = now
        elif req.status == "in_progress":
            tracker.in_progress_at = now
        elif req.status == "completed":
            tracker.completed_at = now
    else:
        tracker = ApplicationTracker(
            opportunity_id=opportunity_id,
            user_id=user_id,
            lane_type="freelance",
            status=req.status,
            notes=req.notes,
            saved_at=now if req.status == "saved" else None,
            applied_at=now if req.status == "applied" else None,
            in_progress_at=now if req.status == "in_progress" else None,
            completed_at=now if req.status == "completed" else None,
        )
        db.add(tracker)

    # Also update the opportunity's status field
    opp.status = req.status
    await db.commit()

    return {"id": tracker.id, "status": tracker.status, "opportunity_id": opportunity_id}


@router.get("/stats/{user_id}")
async def get_freelance_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get freelance lane statistics."""
    total = await db.execute(
        select(func.count(Opportunity.id)).where(Opportunity.opportunity_type == "freelance")
    )
    saved = await db.execute(
        select(func.count(ApplicationTracker.id)).where(
            ApplicationTracker.user_id == user_id,
            ApplicationTracker.lane_type == "freelance",
            ApplicationTracker.status == "saved",
        )
    )
    applied = await db.execute(
        select(func.count(ApplicationTracker.id)).where(
            ApplicationTracker.user_id == user_id,
            ApplicationTracker.lane_type == "freelance",
            ApplicationTracker.status == "applied",
        )
    )
    in_progress = await db.execute(
        select(func.count(ApplicationTracker.id)).where(
            ApplicationTracker.user_id == user_id,
            ApplicationTracker.lane_type == "freelance",
            ApplicationTracker.status == "in_progress",
        )
    )

    return {
        "total_gigs": total.scalar() or 0,
        "saved": saved.scalar() or 0,
        "applied": applied.scalar() or 0,
        "in_progress": in_progress.scalar() or 0,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _format_budget(
    budget_min: float | None,
    budget_max: float | None,
    budget_type: str | None,
    currency: str = "USD",
) -> str:
    """Format budget for display."""
    sym = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£"}.get(currency, currency + " ")

    if budget_min is None and budget_max is None:
        return "Budget not specified"

    suffix = "/hr" if budget_type == "hourly" else " Fixed"

    if budget_min and budget_max and budget_min != budget_max:
        return f"{sym}{budget_min:,.0f}–{sym}{budget_max:,.0f}{suffix}"
    elif budget_max:
        return f"{sym}{budget_max:,.0f}{suffix}"
    elif budget_min:
        return f"{sym}{budget_min:,.0f}+{suffix}"
    return "Budget not specified"
