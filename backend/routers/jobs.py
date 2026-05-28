from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.database import get_db
from backend.models import JobPost, JobMatch, UserProfile, Application
from backend.models.github import RepoEntry, RepoAnalysis
from backend.modules.fetchers import (
    InternshalaFetcher,
    IndeedFetcher,
    LinkedInFetcher,
    FounditFetcher,
    FreshersworldFetcher,
    CutshortFetcher,
    WellfoundFetcher,
    WorkAtAStartupFetcher,
)
from backend.modules.normalizer import normalize_many
from backend.modules.deduper import deduplicate, job_fingerprint, job_signature
from backend.modules.ranker import rank_jobs, _is_expired, _experience_filter, _duration_filter
from backend.modules.keyword_expander import expand_keywords, flatten_to_query_list
from loguru import logger

router = APIRouter(prefix="/jobs", tags=["Jobs"])

FETCHERS = {
    "internshala": InternshalaFetcher,
    "indeed": IndeedFetcher,
    "naukri": LinkedInFetcher,   # LinkedIn replaces blocked Naukri
    "foundit": FounditFetcher,
    "freshersworld": FreshersworldFetcher,
    "cutshort": CutshortFetcher,
    "wellfound": WellfoundFetcher,
    "workatastartup": WorkAtAStartupFetcher,
}


@router.post("/fetch")
async def fetch_jobs(
    user_id: str,
    sources: list[str] = Query(default=["internshala"]),
    force_refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found. Parse resume first.")

    profile_dict = {
        "name": "",
        "skills": profile.skills or [],
        "projects": profile.projects or [],
        "research_areas": profile.research_areas or [],
        "preferred_roles": profile.preferred_roles or [],
        "location_rule": profile.location_rule or {},
        "resume_summary": profile.resume_summary or "",
    }

    # Build expanded keyword list using the domain-tree expander.
    # This widens the search net: a GenAI candidate will also fetch NLP/CV/ML roles.
    keyword_groups = expand_keywords(
        skills=profile.skills or [],
        preferred_roles=profile.preferred_roles or [],
        max_groups=6,
    )
    keywords = flatten_to_query_list(keyword_groups)
    if not keywords:
        # Fallback to the old narrow approach if expander returns nothing
        keywords = (profile.preferred_roles or [])[:3] + (profile.skills or [])[:3]
    logger.info(f"[Jobs] Using {len(keywords)} expanded keywords for user {user_id}: {keywords[:6]}")
    all_raw = []

    # Determine locations to search
    location_rule = profile.location_rule or {}
    search_locations = []
    
    if location_rule.get("remote_allowed", False):
        search_locations.append("Remote")
        
    offline_allowed = location_rule.get("offline_allowed", [])
    if offline_allowed:
        search_locations.append(offline_allowed[0])
        
    if not search_locations:
        search_locations.append("India")

    # Get applied history
    applied_history = await db.execute(
        select(Application.job_fingerprint, Application.canonical_url).where(Application.user_id == user_id)
    )
    rows = applied_history.fetchall()
    applied_fingerprints = {r[0] for r in rows if r[0]}
    applied_urls = {r[1] for r in rows if r[1]}

    # Fetch concurrently
    import asyncio
    fetch_tasks = []
    for source in sources:
        cls = FETCHERS.get(source.lower())
        if not cls:
            continue
        fetcher = cls()
        for loc in search_locations:
            fetch_tasks.append(
                fetcher.fetch(
                    keywords,
                    location=loc,
                    applied_fingerprints=applied_fingerprints,
                    applied_urls=applied_urls,
                    force_refresh=force_refresh,
                )
            )
            
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            logger.warning(f"[Jobs] Fetch failed: {res}")
            continue
        all_raw.extend(res)

    normalised = normalize_many(all_raw)

    existing_result = await db.execute(select(JobPost.content_hash, JobPost.title, JobPost.company, JobPost.location))
    existing_items = [row for row in existing_result.fetchall()]

    # --- Clean up stale entries with broken/unknown titles ---
    # These were created by previously broken scrapers (e.g. Internshala selector changes)
    # and block deduplication of new valid entries with the same company.
    stale_ids_result = await db.execute(
        select(JobPost.id).where(
            (JobPost.title == "Unknown") | (JobPost.title == None) | (JobPost.title == "")
        )
    )
    stale_ids = [row[0] for row in stale_ids_result.fetchall()]
    if stale_ids:
        # Remove matches referencing stale jobs
        await db.execute(delete(JobMatch).where(JobMatch.job_id.in_(stale_ids)))
        # Remove the stale job posts themselves
        await db.execute(delete(JobPost).where(JobPost.id.in_(stale_ids)))
        await db.commit()
        logger.info(f"[Jobs] Cleaned up {len(stale_ids)} stale entries with missing/unknown titles")
        # Re-fetch existing items after cleanup
        existing_result = await db.execute(select(JobPost.content_hash, JobPost.title, JobPost.company, JobPost.location))
        existing_items = [row for row in existing_result.fetchall()]

    existing_hashes = {row[0] for row in existing_items if row[0]}
    existing_signatures = {
        job_signature({"title": row[1], "company": row[2], "location": row[3]})
        for row in existing_items
    }

    unique = deduplicate(normalised, existing_hashes, existing_signatures)

    applied_fps_result = await db.execute(
        select(Application.job_fingerprint).where(Application.user_id == user_id)
    )
    # We already have applied_fingerprints from earlier, but let's re-fetch if needed
    applied_fingerprints_check = {row[0] for row in applied_fps_result.fetchall() if row[0]}

    for job_data in unique:
        job = JobPost(
            id=job_data["id"],
            source=job_data["source"],
            title=job_data["title"],
            company=job_data["company"],
            location=job_data.get("location"),
            mode=job_data.get("mode"),
            description=job_data.get("description"),
            apply_link=job_data.get("apply_link"),
            posted_date=job_data.get("posted_date"),
            content_hash=job_data.get("content_hash"),
        )
        db.add(job)

    await db.commit()

    # Fetch GitHub repos for project matching 
    github_repos = []
    try:
        repos_result = await db.execute(
            select(RepoEntry).where(
                RepoEntry.user_id == user_id,
                RepoEntry.is_archived == False,
            )
        )
        repos = repos_result.scalars().all()
        
        # Get analysis signals for each repo
        repo_ids = [r.id for r in repos]
        if repo_ids:
            analyses_result = await db.execute(
                select(RepoAnalysis).where(RepoAnalysis.repo_id.in_(repo_ids))
            )
            analyses_map = {a.repo_id: a for a in analyses_result.scalars().all()}
            
            for repo in repos:
                analysis = analyses_map.get(repo.id)
                github_repos.append({
                    "id": repo.id,
                    "name": repo.name,
                    "description": repo.description,
                    "language": repo.language,
                    "languages_all": repo.languages_all or {},
                    "topics": repo.topics or [],
                    "analysis_signals": analysis.analysis_signals if analysis else {},
                    # Include README content for deep semantic matching
                    "readme_content": analysis.readme_content if analysis else None,
                })
    except Exception as e:
        
        pass

    # Re score ALL existing jobs for this user so that profile changes always reflect correctly
    all_jobs_result = await db.execute(select(JobPost))
    all_jobs = all_jobs_result.scalars().all()
    from backend.modules.deduper import canonical_fingerprint
    
    all_jobs_dicts = [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "mode": j.mode,
            "description": j.description,
            "apply_link": j.apply_link,
            "posted_date": j.posted_date,
            "source": j.source,
        }
        for j in all_jobs
        if canonical_fingerprint({
            "title": j.title, 
            "company": j.company,
            "location": j.location,
            "apply_link": j.apply_link
        }) not in applied_fingerprints_check
    ]

    ranked = rank_jobs(all_jobs_dicts, profile_dict, github_repos)

    # delete existing matches for this user then re-insert with fresh scores
    await db.execute(delete(JobMatch).where(JobMatch.user_id == user_id))

    for job_data in ranked:
        match = JobMatch(
            user_id=user_id,
            job_id=job_data["id"],
            score=job_data.get("score"),
            score_breakdown=job_data.get("score_breakdown"),
            matched_skills=job_data.get("matched_skills", []),
            matched_projects=job_data.get("matched_projects", []),
        )
        db.add(match)

    await db.commit()

    return {
        "fetched": len(all_raw),
        "new_unique": len(unique),
        "ranked": len(ranked),
        "top_5": ranked[:5],
    }


@router.get("/ranked/{user_id}")
async def get_ranked_jobs(
    user_id: str,
    limit: int = 20,
    include_applied: bool = False,
    sources: list[str] = Query(default=["internshala", "indeed", "naukri"]),
    db: AsyncSession = Depends(get_db),
):
    # Map frontend source IDs to backend source names stored in DB
    SOURCE_NAME_MAP = {
        "internshala": "Internshala",
        "indeed": "Indeed",
        "naukri": "LinkedIn",   # LinkedIn replaces blocked Naukri
        "linkedin": "LinkedIn",
    }
    db_sources = [SOURCE_NAME_MAP.get(s.lower(), s) for s in sources]

    # Load user profile to get location_rule for filtering
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_row = profile_result.scalar_one_or_none()
    location_rule = (profile_row.location_rule or {}) if profile_row else {}
    allowed_cities = [loc.lower() for loc in (location_rule.get("offline_allowed") or [])]

    applied_job_ids: set[str] = set()
    if not include_applied:
        applied_result = await db.execute(
            select(Application.job_id).where(Application.user_id == user_id)
        )
        applied_job_ids = {row[0] for row in applied_result.fetchall() if row[0]}

    query = (
        select(JobMatch, JobPost)
        .join(JobPost, JobMatch.job_id == JobPost.id)
        .where(JobMatch.user_id == user_id)
        .where(JobPost.source.in_(db_sources))
        .order_by(JobMatch.score.desc())
        .limit(limit * 3)  # fetch extra to account for location filtering
    )
    result = await db.execute(query)
    rows = result.fetchall()

    seen_signatures: set[str] = set()
    ranked_jobs: list[dict] = []
    expired_ids: list[str] = []

    for match, job in rows:
        if not include_applied and job.id in applied_job_ids:
            continue

        signature = job_signature({"title": job.title, "company": job.company, "location": job.location})
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "mode": job.mode,
            "description": job.description,
            "posted_date": job.posted_date,
        }

        # --- Read-time filters ---
        # Drop jobs with missing/unknown titles
        title_check = (job.title or "").strip().lower()
        if not title_check or title_check == "unknown":
            expired_ids.append(job.id)
            continue

        # Expired, experience, duration
        if _is_expired(job_dict):
            expired_ids.append(job.id)
            continue
        if not _experience_filter(job_dict):
            expired_ids.append(job.id)
            continue
        if not _duration_filter(job_dict):
            expired_ids.append(job.id)
            continue

        # --- Location filter: remote always passes; offline must match allowed cities ---
        if allowed_cities:
            from backend.modules.ranker import _is_remote
            if not _is_remote(job_dict):
                loc = (job.location or "").lower()
                if not any(a in loc or loc in a for a in allowed_cities):
                    expired_ids.append(job.id)
                    continue

        ranked_jobs.append(
            {
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "mode": job.mode,
                "apply_link": job.apply_link,
                "source": job.source,
                "score": match.score,
                "score_breakdown": match.score_breakdown,
                "matched_skills": match.matched_skills or [],
                "matched_projects": match.matched_projects or [],
                "is_applied": job.id in applied_job_ids,
            }
        )

        if len(ranked_jobs) >= limit:
            break

    # Clean up location-filtered and expired matches from DB
    if expired_ids:
        await db.execute(
            delete(JobMatch).where(
                JobMatch.user_id == user_id,
                JobMatch.job_id.in_(expired_ids),
            )
        )
        await db.commit()

    return ranked_jobs


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")
    return job
