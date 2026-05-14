from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from backend.database import get_db
from backend.models import Draft, SentEmail
from backend.modules.sender import EmailSender

router = APIRouter(prefix="/send", tags=["Send"])
sender = EmailSender()


class SendRequest(BaseModel):
    draft_id: str
    recipient_email: str


@router.post("/")
async def send_email(req: SendRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Draft).where(Draft.id == req.draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(404, "Draft not found.")
    if draft.status != "approved":
        raise HTTPException(400, f"Draft is not approved. Current status: {draft.status}")

    send_result = await sender.send_draft(
        draft={"id": draft.id, "subject": draft.subject, "body": draft.body, "status": draft.status},
        recipient_email=req.recipient_email,
    )

    sent = SentEmail(
        draft_id=draft.id,
        recipient=req.recipient_email,
        sent_at=send_result.get("sent_at") or datetime.utcnow(),
        status=send_result["status"],
        error_message=send_result.get("error_message"),
    )
    db.add(sent)

    if send_result["status"] == "sent":
        draft.status = "sent"

    await db.commit()
    await db.refresh(sent)

    return {
        "sent_email_id": sent.id,
        "status": sent.status,
        "recipient": sent.recipient,
        "sent_at": sent.sent_at,
        "error": sent.error_message,
    }


@router.get("/log")
async def sent_log(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SentEmail, Draft)
        .join(Draft, SentEmail.draft_id == Draft.id)
        .order_by(SentEmail.sent_at.desc())
    )
    rows = result.fetchall()
    return [
        {
            "sent_id": sent.id,
            "recipient": sent.recipient,
            "subject": draft.subject,
            "status": sent.status,
            "sent_at": sent.sent_at,
        }
        for sent, draft in rows
    ]
