"""
Normalizer — converts every RawJob into one common schema.

After normalization, every item looks the same regardless of source.
No more special-case swamps.
"""
import uuid
import re
import hashlib
from datetime import datetime
from loguru import logger
from backend.modules.fetchers.base_fetcher import RawJob


OFFLINE_KEYWORDS = {"offline", "on-site", "onsite", "in-office", "work from office", "wfo"}
REMOTE_KEYWORDS = {"remote", "work from home", "wfh", "virtual", "online"}
HYBRID_KEYWORDS = {"hybrid"}


def _infer_mode(raw: RawJob) -> str:
    combined = " ".join(filter(None, [raw.internship_type, raw.location, raw.description or ""])).lower()
    if any(k in combined for k in REMOTE_KEYWORDS):
        return "remote"
    if any(k in combined for k in HYBRID_KEYWORDS):
        return "hybrid"
    if any(k in combined for k in OFFLINE_KEYWORDS):
        return "offline"
    return "offline"


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text.strip())


def _compute_fingerprint(title: str, company: str, location: str | None, apply_link: str | None) -> str:
    """Compute a stable fingerprint for deduplication."""
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9\s]", "", (s or "").lower().strip())

    key = "|".join([
        _norm(title),
        _norm(company),
        _norm(location or ""),
        (apply_link or "").lower().strip(),
    ])
    return hashlib.sha256(key.encode()).hexdigest()


def _infer_source_type(source: str) -> str:
    """Infer source_type from source name for backward compat."""
    source_lower = source.lower()
    if source_lower.startswith("telegram"):
        return "telegram"
    if source_lower == "gmail":
        return "email"
    return "website"


def normalize(raw: RawJob) -> dict:
    """Normalize a single RawJob into the common schema."""
    if raw.extra is None:
        logger.warning(f"RawJob.extra was None for source: {raw.source}")
    extra = raw.extra or {}
    mode = extra.get("mode") or _infer_mode(raw)

    title = _clean(raw.title) or "Untitled"
    company = _clean(raw.company) or "Unknown"
    location = _clean(raw.location)
    apply_link = raw.apply_link

                                   
    fingerprint = raw.fingerprint or _compute_fingerprint(title, company, location, apply_link)

    result = {
        "id": str(uuid.uuid4()),
        "source": raw.source,
        "source_type": _infer_source_type(raw.source),
        "title": title,
        "company": company,
        "organization": company,
        "location": location,
        "mode": mode,
        "description": _clean(raw.description),
        "apply_link": apply_link,
        "canonical_url": getattr(raw, 'canonical_url', None),
        "fingerprint": fingerprint,
        "raw_text": _clean(raw.description),                                          
        "posted_date": raw.posted_date,
        "posted_at": raw.posted_date,                           
        "opportunity_type": getattr(raw, 'opportunity_type', 'internship'),
        "status": "new",
        "fetched_at": datetime.utcnow(),
    }

                                             
    if result["opportunity_type"] == "freelance":
        _freelance_keys = (
            "budget_min", "budget_max", "budget_type", "currency",
            "deliverables", "client_type", "client_rating",
            "client_reviews_count", "required_skills", "project_length",
            "payment_verified", "delivery_time_days", "remote_only",
            "deadline",
        )
        for key in _freelance_keys:
            if key in extra:
                result[key] = extra[key]

                                          
    if extra.get("eligibility_text"):
        result["eligibility_text"] = extra["eligibility_text"]
    if extra.get("deadline"):
        result["deadline"] = extra["deadline"]
    if extra.get("stipend"):
        result["stipend"] = extra["stipend"]
    if extra.get("sender_email"):
        result["sender_email"] = extra["sender_email"]
    if extra.get("subject"):
        result["subject"] = extra["subject"]

    return result


def normalize_many(raws: list[RawJob]) -> list[dict]:
    return [normalize(r) for r in raws]
