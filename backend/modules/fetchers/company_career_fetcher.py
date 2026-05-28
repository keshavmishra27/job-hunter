import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.config import get_settings
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob


class CompanyCareerFetcher(BaseFetcher):
    source_name = "CompanyCareers"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        """Fetch configured company career pages for internship-like listings."""
        results: list[RawJob] = []
        settings = get_settings()
        company_hosts = settings.company_career_hosts or []
        common_paths = ["/careers", "/careers/internships", "/jobs", "/careers/jobs"]

        if not company_hosts:
            logger.warning("[CompanyCareers] no company_career_hosts configured; skipping company career fetch")
            return results

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for host in company_hosts:
                base = host.rstrip("/")
                for path in common_paths:
                    url = base + path
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            continue
                        soup = BeautifulSoup(resp.text, "lxml")
                        cards = soup.select("a, .job, .opening, li")[:30]
                        for card in cards:
                            text = card.get_text(strip=True)
                            href = card.get("href") or card.get("data-href")
                            if not text:
                                continue
                            if any(k in text.lower() for k in ("intern", "internship", "internships")):
                                link = None
                                if href:
                                    link = href if href.startswith("http") else base + href
                                results.append(RawJob(
                                    title=text[:200],
                                    company=base,
                                    location=None,
                                    internship_type=None,
                                    description=None,
                                    apply_link=link,
                                    source=self.source_name,
                                ))
                        logger.info(f"[CompanyCareers] scanned {url} → found {len(results)} candidates so far")
                    except Exception as e:
                        logger.debug(f"[CompanyCareers] error fetching {url}: {e}")

        return results
