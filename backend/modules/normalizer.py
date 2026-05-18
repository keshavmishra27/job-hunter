import uuid
import re
from datetime import datetime
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


def normalize(raw: RawJob) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "source": raw.source,
        "title": _clean(raw.title) or "Untitled",
        "company": _clean(raw.company) or "Unknown",
        "location": _clean(raw.location),
        "mode": raw.extra.get("mode") or _infer_mode(raw),
        "description": _clean(raw.description),
        "apply_link": raw.apply_link,
        "posted_date": raw.posted_date,
        "status": "new",
        "fetched_at": datetime.utcnow(),
    }


def normalize_many(raws: list[RawJob]) -> list[dict]:
    return [normalize(r) for r in raws]
