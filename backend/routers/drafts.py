from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Draft, JobPost, UserProfile
from backend.modules.draft_generator import DraftGenerator

router = APIRouter(prefix="/drafts", tags=["Drafts"])


class DraftUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    linkedin_message: str | None = None
    status: str | None = None


@router.post("/generate/{user_id}/{job_id}")
async def generate_draft(user_id: str, job_id: str, db: AsyncSession = Depends(get_db)):
    from backend.models import User
    from backend.models.opportunity import Opportunity
    
    # Try legacy job_posts table first, then unified opportunities table
    job_result = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = job_result.scalar_one_or_none()
    
    if job:
        job_dict = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
        }
    else:
        # Fallback: check the unified opportunities table
        opp_result = await db.execute(select(Opportunity).where(Opportunity.id == job_id))
        opp = opp_result.scalar_one_or_none()
        if not opp:
            raise HTTPException(404, "Job not found.")
        job_dict = {
            "id": opp.id,
            "title": opp.title,
            "company": opp.organization,
            "location": opp.location,
            "description": opp.description,
        }

    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found.")

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    profile_dict = {
        "name": user.name if user else "Applicant",
        "skills": profile.skills or [],
        "projects": profile.projects or [],
        "research_areas": profile.research_areas or [],
        "resume_summary": profile.resume_summary or "",
    }

    generator = DraftGenerator()
    draft_data = await generator.generate(job_dict, profile_dict)

    draft = Draft(
        user_id=user_id,
        job_id=job_id,
        subject=draft_data.get("subject"),
        body=draft_data.get("body"),
        linkedin_message=draft_data.get("linkedin_message"),
        attachment_checklist=draft_data.get("attachment_checklist"),
        status="new",
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return {
        "draft_id": draft.id,
        "subject": draft.subject,
        "body": draft.body,
        "linkedin_message": draft.linkedin_message,
        "attachment_checklist": draft.attachment_checklist,
        "status": draft.status,
    }


@router.get("/{user_id}")
async def list_drafts(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Draft, JobPost)
        .join(JobPost, Draft.job_id == JobPost.id)
        .where(Draft.user_id == user_id)
        .order_by(Draft.created_at.desc())
    )
    rows = result.fetchall()
    return [
        {
            "draft_id": draft.id,
            "job_title": job.title,
            "company": job.company,
            "subject": draft.subject,
            "status": draft.status,
            "created_at": draft.created_at,
        }
        for draft, job in rows
    ]


@router.get("/detail/{draft_id}")
async def get_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(404, "Draft not found.")
    return draft


@router.patch("/{draft_id}")
async def update_draft(draft_id: str, update: DraftUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(404, "Draft not found.")

    if update.subject is not None:
        draft.subject = update.subject
    if update.body is not None:
        draft.body = update.body
    if update.linkedin_message is not None:
        draft.linkedin_message = update.linkedin_message
    if update.status is not None:
        valid = {"new", "approved", "rejected"}
        if update.status not in valid:
            raise HTTPException(400, f"Invalid status. Must be one of: {valid}")
        draft.status = update.status

    await db.commit()
    return {"message": "Draft updated.", "draft_id": draft.id, "status": draft.status}


@router.post("/approve/{draft_id}")
async def approve_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(404, "Draft not found.")
    draft.status = "approved"
    await db.commit()
    return {"message": "Draft approved and ready to send.", "draft_id": draft_id}
