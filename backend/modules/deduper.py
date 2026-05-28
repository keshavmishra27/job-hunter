import hashlib
import re
from loguru import logger


def _normalise(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def job_signature(job: dict) -> str:
    title = _normalise(job.get("title") or "")
    company = _normalise(job.get("company") or "")
    location = _normalise(job.get("location") or "")
    return "|".join([title, company, location])


def job_fingerprint(job: dict) -> str:
    title = _normalise(job.get("title") or "")
    company = _normalise(job.get("company") or "")
    location = _normalise(job.get("location") or "")
    link = (job.get("apply_link") or "").lower().strip()
    desc_head = _normalise((job.get("description") or "")[:200])
    key = "|".join([title, company, location, link, desc_head])
    return hashlib.sha256(key.encode()).hexdigest()


def canonical_fingerprint(job: dict) -> str:
    """Computes a strict fingerprint without description, used for application tracking."""
    title = _normalise(job.get("title") or "")
    company = _normalise(job.get("company") or "")
    location = _normalise(job.get("location") or "")
    link = (job.get("apply_link") or "").lower().strip()
    key = "|".join([title, company, location, link])
    return hashlib.sha256(key.encode()).hexdigest()


def deduplicate(
    jobs: list[dict],
    existing_hashes: set[str] | None = None,
    existing_signatures: set[str] | None = None,
) -> list[dict]:
    seen_hashes: set[str] = set(existing_hashes or [])
    seen_signatures: set[str] = set(existing_signatures or [])
    unique: list[dict] = []

    for job in jobs:
        signature = job_signature(job)
        h = job_fingerprint(job)
        job["content_hash"] = h

        if h in seen_hashes or signature in seen_signatures:
            logger.debug(f"[Deduper] Skipping duplicate: {job['title']} @ {job['company']}")
            continue

        seen_hashes.add(h)
        seen_signatures.add(signature)
        unique.append(job)

    logger.info(f"[Deduper] {len(jobs)} → {len(unique)} after dedup ({len(jobs) - len(unique)} removed)")
    return unique
