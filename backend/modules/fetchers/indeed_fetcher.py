import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob

INDEED_BASE = "https://in.indeed.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


class IndeedFetcher(BaseFetcher):
    source_name = "Indeed"

    async def fetch(self, keywords: list[str], location: str = "India") -> list[RawJob]:
        results: list[RawJob] = []
        query = " OR ".join(keywords[:3])
        url = f"{INDEED_BASE}/jobs?q={query.replace(' ', '+')}&l={location.replace(' ', '+')}&fromage=14"

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = self._parse_listings(soup)
            logger.info(f"[Indeed] '{query}' → {len(results)} listings")
        except Exception as e:
            logger.warning(f"[Indeed] fetch error: {e}")

        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        jobs = []
        cards = soup.select("div.job_seen_beacon") or soup.select("div[data-jk]")

        for card in cards[:20]:
            try:
                title_el = card.select_one("h2.jobTitle span")
                company_el = card.select_one("[data-testid='company-name']") or card.select_one(".companyName")
                location_el = card.select_one("[data-testid='text-location']") or card.select_one(".companyLocation")
                link_el = card.select_one("h2.jobTitle a")
                date_el = card.select_one("[data-testid='myJobsStateDate']") or card.select_one(".date")

                title = title_el.get_text(strip=True) if title_el else "Unknown"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location = location_el.get_text(strip=True) if location_el else None
                href = link_el["href"] if link_el and link_el.get("href") else None
                apply_link = (INDEED_BASE + href) if href and href.startswith("/") else href
                posted_date = self._safe_date(date_el.get_text(strip=True) if date_el else None)

                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type=None,
                    description=None,
                    apply_link=apply_link,
                    source=self.source_name,
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[Indeed] card parse error: {e}")

        return jobs
