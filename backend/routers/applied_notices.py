from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import AppliedNotice, Notice

router = APIRouter(prefix="/applied", tags=["AppliedNotices"])

VALID_STATUSES = {"saved", "viewed", "opened", "applied", "dismissed"}


class MarkAppliedRequest(BaseModel):
    user_id: str
    notice_id: str
    status: str = "saved"
    notes: str | None = None


class UpdateAppliedRequest(BaseModel):
    status: str | None = None
    notes: str | None = None


@router.post("/mark")
async def mark_applied(req: MarkAppliedRequest, db: AsyncSession = Depends(get_db)):
    if req.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")

                          
    nres = await db.execute(select(Notice).where(Notice.id == req.notice_id))
    notice = nres.scalar_one_or_none()
    if not notice:
        raise HTTPException(404, "Notice not found.")

    existing = await db.execute(
        select(AppliedNotice).where(
            AppliedNotice.user_id == req.user_id,
            AppliedNotice.notice_id == req.notice_id,
        )
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row:
        raise HTTPException(409, "Already tracked this notice for the user.")

    applied = AppliedNotice(
        notice_id=req.notice_id,
        user_id=req.user_id,
        status=req.status,
        notes=req.notes,
        updated_at=datetime.utcnow(),
    )
    db.add(applied)
    await db.commit()
    await db.refresh(applied)

    return {
        "applied_id": applied.id,
        "notice_id": applied.notice_id,
        "status": applied.status,
        "updated_at": applied.updated_at,
    }


@router.get("/{user_id}")
async def list_applied(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AppliedNotice, Notice).join(Notice, AppliedNotice.notice_id == Notice.id).where(AppliedNotice.user_id == user_id)
    )
    rows = result.fetchall()
    return [
        {
            "applied_id": a.id,
            "notice_id": a.notice_id,
            "title": n.title,
            "company": n.company,
            "status": a.status,
            "notes": a.notes,
            "updated_at": a.updated_at,
            "apply_link": n.portal_link,
            "source": n.source,
        }
        for a, n in rows
    ]


@router.patch("/{applied_id}")
async def update_applied(applied_id: str, req: UpdateAppliedRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AppliedNotice).where(AppliedNotice.id == applied_id))
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Applied record not found.")

    if req.status is not None:
        if req.status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")
        a.status = req.status

    if req.notes is not None:
        a.notes = req.notes

    a.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Updated.", "applied_id": applied_id, "status": a.status}


@router.delete("/{applied_id}")
async def delete_applied(applied_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AppliedNotice).where(AppliedNotice.id == applied_id))
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Applied record not found.")
    await db.delete(a)
    await db.commit()
    return {"message": "Removed tracking for applied notice."}
