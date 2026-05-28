from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Application, JobPost, Draft
from backend.modules.deduper import job_fingerprint

router = APIRouter(prefix="/applications", tags=["Applications"])

APPLICATION_STATUSES = {"saved", "drafted", "approved", "sent", "applied", "failed"}


class MarkAppliedRequest(BaseModel):
    user_id: str
    job_id: str
    draft_id: str | None = None
    status: str = "applied"
    source: str | None = None
    follow_up_date: str | None = None
    notes: str | None = None


class UpdateApplicationRequest(BaseModel):
    status: str | None = None
    follow_up_date: str | None = None
    notes: str | None = None


@router.post("/mark")
async def mark_applied(req: MarkAppliedRequest, db: AsyncSession = Depends(get_db)):
    if req.status not in APPLICATION_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {APPLICATION_STATUSES}")

    job_result = await db.execute(select(JobPost).where(JobPost.id == req.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")

    existing = await db.execute(
        select(Application).where(
            Application.user_id == req.user_id,
            Application.job_id == req.job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already marked as applied for this job.")

    from backend.modules.deduper import canonical_fingerprint
    fp = canonical_fingerprint({
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "apply_link": job.apply_link,
    })

    follow_up_dt = None
    if req.follow_up_date:
        try:
            follow_up_dt = datetime.fromisoformat(req.follow_up_date)
        except ValueError:
            raise HTTPException(400, "follow_up_date must be ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

    application = Application(
        user_id=req.user_id,
        job_id=req.job_id,
        draft_id=req.draft_id,
        status=req.status,
        company_name=job.company,
        role_title=job.title,
        application_link=job.apply_link,
        canonical_url=job.apply_link,
        source=req.source or job.source,
        job_fingerprint=fp,
        follow_up_date=follow_up_dt,
        notes=req.notes,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    return {
        "application_id": application.id,
        "job_id": application.job_id,
        "role_title": application.role_title,
        "company_name": application.company_name,
        "status": application.status,
        "applied_at": application.applied_at,
        "follow_up_date": application.follow_up_date,
    }


@router.get("/{user_id}")
async def list_applications(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application, JobPost)
        .join(JobPost, Application.job_id == JobPost.id)
        .where(Application.user_id == user_id)
        .order_by(Application.applied_at.desc())
    )
    rows = result.fetchall()

    draft_ids = [app.draft_id for app, _ in rows if app.draft_id]
    draft_subjects: dict[str, str] = {}
    if draft_ids:
        drafts_result = await db.execute(
            select(Draft).where(Draft.id.in_(draft_ids))
        )
        for d in drafts_result.scalars().all():
            draft_subjects[d.id] = d.subject or "(no subject)"

    return [
        {
            "application_id": app.id,
            "job_id": app.job_id,
            "role_title": app.role_title or job.title,
            "company_name": app.company_name or job.company,
            "source": app.source or job.source,
            "location": job.location,
            "apply_link": app.application_link or job.apply_link,
            "status": app.status,
            "applied_at": app.applied_at,
            "follow_up_date": app.follow_up_date,
            "draft_id": app.draft_id,
            "draft_subject": draft_subjects.get(app.draft_id) if app.draft_id else None,
            "notes": app.notes,
        }
        for app, job in rows
    ]


@router.patch("/{application_id}")
async def update_application(
    application_id: str,
    req: UpdateApplicationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Application).where(Application.id == application_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found.")

    if req.status is not None:
        if req.status not in APPLICATION_STATUSES:
            raise HTTPException(400, f"Invalid status. Must be one of: {APPLICATION_STATUSES}")
        app.status = req.status

    if req.follow_up_date is not None:
        try:
            app.follow_up_date = datetime.fromisoformat(req.follow_up_date)
        except ValueError:
            raise HTTPException(400, "follow_up_date must be ISO 8601 format")

    if req.notes is not None:
        app.notes = req.notes

    await db.commit()
    return {"message": "Application updated.", "application_id": application_id, "status": app.status}


@router.delete("/{application_id}")
async def unmark_applied(application_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == application_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found.")
    await db.delete(app)
    await db.commit()
    return {"message": "Application removed. Job will reappear in the feed."}
