import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import User, UserProfile, Resume
from backend.modules.resume_parser import ResumeParser
from backend.config import get_settings

router = APIRouter(prefix="/profile", tags=["Profile"])
settings = get_settings()


@router.post("/upload-resume")
async def upload_resume(
    user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF resumes are supported.")

    storage = Path(settings.storage_dir) / "resumes"
    storage.mkdir(parents=True, exist_ok=True)
    dest = storage / f"{user_id}_{file.filename}"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    resume = Resume(user_id=user_id, file_path=str(dest), original_filename=file.filename)
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return {"resume_id": resume.id, "file_path": str(dest), "message": "Uploaded. Call /parse to extract profile."}


@router.post("/parse/{resume_id}")
async def parse_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found.")

    parser = ResumeParser(resume.file_path)
    profile_data = parser.parse()

    result2 = await db.execute(select(UserProfile).where(UserProfile.user_id == resume.user_id))
    existing = result2.scalar_one_or_none()

    if existing:
        existing.skills = profile_data["skills"]
        existing.projects = profile_data["projects"]
        existing.research_areas = profile_data["research_areas"]
        existing.preferred_roles = profile_data["preferred_roles"]
        existing.location_rule = profile_data["location_rule"]
        existing.resume_summary = profile_data["resume_summary"]
    else:
        profile = UserProfile(
            user_id=resume.user_id,
            skills=profile_data["skills"],
            projects=profile_data["projects"],
            research_areas=profile_data["research_areas"],
            preferred_roles=profile_data["preferred_roles"],
            location_rule=profile_data["location_rule"],
            resume_summary=profile_data["resume_summary"],
        )
        db.add(profile)

    resume.parsed = True
    await db.commit()

    return {"message": "Profile extracted.", "profile": profile_data}


@router.get("/{user_id}")
async def get_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found. Upload and parse a resume first.")
    return {
        "skills": profile.skills,
        "projects": profile.projects,
        "research_areas": profile.research_areas,
        "preferred_roles": profile.preferred_roles,
        "location_rule": profile.location_rule,
        "resume_summary": profile.resume_summary,
        "graduation_year": profile.graduation_year,
        "telegram_chat_id": profile.telegram_chat_id,
    }


class ProfileUpdate(BaseModel):
    graduation_year: int | None = None
    telegram_chat_id: str | None = None
    preferred_roles: list[str] | None = None
    skills: list[str] | None = None


@router.patch("/{user_id}")
async def update_profile(user_id: str, update: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    """Update profile fields (graduation year, Telegram chat ID, roles, skills)."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        # Create minimal profile so user can save settings without a resume
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    if update.graduation_year is not None:
        profile.graduation_year = update.graduation_year
    if update.telegram_chat_id is not None:
        profile.telegram_chat_id = update.telegram_chat_id
    if update.preferred_roles is not None:
        profile.preferred_roles = update.preferred_roles
    if update.skills is not None:
        profile.skills = update.skills

    await db.commit()
    await db.refresh(profile)

    return {
        "message": "Profile updated.",
        "graduation_year": profile.graduation_year,
        "telegram_chat_id": profile.telegram_chat_id,
        "preferred_roles": profile.preferred_roles,
        "skills": profile.skills,
    }

