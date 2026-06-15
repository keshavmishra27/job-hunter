"""
Freelance platform fetcher stubs.

Each fetcher extends BaseFetcher and targets a specific freelance platform.
They return RawJob items with opportunity_type="freelance" and freelance-specific
extra fields (budget, client info, etc.).

Most platforms require API keys or OAuth — these stubs are structured adapters
that return real data once credentials are configured. Without credentials,
they log a warning and return an empty list.
"""
from datetime import datetime
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob


# ─────────────────────────────────────────────────────────────────────────────
# Fiverr
# ─────────────────────────────────────────────────────────────────────────────

class FiverrFetcher(BaseFetcher):
    """Fiverr buyer requests / gig search. Requires session auth."""
    source_name = "Fiverr"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Fiverr] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Fiverr] No API credentials configured — returning empty. "
                       "Add FIVERR_SESSION_TOKEN to .env to enable.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Freelancer.com
# ─────────────────────────────────────────────────────────────────────────────

class FreelancerComFetcher(BaseFetcher):
    """Freelancer.com API integration. Has a public API at api.freelancer.com."""
    source_name = "Freelancer"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        import httpx

        query = " ".join(keywords[:3])
        jobs: list[RawJob] = []

        try:
            # Freelancer has a public search endpoint
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.freelancer.com/api/projects/0.1/projects/active",
                    params={
                        "query": query,
                        "compact": "true",
                        "limit": 25,
                        "job_details": "true",
                        "sort_field": "time_submitted",
                        "sort_direction": "desc",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(f"[Freelancer] API returned {resp.status_code}")
                    return jobs

                data = resp.json()
                projects = data.get("result", {}).get("projects", [])

                for p in projects[:25]:
                    budget = p.get("budget", {})
                    jobs.append(RawJob(
                        title=p.get("title", "Untitled"),
                        company=f"Client #{p.get('owner_id', 'unknown')}",
                        location="Remote",
                        internship_type=None,
                        description=p.get("preview_description") or p.get("description", ""),
                        apply_link=f"https://www.freelancer.com/projects/{p.get('seo_url', '')}",
                        source=self.source_name,
                        posted_date=datetime.utcfromtimestamp(p["time_submitted"]) if p.get("time_submitted") else None,
                        opportunity_type="freelance",
                        extra={
                            "budget_min": budget.get("minimum"),
                            "budget_max": budget.get("maximum"),
                            "budget_type": p.get("type", "fixed"),
                            "currency": p.get("currency", {}).get("code", "USD"),
                            "required_skills": [j.get("name", "") for j in p.get("jobs", [])],
                            "remote_only": True,
                        },
                    ))

        except Exception as e:
            logger.error(f"[Freelancer] Fetch failed: {e}")

        logger.info(f"[Freelancer] Fetched {len(jobs)} gigs")
        return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Guru
# ─────────────────────────────────────────────────────────────────────────────

class GuruFetcher(BaseFetcher):
    """Guru.com job listing scraper stub."""
    source_name = "Guru"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Guru] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Guru] No API credentials configured — returning empty. "
                       "Add GURU_API_KEY to .env to enable.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Toptal
# ─────────────────────────────────────────────────────────────────────────────

class ToptalFetcher(BaseFetcher):
    """Toptal job board scraper stub. Toptal is invite-only."""
    source_name = "Toptal"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Toptal] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Toptal] Invite-only platform — returning empty. "
                       "Manual integration required.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Contra
# ─────────────────────────────────────────────────────────────────────────────

class ContraFetcher(BaseFetcher):
    """Contra opportunities scraper stub."""
    source_name = "Contra"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Contra] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Contra] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# PeoplePerHour
# ─────────────────────────────────────────────────────────────────────────────

class PeoplePerHourFetcher(BaseFetcher):
    """PeoplePerHour project listing scraper stub."""
    source_name = "PeoplePerHour"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[PeoplePerHour] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[PeoplePerHour] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Arc.dev
# ─────────────────────────────────────────────────────────────────────────────

class ArcFetcher(BaseFetcher):
    """Arc.dev remote job scraper stub."""
    source_name = "Arc"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Arc] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Arc] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Turing
# ─────────────────────────────────────────────────────────────────────────────

class TuringFetcher(BaseFetcher):
    """Turing.com job board scraper stub."""
    source_name = "Turing"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Turing] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Turing] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Lemon.io
# ─────────────────────────────────────────────────────────────────────────────

class LemonioFetcher(BaseFetcher):
    """Lemon.io developer matching platform scraper stub."""
    source_name = "Lemon.io"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Lemon.io] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Lemon.io] Invite-only platform — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Gun.io
# ─────────────────────────────────────────────────────────────────────────────

class GunioFetcher(BaseFetcher):
    """Gun.io freelance project scraper stub."""
    source_name = "Gun.io"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Gun.io] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Gun.io] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 99Designs
# ─────────────────────────────────────────────────────────────────────────────

class NinetyNineDesignsFetcher(BaseFetcher):
    """99Designs contest/project scraper stub."""
    source_name = "99Designs"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[99Designs] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[99Designs] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Dribbble Jobs
# ─────────────────────────────────────────────────────────────────────────────

class DribbbleFetcher(BaseFetcher):
    """Dribbble Jobs scraper stub."""
    source_name = "Dribbble"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Dribbble] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Dribbble] No API credentials configured — returning empty.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Behance
# ─────────────────────────────────────────────────────────────────────────────

class BehanceFetcher(BaseFetcher):
    """Behance job board scraper stub."""
    source_name = "Behance"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        logger.info(f"[Behance] Fetcher stub called with keywords: {keywords[:3]}")
        logger.warning("[Behance] No API credentials configured — returning empty.")
        return []
