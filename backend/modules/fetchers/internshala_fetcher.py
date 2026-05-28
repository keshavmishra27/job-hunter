import re
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob

INTERNSHALA_BASE = "https://internshala.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class InternshalaFetcher(BaseFetcher):
    source_name = "Internshala"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []

        for keyword in keywords[:3]:
            kw_slug = keyword.replace(' ', '-').lower()
            loc_slug = location.replace(' ', '-').lower()
            
            if loc_slug == "remote":
                url = f"{INTERNSHALA_BASE}/internships/work-from-home-keywords-{kw_slug}/"
            elif loc_slug and loc_slug != "india":
                url = f"{INTERNSHALA_BASE}/internships/internship-in-{loc_slug}-keywords-{kw_slug}/"
            else:
                url = f"{INTERNSHALA_BASE}/internships/keywords-{kw_slug}/"
                
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
                # Updated selectors — Internshala changed their HTML in 2025
                title_el = (
                    card.select_one(".job-title-href")
                    or card.select_one(".job-internship-name a")
                    or card.select_one(".job-internship-name")
                    # Legacy fallbacks (kept for resilience)
                    or card.select_one(".profile a")
                    or card.select_one(".profile")
                )
                company_el = (
                    card.select_one(".company_name")
                    or card.select_one(".company-name")
                    or card.select_one(".company_and_premium")
                )
                location_el = (
                    card.select_one("#location_names")
                    or card.select_one("[class*='location']")
                    # Legacy fallbacks
                    or card.select_one(".location_link")
                    or card.select_one(".location")
                )
                type_el = card.select_one(".internship_other_details_container .item_body")
                link_el = (
                    card.select_one("a.job-title-href")
                    or card.select_one(".job-internship-name a")
                    or card.select_one(".profile a")
                )
                date_el = card.select_one(".status-inactive") or card.select_one(".status-success")
                stipend_el = card.select_one(".stipend")

                title = title_el.get_text(strip=True) if title_el else "Unknown"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                # Clean up "Actively hiring" badge text that's included inside .company_name
                company = re.sub(r'Actively\s*hiring', '', company).strip()
                location = location_el.get_text(strip=True) if location_el else None
                internship_type = type_el.get_text(strip=True) if type_el else None
                apply_link = (INTERNSHALA_BASE + link_el["href"]) if link_el and link_el.get("href") else None
                posted_date = self._safe_date(date_el.get_text(strip=True) if date_el else None)

                # Skip cards with empty/unknown titles
                if not title or title == "Unknown":
                    continue

                # Detect remote/WFH from location text
                loc_lower = (location or "").lower()
                mode = None
                if "work from home" in loc_lower or "remote" in loc_lower:
                    mode = "remote"
                elif "hybrid" in loc_lower:
                    mode = "hybrid"

                # Build description from available snippets
                desc_parts = []
                if stipend_el:
                    desc_parts.append(f"Stipend: {stipend_el.get_text(strip=True)}")
                if internship_type:
                    desc_parts.append(f"Duration: {internship_type}")
                description = " | ".join(desc_parts) if desc_parts else None

                extra = {}
                if mode:
                    extra["mode"] = mode

                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type=internship_type,
                    description=description,
                    apply_link=apply_link,
                    source=self.source_name,
                    posted_date=posted_date,
                    extra=extra,
                ))
            except Exception as e:
                logger.debug(f"[Internshala] card parse error: {e}")

        return jobs
