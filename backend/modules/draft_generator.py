import json
from loguru import logger
from backend.config import get_settings

settings = get_settings()


try:
    from openai import AsyncOpenAI as AsyncOpenRouter
    OPENROUTER_AVAILABLE = bool(settings.openrouter_key)
except ImportError:
    OPENROUTER_AVAILABLE = False


DRAFT_PROMPT = """\
You are a professional internship application assistant.

## Candidate Profile
Name: {name}
Skills: {skills}
Projects: {projects}
Research Areas: {research_areas}
Resume Summary: {resume_summary}

## Target Internship
Title: {title}
Company: {company}
Location: {location}
Description: {description}

## Task
Write a professional, concise, and personalised internship application email.

Return ONLY a JSON object with exactly these fields:
{{
  "subject": "<email subject>",
  "body": "<full email body with greeting, intro, project match, why fit, closing>",
  "linkedin_message": "<under 300 char LinkedIn connection message>",
  "attachment_checklist": ["Resume", "LOR (if applicable)"]
}}

Rules:
- Mention the most relevant project by name.
- Keep body under 250 words.
- Do not use placeholders like [Your Name].
- Use the candidate name directly.
"""


class DraftGenerator:
    async def _call_llm(self, prompt: str) -> str:

        if OPENROUTER_AVAILABLE:
            client = AsyncOpenRouter(
                api_key=settings.openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
            resp = await client.chat.completions.create(
                model="auto",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return resp.choices[0].message.content or ""

        logger.warning("[DraftGenerator] No LLM configured — using fallback template")
        return self._fallback_draft()

    def _fallback_draft(self) -> str:
        return json.dumps({
            "subject": "Application for Internship",
            "body": "Please configure OPENROUTER_KEY to enable personalised drafts.",
            "linkedin_message": "Hi, I'm interested in this internship opportunity.",
            "attachment_checklist": ["Resume"],
        })

    async def generate(self, job: dict, profile: dict) -> dict:
        prompt = DRAFT_PROMPT.format(
            name=profile.get("name", "Applicant"),
            skills=", ".join(profile.get("skills", [])[:10]),
            projects="; ".join(profile.get("projects", [])[:3]),
            research_areas=", ".join(profile.get("research_areas", [])[:4]),
            resume_summary=profile.get("resume_summary", ""),
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            description=(job.get("description") or "")[:800],
        )

        raw = await self._call_llm(prompt)

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            draft = json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            logger.warning("[DraftGenerator] Failed to parse LLM JSON, using raw text as body")
            draft = {
                "subject": f"Application for {job.get('title', 'Internship')} at {job.get('company', '')}",
                "body": raw,
                "linkedin_message": "",
                "attachment_checklist": ["Resume"],
            }

        draft["job_id"] = job.get("id")
        draft["status"] = "new"
        return draft
