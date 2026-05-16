from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.database import get_db
from backend.models import JobPost, JobMatch, UserProfile, Application
from backend.models.github import RepoEntry, RepoAnalysis
from backend.modules.fetchers import (
    InternshalaFetcher, IndeedFetcher
)
from backend.modules.normalizer import normalize_many
from backend.modules.deduper import deduplicate, job_fingerprint
from backend.modules.ranker import rank_jobs

router = APIRouter(prefix="/jobs", tags=["Jobs"])

FETCHERS = {
    "internshala": InternshalaFetcher,
    "indeed": IndeedFetcher,
}


@router.post("/fetch")
async def fetch_jobs(
    user_id: str,
    sources: list[str] = Query(default=["internshala"]),
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

    keywords = (profile.preferred_roles or [])[:3] + (profile.skills or [])[:3]
    all_raw = []

    for source in sources:
        cls = FETCHERS.get(source.lower())
        if not cls:
            continue
        fetcher = cls()
        raw = await fetcher.fetch(keywords)
        all_raw.extend(raw)

    normalised = normalize_many(all_raw)

    existing_result = await db.execute(select(JobPost.content_hash))
    existing_hashes = {row[0] for row in existing_result.fetchall() if row[0]}

    unique = deduplicate(normalised, existing_hashes)

    applied_fps_result = await db.execute(
        select(Application.job_fingerprint).where(Application.user_id == user_id)
    )
    applied_fingerprints = {row[0] for row in applied_fps_result.fetchall() if row[0]}

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
                    "topics": repo.topics or [],
                    "analysis_signals": analysis.analysis_signals if analysis else {},
                })
    except Exception as e:
        
        pass

    # Re score ALL existing jobs for this user so that profile changes always reflect correctly
    all_jobs_result = await db.execute(select(JobPost))
    all_jobs = all_jobs_result.scalars().all()
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
        if job_fingerprint({"title": j.title, "company": j.company}) not in applied_fingerprints
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
    db: AsyncSession = Depends(get_db),
):
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
        .order_by(JobMatch.score.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.fetchall()

    return [
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
        for match, job in rows
        if include_applied or job.id not in applied_job_ids
    ]


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")
    return job
