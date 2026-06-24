from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import Alert


async def create_alert(db: AsyncSession, user_id: str | None, notice_id: str | None, kind: str, message: str):
    try:
        alert = Alert(
            notice_id=notice_id,
            user_id=user_id,
            kind=kind,
            message=message,
            created_at=datetime.utcnow(),
            read=False,
        )
        db.add(alert)
        await db.flush()
        logger.info(f"[AlertEngine] created alert for user={user_id} kind={kind}")
        return alert
    except Exception as e:
        logger.exception(f"Failed to create alert: {e}")
        return None


async def alert_on_notice(db: AsyncSession, user_id: str, notice: object, score: float, threshold: float = 6.0):
    """Decide whether to create an alert for a user based on notice and score.
    Returns the Alert or None.
    """
    try:
                                                                               
        eligible = getattr(notice, "eligibility_status", None) or getattr(notice, "eligibility_text", None)
        if score >= threshold or (eligible and "eligible" in str(eligible).lower()):
            title = getattr(notice, "title", "New internship")
            company = getattr(notice, "company", "")
            message = f"{title} @ {company} — score {score:.1f}"
            return await create_alert(db, user_id, getattr(notice, "id", None), "new_relevant_notice", message)
    except Exception:
        logger.exception("alert_on_notice error")
    return None
