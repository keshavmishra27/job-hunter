from datetime import datetime
from loguru import logger


def detect_year_fit(text: str | None) -> str:
    if not text:
        return "unknown"
    t = text.lower()

    # Explicit 3rd-year / pre-final confirmation
    CONFIRM = ["3rd year", "3rd-year", "third year", "pre-final", "prefinal",
               "pre final", "pre-final year", "prefinal year", "3rd"]
    for trig in CONFIRM:
        if trig in t:
            return "eligible"

    # Explicit exclusions that make a posting off-limits
    EXCLUDE = [
        "final year only", "only final year", "final year students only",
        "post graduate", "postgraduate", "post-graduate",
        "mba required", "mba preferred", "phd",
        # Numeric experience requirements (1+ year) block a 0-exp student
        "1+ year", "1+ years", "1 year experience", "1 years experience",
        "minimum 1 year", "minimum 1 years",
        "minimum 2 years", "minimum 3 years", "minimum 5 years",
        "2+ years", "3+ years", "5+ years",
        "1-2 years", "1-3 years", "2-3 years", "2-5 years",
        "experience: 1", "experience: 2", "experience: 3",  # Indeed format
    ]
    for excl in EXCLUDE:
        if excl in t:
            return "not_eligible"

    # No year constraint mentioned -> open internship, eligible
    return "eligible"


def simple_role_match(title: str | None, description: str | None, preferred_roles: list[str]) -> float:
    if not preferred_roles:
        return 0.5
    text = " ".join(filter(None, [title or "", description or ""])).lower()
    matched = 0
    for role in preferred_roles:
        if role.lower() in text:
            matched += 1
    return min(matched / max(len(preferred_roles), 1), 1.0)


def recency_score(posted_date) -> float:
    if not posted_date:
        return 0.5
    try:
        if isinstance(posted_date, str):
            posted = datetime.fromisoformat(posted_date)
        else:
            posted = posted_date
    except Exception:
        return 0.5
    days = (datetime.utcnow() - posted).days
    return max(0.0, 1.0 - days / 30)


def score_notice(notice: dict, profile: dict) -> dict:
    year_fit = 1.0 if detect_year_fit((notice.get("title") or "") + " " + (notice.get("description") or "")) == "eligible" else 0.0
    role_score = simple_role_match(notice.get("title"), notice.get("description"), profile.get("preferred_roles", []))
    location_score = 1.0 if (notice.get("mode") == "remote") else 0.5
    recency = recency_score(notice.get("posted_date"))

    breakdown = {
        "year_fit": year_fit,
        "role_match": role_score,
        "location_fit": location_score,
        "recency": recency,
    }

    weights = {"year_fit": 0.4, "role_match": 0.3, "location_fit": 0.2, "recency": 0.1}
    total = sum(weights[k] * breakdown.get(k, 0) for k in weights)
    logger.debug(f"[InternMatch] score breakdown {breakdown} -> {total}")
    return {"score": round(total, 4), "breakdown": breakdown}
