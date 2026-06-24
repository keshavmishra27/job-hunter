from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import JobPost, Draft, SentEmail, JobMatch, Application
from backend.models.opportunity import Opportunity

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats/{user_id}")
async def dashboard_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    total_jobs = await db.scalar(select(func.count()).select_from(JobPost))
    matched_jobs = await db.scalar(
        select(func.count()).select_from(JobMatch).where(JobMatch.user_id == user_id)
    )
    drafts_new = await db.scalar(
        select(func.count()).select_from(Draft).where(Draft.user_id == user_id, Draft.status == "new")
    )
    drafts_approved = await db.scalar(
        select(func.count()).select_from(Draft).where(Draft.user_id == user_id, Draft.status == "approved")
    )
    sent_count = await db.scalar(select(func.count()).select_from(SentEmail).where(SentEmail.status == "sent"))

                     
    freelance_gigs = await db.scalar(
        select(func.count()).select_from(Opportunity).where(Opportunity.opportunity_type == "freelance")
    )

    return {
        "total_jobs_fetched": total_jobs,
        "matched_for_user": matched_jobs,
        "drafts_pending_review": drafts_new,
        "drafts_approved": drafts_approved,
        "emails_sent": sent_count,
        "freelance_gigs": freelance_gigs or 0,
    }

@router.get("/analytics/{user_id}")
async def dashboard_analytics(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns outcome measurement analytics based on Application tracker data.
    """
                                        
    base_query = select(Application).where(Application.user_id == user_id)
    result = await db.execute(base_query)
    applications = result.scalars().all()

    total_sent = len(applications)
    interviews = sum(1 for app in applications if app.status == "Interview")
    offers = sum(1 for app in applications if app.status == "Offer")
    responses = sum(1 for app in applications if app.status in ["Interview", "Assessment", "Rejected", "Offer"])

    response_rate = (responses / total_sent * 100) if total_sent > 0 else 0

                                                      
    resume_stats = {}
    for app in applications:
        res = app.resume_used or "Unknown"
        if res not in resume_stats:
            resume_stats[res] = {"total": 0, "success": 0}
        resume_stats[res]["total"] += 1
        if app.status in ["Interview", "Offer"]:
            resume_stats[res]["success"] += 1

    best_resume = "None"
    worst_resume = "None"
    best_rate = -1
    worst_rate = 101
    
    for res, stats in resume_stats.items():
        if stats["total"] > 0:
            rate = stats["success"] / stats["total"] * 100
            if rate > best_rate:
                best_rate = rate
                best_resume = res
            if rate < worst_rate:
                worst_rate = rate
                worst_resume = res

                         
    source_stats = {}
    for app in applications:
        src = app.source or "Unknown"
        if src not in source_stats:
            source_stats[src] = {"total": 0, "success": 0}
        source_stats[src]["total"] += 1
        if app.status in ["Interview", "Offer"]:
            source_stats[src]["success"] += 1
            
    source_success_rates = {}
    for src, stats in source_stats.items():
        if stats["total"] > 0:
            source_success_rates[src] = round(stats["success"] / stats["total"] * 100, 1)

    return {
        "applications_sent": total_sent,
        "interviews": interviews,
        "offers": offers,
        "response_rate_percent": round(response_rate, 1),
        "best_resume": best_resume,
        "worst_resume": worst_resume,
        "source_success_rates": source_success_rates
    }
