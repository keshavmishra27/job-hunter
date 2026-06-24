import imaplib
import email as email_lib
from email.utils import parseaddr
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import uuid

from backend.config import get_settings
from backend.models import Application, JobPost
from backend.modules.fetchers.gmail_fetcher import _decode_header_value, _extract_company_from_sender, _get_body, _html_to_text

class GmailTrackerSync:
    """
    Syncs the user's Gmail inbox for emails that indicate an application was sent,
    such as 'Thank you for applying', 'Application Received', etc.
    """
    
    @staticmethod
    def _is_application_confirmation(subject: str, body: str) -> bool:
        subj_low = subject.lower()
        body_low = body.lower()
        
        keywords = [
            "thank you for applying", "application received", "application has been received", 
            "submission confirmation", "we have received your application", "successfully applied",
            "your application was sent", "indeed application", "application submitted",
            "thank you for your application", "thanks for applying", "application to",
            "received your resume", "we got your application"
        ]
        return any(kw in subj_low or kw in body_low for kw in keywords)

    async def sync_applications(self, user_id: str, db: AsyncSession, days_back: int = 14) -> int:
        settings = get_settings()
        if not settings.gmail_user or not settings.gmail_app_password:
            logger.warning("[Tracker] No Gmail credentials configured.")
            return 0

        import asyncio
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None,
                self._fetch_sync,
                settings.gmail_user,
                settings.gmail_app_password,
                settings.gmail_imap_host,
                settings.gmail_imap_port,
                days_back,
            )
            
            added_count = 0
            for item in results:
                                                                     
                existing = await db.execute(select(Application).where(Application.thread_id == item["thread_id"]))
                if existing.scalar_one_or_none():
                    continue
                
                                                                
                job_id = str(uuid.uuid4())
                job = JobPost(
                    id=job_id,
                    title=item["role"],
                    company=item["company"],
                    location="Unknown",
                    internship_type="Full-time/Internship",
                    description="Job synced from Gmail tracking.",
                    apply_link="email_sync",
                    source="Gmail Tracker",
                    posted_date=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                db.add(job)
                
                app = Application(
                    user_id=user_id,
                    job_id=job_id,
                    status="applied",
                    company_name=item["company"],
                    role_title=item["role"],
                    application_link="email_sync",
                    source="Gmail Tracker",
                    thread_id=item["thread_id"],
                    applied_at=item["date"] or datetime.now(timezone.utc).replace(tzinfo=None)
                )
                db.add(app)
                added_count += 1
                
            if added_count > 0:
                await db.commit()
            
            return added_count
        except Exception as e:
            logger.error(f"[Tracker] Gmail sync failed: {e}")
            return 0

    def _fetch_sync(self, user, password, host, port, days_back) -> list[dict]:
        results = []
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(user, password)
            mail.select("INBOX", readonly=True)

            since_date = (datetime.now(tz=timezone.utc) - timedelta(days=days_back)).strftime("%d-%b-%Y")
            status, msg_ids = mail.search(None, f'(SINCE "{since_date}")')
            if status != "OK" or not msg_ids[0]:
                mail.logout()
                return []

            ids = msg_ids[0].split()
            for msg_id in reversed(ids):
                try:
                    status, data = mail.fetch(msg_id, "(RFC822)")
                    if status != "OK" or not data[0]:
                        continue
                    
                    raw_email = data[0][1]
                    msg = email_lib.message_from_bytes(raw_email)
                    
                    subject = _decode_header_value(msg.get("Subject", ""))
                    from_header = _decode_header_value(msg.get("From", ""))
                    thread_id = _decode_header_value(msg.get("In-Reply-To", msg.get("Message-ID", "")))
                    
                    plain, html = _get_body(msg)
                    body_text = plain or _html_to_text(html) if html else ""
                    
                    if self._is_application_confirmation(subject, body_text):
                        company = _extract_company_from_sender(from_header)
                                                                                     
                        role = re.sub(r"(?i)^(application received|thank you for applying)[\s:-]*", "", subject).strip()
                        if not role:
                            role = "Unknown Role"
                            
                                      
                        date_str = msg.get("Date")
                        parsed_date = None
                        if date_str:
                            from email.utils import parsedate_to_datetime
                            try:
                                parsed_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
                            except Exception:
                                pass
                                
                        results.append({
                            "company": company,
                            "role": role,
                            "thread_id": thread_id,
                            "date": parsed_date
                        })
                except Exception as e:
                    logger.debug(f"[Tracker] Error processing message {msg_id}: {e}")
                    continue
                    
            mail.logout()
        except Exception as e:
            logger.error(f"[Tracker] IMAP connection error: {e}")
            
        return results

    def fetch_thread_reply(self, thread_id: str, since_date: datetime) -> str | None:
        settings = get_settings()
        if not settings.gmail_user or not settings.gmail_app_password:
            return None
            
        try:
            mail = imaplib.IMAP4_SSL(settings.gmail_imap_host, settings.gmail_imap_port)
            mail.login(settings.gmail_user, settings.gmail_app_password)
            mail.select("INBOX", readonly=True)
            
                                                                                         
                                                                   
                                                                           
            since_str = since_date.strftime("%d-%b-%Y")
            status, msg_ids = mail.search(None, f'(SINCE "{since_str}")')
            if status == "OK" and msg_ids[0]:
                for msg_id in reversed(msg_ids[0].split()[:20]):                         
                    st, data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (IN-REPLY-TO MESSAGE-ID)])")
                    if st == "OK" and data[0]:
                        msg = email_lib.message_from_bytes(data[0][1])
                        reply_to = _decode_header_value(msg.get("In-Reply-To", ""))
                        msg_id_val = _decode_header_value(msg.get("Message-ID", ""))
                        if thread_id in reply_to or thread_id in msg_id_val:
                                                                 
                            st_body, body_data = mail.fetch(msg_id, "(RFC822)")
                            if st_body == "OK" and body_data[0]:
                                full_msg = email_lib.message_from_bytes(body_data[0][1])
                                plain, html = _get_body(full_msg)
                                mail.logout()
                                return plain or _html_to_text(html) if html else ""
            mail.logout()
        except Exception as e:
            logger.error(f"[Tracker] Failed to check thread replies: {e}")
        return None
