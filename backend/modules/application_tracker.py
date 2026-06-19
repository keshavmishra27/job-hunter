import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from backend.modules.gmail_tracker import GmailTrackerSync

logger = logging.getLogger(__name__)

class ApplicationTracker:
    """
    Application Tracker Engine:
    Monitors email threads associated with Applications You Sent.
    Purpose: Measure Outcomes.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def check_thread_for_replies(self, thread_id: str, last_checked_date: datetime) -> Optional[str]:
        """
        Polls the email API (e.g. Gmail) to get the latest reply in a thread after the last_checked_date.
        Returns the text content of the reply, or None if no new reply.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        sync_module = GmailTrackerSync()
        return await loop.run_in_executor(None, sync_module.fetch_thread_reply, thread_id, last_checked_date)

    async def classify_response(self, email_body: str) -> Tuple[str, Optional[str]]:
        """
        Uses an LLM to classify an email reply into one of the tracking statuses.
        Returns (Status, Rejection_Reason)
        
        Statuses:
        - Interview: Any invitation to talk, interview, or next steps that involve a call.
        - Assessment: Request to complete a coding challenge, OA, or take-home assignment.
        - Rejected: Explicit rejection.
        - Offer: Job offer made.
        - No Response: Handled externally based on time.
        """
        
        system_prompt = """You are an expert HR tracking assistant. Read the following email reply from a company.
Classify the response into EXACTLY ONE of the following categories:
- "Interview": They want to schedule a call, chat, or interview.
- "Assessment": They want you to take an assessment, HackerRank, OA, or test.
- "Rejected": They are moving forward with other candidates or explicitly rejecting.
- "Offer": They are offering the position.
- "Other": Any other type of email (e.g. automated confirmation of receipt).

If the status is "Rejected", try to extract a concise 1-sentence reason if explicitly stated (e.g. "Profile mismatch", "Role filled").

Return a JSON object in this format:
{
    "status": "...",
    "reason": "..." // Only if Rejected, otherwise null
}
"""
        if not self.llm_client:
            # Mock or default logic if LLM is not configured for testing
            body_lower = email_body.lower()
            if "unfortunately" in body_lower or "regret" in body_lower:
                return "Rejected", "Profile mismatch"
            if "interview" in body_lower or "invite you" in body_lower or "chat" in body_lower:
                return "Interview", None
            if "assessment" in body_lower or "hackerrank" in body_lower or "test" in body_lower:
                return "Assessment", None
            if "offer" in body_lower:
                return "Offer", None
            return "Other", None

        # Here we would call the actual LLM Client
        try:
            # response = await self.llm_client.generate(system_prompt, email_body)
            # data = json.loads(response)
            # return data.get("status", "Other"), data.get("reason", None)
            pass
        except Exception as e:
            logger.error(f"Failed to classify email: {e}")
            return "Other", None

    async def monitor_application(self, application) -> bool:
        """
        Orchestrates monitoring for a single application object.
        Returns True if status changed.
        """
        if not application.thread_id:
            return False

        # If it's been > 14 days and status is still "applied" or similar
        days_since_apply = (datetime.now(timezone.utc).replace(tzinfo=None) - application.applied_at).days
        if days_since_apply > 14 and application.status in ["applied"]:
            application.status = "No Response"
            return True

        new_reply = await self.check_thread_for_replies(application.thread_id, application.response_date or application.applied_at)
        if new_reply:
            status, reason = await self.classify_response(new_reply)
            if status != "Other" and status != application.status:
                application.status = status
                application.response_date = datetime.now(timezone.utc).replace(tzinfo=None)
                if reason:
                    application.rejection_reason = reason
                return True
                
        return False
