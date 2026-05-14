import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob

INTERNSHALA_BASE = "https://internshala.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class InternshalaFetcher(BaseFetcher):
    source_name = "Internshala"

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
        results: list[RawJob] = []

        for keyword in keywords[:3]:
            url = f"{INTERNSHALA_BASE}/internships/keywords-{keyword.replace(' ', '-').lower()}"
            try:
                async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                results.extend(self._parse_listings(soup))
                logger.info(f"[Internshala] '{keyword}' → {len(results)} listings so far")
            except Exception as e:
                logger.warning(f"[Internshala] fetch error for '{keyword}': {e}")

        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        jobs = []
        cards = soup.select(".individual_internship")

        for card in cards[:20]:
            try:
                title_el = card.select_one(".profile a") or card.select_one(".profile")
                company_el = card.select_one(".company_name a") or card.select_one(".company_name")
                location_el = card.select_one(".location_link") or card.select_one(".location")
                type_el = card.select_one(".internship_other_details_container .item_body")
                link_el = card.select_one(".profile a")
                date_el = card.select_one(".status-inactive")

                title = title_el.get_text(strip=True) if title_el else "Unknown"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location = location_el.get_text(strip=True) if location_el else None
                internship_type = type_el.get_text(strip=True) if type_el else None
                apply_link = (INTERNSHALA_BASE + link_el["href"]) if link_el and link_el.get("href") else None
                posted_date = self._safe_date(date_el.get_text(strip=True) if date_el else None)

                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type=internship_type,
                    description=None,
                    apply_link=apply_link,
                    source=self.source_name,
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[Internshala] card parse error: {e}")

        return jobs
