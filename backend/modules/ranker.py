import math
from datetime import datetime, timezone
from loguru import logger


OFFLINE_ALLOWED = {"delhi ncr", "gurgaon", "noida", "gurugram", "delhi"}

WEIGHTS = {
    "project_overlap": 0.35,
    "skill_match": 0.30,
    "role_match": 0.15,
    "location_fit": 0.10,
    "recency": 0.10,
}


def _location_fit(job: dict, profile: dict) -> float:
    mode = (job.get("mode") or "offline").lower()
    if mode == "remote":
        return 1.0
    location = (job.get("location") or "").lower()
    allowed = [loc.lower() for loc in profile.get("location_rule", {}).get("offline_allowed", [])]
    if any(a in location or location in a for a in allowed):
        return 1.0
    return 0.0


def _hard_filter(job: dict, profile: dict) -> bool:
    mode = (job.get("mode") or "offline").lower()
    if mode == "remote":
        return True
    location = (job.get("location") or "").lower()
    allowed = [loc.lower() for loc in profile.get("location_rule", {}).get("offline_allowed", [])]
    if any(a in location or location in a for a in allowed):
        return True
    logger.debug(f"[Ranker] Hard-filtered out: {job['title']} @ {job['company']} ({location})")
    return False


def _skill_match(job: dict, profile: dict) -> float:
    profile_skills = {s.lower() for s in (profile.get("skills") or [])}
    description = (job.get("description") or job.get("title") or "").lower()
    if not profile_skills:
        return 0.5
    matched = sum(1 for s in profile_skills if s in description)
    return min(matched / max(len(profile_skills), 1), 1.0)


def _role_match(job: dict, profile: dict) -> float:
    title = (job.get("title") or "").lower()
    preferred = [r.lower() for r in (profile.get("preferred_roles") or [])]
    if not preferred:
        return 0.5
    for role in preferred:
        words = role.split()
        if any(w in title for w in words):
            return 1.0
    return 0.2


def _project_overlap(job: dict, profile: dict) -> float:
    projects = profile.get("projects") or []
    description = (job.get("description") or job.get("title") or "").lower()
    if not projects:
        return 0.0
    score = 0.0
    for project in projects:
        words = [w.lower() for w in project.split() if len(w) > 3]
        hits = sum(1 for w in words if w in description)
        score = max(score, hits / max(len(words), 1))
    return min(score, 1.0)


def _recency(job: dict) -> float:
    posted = job.get("posted_date")
    if not posted:
        return 0.5
    if isinstance(posted, str):
        try:
            posted = datetime.fromisoformat(posted)
        except ValueError:
            return 0.5
    now = datetime.now(tz=timezone.utc)
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    days_old = (now - posted).days
    return max(0.0, 1.0 - days_old / 30)


def score_job(job: dict, profile: dict) -> dict:
    breakdown = {
        "project_overlap": _project_overlap(job, profile),
        "skill_match": _skill_match(job, profile),
        "role_match": _role_match(job, profile),
        "location_fit": _location_fit(job, profile),
        "recency": _recency(job),
    }
    total = sum(WEIGHTS[k] * v for k, v in breakdown.items())
    return {"score": round(total, 4), "breakdown": breakdown}


def rank_jobs(jobs: list[dict], profile: dict) -> list[dict]:
    passed: list[dict] = []

    for job in jobs:
        if not _hard_filter(job, profile):
            continue
        result = score_job(job, profile)
        job["score"] = result["score"]
        job["score_breakdown"] = result["breakdown"]
        passed.append(job)

    passed.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"[Ranker] {len(jobs)} jobs → {len(passed)} after hard filters, ranked.")
    return passed
