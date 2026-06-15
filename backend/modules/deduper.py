"""
Deduper — prevent the same opportunity from haunting the dashboard.

Uses three deduplication layers:
  1. Content hash (SHA-256 of title + company + location + link + desc head)
  2. Signature (title + company + location — catches minor link variations)
  3. Description similarity (character-trigram Jaccard — catches cross-source dupes)
"""
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
    company = _normalise(job.get("company") or job.get("organization") or "")
    location = _normalise(job.get("location") or "")
    return "|".join([title, company, location])


def job_fingerprint(job: dict) -> str:
    title = _normalise(job.get("title") or "")
    company = _normalise(job.get("company") or job.get("organization") or "")
    location = _normalise(job.get("location") or "")
    link = (job.get("apply_link") or "").lower().strip()
    desc_head = _normalise((job.get("description") or "")[:200])
    key = "|".join([title, company, location, link, desc_head])
    return hashlib.sha256(key.encode()).hexdigest()


def canonical_fingerprint(job: dict) -> str:
    """Computes a strict fingerprint without description, used for application tracking."""
    title = _normalise(job.get("title") or "")
    company = _normalise(job.get("company") or job.get("organization") or "")
    location = _normalise(job.get("location") or "")
    link = (job.get("apply_link") or "").lower().strip()
    key = "|".join([title, company, location, link])
    return hashlib.sha256(key.encode()).hexdigest()


# ─── Description Similarity ─────────────────────────────────────────────────

def _char_trigrams(text: str) -> set[str]:
    """Extract character trigrams from normalized text."""
    t = _normalise(text)
    if len(t) < 3:
        return {t} if t else set()
    return {t[i:i+3] for i in range(len(t) - 2)}


def description_similarity(desc_a: str | None, desc_b: str | None) -> float:
    """
    Quick character-trigram Jaccard similarity between two descriptions.
    Returns 0.0 to 1.0.
    """
    if not desc_a or not desc_b:
        return 0.0

    # Only compare first 500 chars to keep it fast
    tg_a = _char_trigrams(desc_a[:500])
    tg_b = _char_trigrams(desc_b[:500])

    if not tg_a or not tg_b:
        return 0.0

    intersection = len(tg_a & tg_b)
    union = len(tg_a | tg_b)
    return intersection / union if union > 0 else 0.0


# ─── Main Dedup ──────────────────────────────────────────────────────────────

def deduplicate(
    jobs: list[dict],
    existing_hashes: set[str] | None = None,
    existing_signatures: set[str] | None = None,
    *,
    use_description_similarity: bool = False,
    similarity_threshold: float = 0.85,
    existing_descriptions: list[str] | None = None,
) -> list[dict]:
    """
    Deduplicate a list of job dicts.

    Args:
        jobs: list of normalized job dicts
        existing_hashes: content hashes already in DB
        existing_signatures: signatures already in DB
        use_description_similarity: enable fuzzy description matching
        similarity_threshold: Jaccard threshold for description match
        existing_descriptions: descriptions from DB for cross-source dedup
    """
    seen_hashes: set[str] = set(existing_hashes or [])
    seen_signatures: set[str] = set(existing_signatures or [])
    unique: list[dict] = []
    unique_descriptions: list[str] = list(existing_descriptions or [])

    for job in jobs:
        signature = job_signature(job)
        h = job.get("fingerprint") or job_fingerprint(job)
        job["content_hash"] = h

        # Layer 1: exact content hash
        if h in seen_hashes:
            logger.debug(f"[Deduper] Hash duplicate: {job.get('title')} @ {job.get('company')}")
            continue

        # Layer 2: title + company + location signature
        if signature in seen_signatures:
            logger.debug(f"[Deduper] Signature duplicate: {job.get('title')} @ {job.get('company')}")
            continue

        # Layer 3: description similarity (for cross-source dedup)
        if use_description_similarity and unique_descriptions:
            desc = job.get("description") or ""
            is_desc_dupe = False
            for existing_desc in unique_descriptions:
                if description_similarity(desc, existing_desc) >= similarity_threshold:
                    logger.debug(
                        f"[Deduper] Description duplicate: {job.get('title')} @ {job.get('company')}"
                    )
                    is_desc_dupe = True
                    break
            if is_desc_dupe:
                continue

        seen_hashes.add(h)
        seen_signatures.add(signature)
        if job.get("description"):
            unique_descriptions.append(job["description"])
        unique.append(job)

    logger.info(
        f"[Deduper] {len(jobs)} → {len(unique)} after dedup "
        f"({len(jobs) - len(unique)} removed)"
    )
    return unique
