from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import JobPost, Draft, SentEmail, JobMatch

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

    return {
        "total_jobs_fetched": total_jobs,
        "matched_for_user": matched_jobs,
        "drafts_pending_review": drafts_new,
        "drafts_approved": drafts_approved,
        "emails_sent": sent_count,
    }
