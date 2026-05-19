import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
import asyncio

INDEED_BASE = "https://in.indeed.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

# Patterns that indicate a job listing has expired
EXPIRED_MARKERS = [
    "this job has expired",
    "this job is no longer available",
    "no longer accepting applications",
    "is not actively hiring",
]


class IndeedFetcher(BaseFetcher):
    source_name = "Indeed"

    async def fetch(self, keywords: list[str], location: str = "India") -> list[RawJob]:
        results: list[RawJob] = []
        query = " OR ".join(keywords[:3])
        url = f"{INDEED_BASE}/jobs?q={query.replace(' ', '+')}&l={location.replace(' ', '+')}&fromage=7"

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                cards = self._parse_cards(soup)
                logger.info(f"[Indeed] '{query}' → {len(cards)} cards found")

                # Fetch detail pages concurrently (max 5 at a time) to get
                # full descriptions and detect expired listings
                sem = asyncio.Semaphore(5)
                tasks = [self._enrich_card(client, card, sem) for card in cards]
                enriched = await asyncio.gather(*tasks, return_exceptions=True)

                for item in enriched:
                    if isinstance(item, Exception):
                        continue
                    if item is not None:
                        results.append(item)

                logger.info(f"[Indeed] '{query}' → {len(results)} valid (non-expired) listings")
        except Exception as e:
            logger.warning(f"[Indeed] fetch error: {e}")

        return results

    def _parse_cards(self, soup: BeautifulSoup) -> list[dict]:
        """Parse search result cards into intermediate dicts (not RawJob yet)."""
        cards_data = []
        cards = soup.select("div.job_seen_beacon") or soup.select("div[data-jk]")

        for card in cards[:20]:
            try:
                title_el = card.select_one("h2.jobTitle span")
                company_el = card.select_one("[data-testid='company-name']") or card.select_one(".companyName")
                location_el = card.select_one("[data-testid='text-location']") or card.select_one(".companyLocation")
                link_el = card.select_one("h2.jobTitle a")
                date_el = card.select_one("[data-testid='myJobsStateDate']") or card.select_one(".date")
                snippet_el = card.select_one(".job-snippet") or card.select_one(".jobsearch-JobComponent-description")

                title = title_el.get_text(strip=True) if title_el else "Unknown"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location = location_el.get_text(strip=True) if location_el else None
                href = link_el["href"] if link_el and link_el.get("href") else None
                apply_link = (INDEED_BASE + href) if href and href.startswith("/") else href
                posted_date = self._safe_date(date_el.get_text(strip=True) if date_el else None)
                snippet = snippet_el.get_text(strip=True) if snippet_el else None

                cards_data.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "apply_link": apply_link,
                    "posted_date": posted_date,
                    "snippet": snippet,
                })
            except Exception as e:
                logger.debug(f"[Indeed] card parse error: {e}")

        return cards_data

    async def _enrich_card(self, client: httpx.AsyncClient, card: dict, sem: asyncio.Semaphore) -> RawJob | None:
        """Fetch the detail page for a card to get full description and check expired status."""
        apply_link = card.get("apply_link")
        description = card.get("snippet")  # fallback if detail fetch fails

        if apply_link:
            try:
                async with sem:
                    resp = await client.get(apply_link, timeout=15)
                    if resp.status_code == 200:
                        detail_soup = BeautifulSoup(resp.text, "lxml")

                        # Check for expired banner
                        page_text = detail_soup.get_text(separator=" ").lower()
                        for marker in EXPIRED_MARKERS:
                            if marker in page_text:
                                logger.info(
                                    f"[Indeed] Skipping expired: {card['title']} @ {card['company']}"
                                )
                                return None  # Skip this job entirely

                        # Extract full job description
                        desc_el = (
                            detail_soup.select_one("#jobDescriptionText")
                            or detail_soup.select_one(".jobsearch-JobComponent-description")
                            or detail_soup.select_one("[data-testid='jobDescriptionText']")
                        )
                        if desc_el:
                            description = desc_el.get_text(separator="\n", strip=True)
            except Exception as e:
                logger.debug(f"[Indeed] detail fetch failed for {card['title']}: {e}")

        return RawJob(
            title=card["title"],
            company=card["company"],
            location=card["location"],
            internship_type=None,
            description=description,
            apply_link=apply_link,
            source=self.source_name,
            posted_date=card["posted_date"],
        )
