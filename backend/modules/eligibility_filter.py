"""
Eligibility Filter — decides whether a posting is worth showing.

Extracted from ranker._hard_filter so it can be used independently
in the unified pipeline.

Applied rules:
  - Title validity (no missing/unknown titles)
  - Expiry check (posted_date older than max_days)
  - Experience requirement (3rd year / pre-final year fit)
  - Duration cap (internship duration <= MAX_DURATION_MONTHS)
  - Location rule (remote always passes; offline must match allowed cities)
  - Deadline validity (for notices: must be in the future)
  - Source trust (reliability-based optional filter)
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from loguru import logger


# ─── Constants ───────────────────────────────────────────────────────────────

REMOTE_HINTS = {
    "remote", "wfh", "work from home", "work-from-home",
    "anywhere in india", "pan india",
}

MAX_DURATION_MONTHS = 6


# ─── Individual Checks ──────────────────────────────────────────────────────

def _has_valid_title(job: dict) -> bool:
    """Check that title is present and not 'Unknown'."""
    title = (job.get("title") or "").strip().lower()
    return bool(title) and title != "unknown"


def _is_expired(job: dict, max_days: int = 30) -> bool:
    """Return True if the job is older than max_days."""
    posted = job.get("posted_date") or job.get("posted_at")
    if not posted:
        return False  # No date → keep it, don't drop blindly
    try:
        if isinstance(posted, str):
            posted = datetime.fromisoformat(posted)
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(tz=timezone.utc) - posted).days
        return days_old > max_days
    except Exception:
        return False


def _is_remote(job: dict) -> bool:
    """Check if a job is remote/WFH using mode field and location hints."""
    mode = (job.get("mode") or "").lower()
    if mode == "remote":
        return True
    location = (job.get("location") or "").lower()
    description = (job.get("description") or "").lower()
    combined = f"{location} {description}"
    return any(hint in combined for hint in REMOTE_HINTS)


def _detect_duration_months(text: str) -> int | None:
    """Extract internship duration in months from text."""
    if not text:
        return None
    t = text.lower()
    max_months = None

    # Pattern: "X-Y months" or "X to Y months"
    range_pattern = re.findall(r'(\d+)\s*(?:to|-)\s*(\d+)\s*months?', t)
    for low, high in range_pattern:
        val = int(high)
        if max_months is None or val > max_months:
            max_months = val

    # Pattern: standalone "X months"
    single_pattern = re.findall(r'(\d+)\s*months?', t)
    for m in single_pattern:
        val = int(m)
        if val > 24:
            continue
        if max_months is None or val > max_months:
            max_months = val

    # Pattern: "X weeks" → convert
    week_pattern = re.findall(r'(\d+)\s*weeks?', t)
    for w in week_pattern:
        int_months = math.ceil(int(w) / 4.0)
        if max_months is None or int_months > max_months:
            max_months = int_months

    return max_months


def _experience_filter(job: dict) -> bool:
    """Return True (keep) if the job does not require prior experience."""
    from backend.modules.internship_matcher import detect_year_fit
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    result = detect_year_fit(text)
    if result == "not_eligible":
        return False
    return True


def _duration_filter(job: dict) -> bool:
    """Return True (keep) if duration is <= MAX_DURATION_MONTHS."""
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    months = _detect_duration_months(text)
    if months is not None and months > MAX_DURATION_MONTHS:
        return False
    return True


def _location_filter(job: dict, profile: dict) -> bool:
    """
    Return True (keep) if the job passes the location rule.
    Remote jobs always pass.  Offline jobs must match an allowed city.
    If no cities are set, everything passes.
    """
    location_rule = profile.get("location_rule") or {}
    allowed_cities = [loc.lower() for loc in (location_rule.get("offline_allowed") or [])]

    if not allowed_cities:
        return True  # No restriction

    if _is_remote(job):
        return True

    location = (job.get("location") or "").lower()
    return any(a in location or location in a for a in allowed_cities)


def _deadline_filter(job: dict) -> bool:
    """Return True (keep) if deadline is in the future or not set."""
    deadline = job.get("deadline")
    if not deadline:
        return True
    try:
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return deadline > datetime.now(tz=timezone.utc)
    except Exception:
        return True  # If we can't parse, keep it


# ─── Main Filter ─────────────────────────────────────────────────────────────

def filter_eligible(
    jobs: list[dict],
    profile: dict,
    *,
    check_experience: bool = True,
    check_duration: bool = True,
    check_location: bool = True,
    check_deadline: bool = False,
    max_days: int = 30,
) -> tuple[list[dict], list[dict]]:
    """
    Apply all eligibility filters.

    Returns:
        (eligible, filtered_out) — two lists so callers can log why items were dropped.
    """
    eligible: list[dict] = []
    filtered_out: list[dict] = []

    for job in jobs:
        # 1. Title validity
        if not _has_valid_title(job):
            job["_filter_reason"] = "invalid_title"
            filtered_out.append(job)
            continue

        # 2. Expiry
        if _is_expired(job, max_days=max_days):
            job["_filter_reason"] = "expired"
            filtered_out.append(job)
            continue

        # 3. Experience requirement
        if check_experience and not _experience_filter(job):
            job["_filter_reason"] = "experience_required"
            filtered_out.append(job)
            continue

        # 4. Duration cap
        if check_duration and not _duration_filter(job):
            job["_filter_reason"] = "duration_too_long"
            filtered_out.append(job)
            continue

        # 5. Location
        if check_location and not _location_filter(job, profile):
            job["_filter_reason"] = "location_mismatch"
            filtered_out.append(job)
            continue

        # 6. Deadline validity
        if check_deadline and not _deadline_filter(job):
            job["_filter_reason"] = "deadline_passed"
            filtered_out.append(job)
            continue

        eligible.append(job)

    logger.info(
        f"[EligibilityFilter] {len(jobs)} → {len(eligible)} eligible, "
        f"{len(filtered_out)} filtered out"
    )
    return eligible, filtered_out
