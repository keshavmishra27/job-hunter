import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.config import get_settings

settings = get_settings()


class EmailSender:
    def __init__(self):
        self._sent_count_today = 0
        self._last_reset = datetime.utcnow().date()

    def _reset_daily_count(self):
        today = datetime.utcnow().date()
        if today != self._last_reset:
            self._sent_count_today = 0
            self._last_reset = today

    def _check_throttle(self):
        self._reset_daily_count()
        if self._sent_count_today >= settings.max_emails_per_day:
            raise RuntimeError(
                f"Daily email limit reached ({settings.max_emails_per_day}). Try again tomorrow."
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _smtp_send(self, to: str, subject: str, body: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user
        msg["To"] = to
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.smtp_user, to, msg.as_string())

    async def send(self, to: str, subject: str, body: str) -> dict:
        self._check_throttle()

        result = {
            "recipient": to,
            "sent_at": None,
            "status": "failed",
            "error_message": None,
        }

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._smtp_send(to, subject, body)
            )
            self._sent_count_today += 1
            result["status"] = "sent"
            result["sent_at"] = datetime.utcnow()
            logger.success(f"[Sender] Email sent to {to} | Subject: {subject}")
        except Exception as e:
            result["error_message"] = str(e)
            logger.error(f"[Sender] Failed to send to {to}: {e}")

        return result

    async def send_draft(self, draft: dict, recipient_email: str) -> dict:
        if draft.get("status") != "approved":
            raise ValueError(f"Draft {draft.get('id')} is not approved. Status: {draft.get('status')}")
        return await self.send(
            to=recipient_email,
            subject=draft.get("subject", "Internship Application"),
            body=draft.get("body", ""),
        )
