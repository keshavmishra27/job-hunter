"""
Gmail integration routes — status check, credential validation, and standalone sync.

The main fetch flow goes through POST /internships/fetch?sources=gmail, but these
routes provide setup helpers and a dedicated sync endpoint.
"""

import imaplib
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.config import get_settings
from loguru import logger

router = APIRouter(prefix="/gmail", tags=["Gmail"])


@router.get("/status")
async def gmail_status():
    """Check if Gmail IMAP credentials are configured."""
    settings = get_settings()
    connected = bool(settings.gmail_user and settings.gmail_app_password)
    return {
        "connected": connected,
        "email": settings.gmail_user if connected else None,
        "imap_host": settings.gmail_imap_host,
        "days_back": settings.gmail_days_back,
    }


@router.post("/connect")
async def gmail_connect():
    """
    Validate Gmail IMAP credentials by attempting a test connection.
    Does not fetch any emails — just verifies the login works.
    """
    settings = get_settings()

    if not settings.gmail_user or not settings.gmail_app_password:
        return {
            "success": False,
            "error": "Gmail credentials not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env",
        }

    try:
        mail = imaplib.IMAP4_SSL(settings.gmail_imap_host, settings.gmail_imap_port)
        mail.login(settings.gmail_user, settings.gmail_app_password)
                             
        status, data = mail.select("INBOX", readonly=True)
        msg_count = int(data[0]) if status == "OK" else 0
        mail.logout()

        logger.info(f"[Gmail] Connection test successful — {msg_count} messages in INBOX")
        return {
            "success": True,
            "email": settings.gmail_user,
            "inbox_count": msg_count,
        }
    except imaplib.IMAP4.error as e:
        logger.error(f"[Gmail] IMAP auth failed: {e}")
        return {
            "success": False,
            "error": f"IMAP authentication failed: {e}. Check your app password.",
        }
    except Exception as e:
        logger.error(f"[Gmail] Connection error: {e}")
        return {
            "success": False,
            "error": f"Connection failed: {e}",
        }


@router.post("/sync")
async def gmail_sync(user_id: str = "demo-user-1", db: AsyncSession = Depends(get_db)):
    """
    Standalone Gmail sync — fetches, filters, and counts internship emails.
    This is a convenience wrapper; the full pipeline runs via POST /internships/fetch?sources=gmail.
    """
    from backend.modules.fetchers.gmail_fetcher import GmailFetcher

    fetcher = GmailFetcher()
    try:
        raw_jobs = await fetcher.fetch(["internship"])
        return {
            "success": True,
            "total_scanned": "see logs for total",
            "internship_matches": len(raw_jobs),
            "notices": [
                {
                    "title": j.title,
                    "company": j.company,
                    "apply_link": j.apply_link,
                    "sender": j.extra.get("sender_email", ""),
                }
                for j in raw_jobs[:20]                    
            ],
        }
    except Exception as e:
        logger.error(f"[Gmail] Sync failed: {e}")
        return {"success": False, "error": str(e)}
