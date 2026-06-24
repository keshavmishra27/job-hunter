import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _text(el):
    return el.get_text(strip=True) if el else None


def _absolute_link(base: str, href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith("http"):
        return href
    return base.rstrip("/") + "/" + href.lstrip("/")


class LinkedInFetcher(BaseFetcher):
    """
    Replaces NaukriFetcher — LinkedIn public job search returns full SSR HTML
    (59 cards confirmed), no auth or CAPTCHA required.
    Registered under the 'naukri' key so the frontend button needs no change.
    """
    source_name = "LinkedIn"
    BASE_URL = "https://www.linkedin.com"
    SEARCH_URL = "https://www.linkedin.com/jobs/search"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async def fetch(self, keywords: list[str], location: str = "India", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
                                                                               
        query = " OR ".join(keywords[:2])
        params = {
            "keywords": query,
            "location": location or "India",
            "f_JT": "I",                                  
            "trk": "public_jobs_jobs-search-bar_search-submit",
        }
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=25, follow_redirects=True
            ) as client:
                resp = await client.get(self.SEARCH_URL, params=params)
                resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = self._parse_listings(soup)
            logger.info(f"[LinkedIn] '{query}' → {len(results)} internship listings")
        except Exception as e:
            logger.warning(f"[LinkedIn] fetch error: {e}")
        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        cards = soup.select(".base-card") or soup.select(".job-search-card")
        jobs: list[RawJob] = []
        for card in cards[:25]:
            try:
                title_el = card.select_one(".base-search-card__title")
                company_el = card.select_one(".base-search-card__subtitle")
                location_el = card.select_one(".job-search-card__location")
                link_el = card.select_one(".base-card__full-link") or card.select_one("a[href]")

                title = _text(title_el)
                company = _text(company_el) or "Unknown"
                location = _text(location_el)
                apply_link = link_el.get("href") if link_el else None

                if not title:
                    continue

                                               
                loc_lower = (location or "").lower()
                mode_extra: dict = {}
                if "remote" in loc_lower or "work from home" in loc_lower:
                    mode_extra["mode"] = "remote"
                elif "hybrid" in loc_lower:
                    mode_extra["mode"] = "hybrid"

                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type="Internship",
                    description=None,
                    apply_link=apply_link,
                    source=self.source_name,
                    extra=mode_extra,
                ))
            except Exception as e:
                logger.debug(f"[LinkedIn] card parse error: {e}")
        return jobs

                                      
    def _parse_json(self, data: dict) -> list[RawJob]:
        return []



class FounditFetcher(BaseFetcher):
    source_name = "Foundit"
    BASE_URL = "https://www.foundit.in"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
        for keyword in keywords[:3]:
            query = keyword.replace(" ", "+")
            url = f"{self.BASE_URL}/jobs?keywords={query}"
            try:
                async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                results.extend(self._parse_listings(soup))
                logger.info(f"[Foundit] '{keyword}' → {len(results)} listings so far")
            except Exception as e:
                logger.warning(f"[Foundit] fetch error for '{keyword}': {e}")
        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        cards = soup.select(".job-card") or soup.select(".srp-card") or soup.select("article")
        jobs: list[RawJob] = []
        for card in cards[:20]:
            try:
                title_el = card.select_one("a") or card.select_one(".job-title")
                company_el = card.select_one(".company") or card.select_one(".company-name")
                location_el = card.select_one(".location") or card.select_one(".job-location")
                desc_el = card.select_one(".description") or card.select_one(".job-desc")
                title = _text(title_el)
                company = _text(company_el) or "Unknown"
                location = _text(location_el)
                description = _text(desc_el)
                apply_link = title_el["href"] if title_el and title_el.has_attr("href") else None
                if apply_link and apply_link.startswith("/"):
                    apply_link = _absolute_link(self.BASE_URL, apply_link)
                if not title:
                    continue
                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type=None,
                    description=description,
                    apply_link=apply_link,
                    source=self.source_name,
                ))
            except Exception as e:
                logger.debug(f"[Foundit] card parse error: {e}")
        return jobs


class FreshersworldFetcher(BaseFetcher):
    source_name = "Freshersworld"
    BASE_URL = "https://www.freshersworld.com"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
        for keyword in keywords[:3]:
                                                                                      
            slug = keyword.replace(" ", "-").lower()
            url = f"{self.BASE_URL}/internship-jobs/keyword-{slug}/all-cities"
            try:
                async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                results.extend(self._parse_listings(soup))
                logger.info(f"[Freshersworld] '{keyword}' → {len(results)} listings so far")
            except Exception as e:
                logger.warning(f"[Freshersworld] fetch error for '{keyword}': {e}")
        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
                                                                              
        cards = (
            soup.select(".jobs-list-item")
            or soup.select(".job-container")
            or soup.select(".job-block")
            or soup.select(".freshersblock")
            or soup.select("[data-jobid]")
        )
        jobs: list[RawJob] = []
        for card in cards[:20]:
            try:
                title_el = (
                    card.select_one(".job-title a")
                    or card.select_one(".position a")
                    or card.select_one("h3 a")
                    or card.select_one("a")
                )
                company_el = (
                    card.select_one(".company-name")
                    or card.select_one(".company")
                    or card.select_one(".org")
                )
                location_el = (
                    card.select_one(".location")
                    or card.select_one(".job-location")
                    or card.select_one(".loc")
                )
                desc_el = card.select_one(".description") or card.select_one(".job-summary")
                title = _text(title_el)
                company = _text(company_el) or "Unknown"
                location = _text(location_el)
                description = _text(desc_el)
                apply_link = title_el["href"] if title_el and title_el.has_attr("href") else None
                if apply_link and apply_link.startswith("/"):
                    apply_link = _absolute_link(self.BASE_URL, apply_link)
                if not title:
                    continue
                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type=None,
                    description=description,
                    apply_link=apply_link,
                    source=self.source_name,
                ))
            except Exception as e:
                logger.debug(f"[Freshersworld] card parse error: {e}")
        return jobs


class CutshortFetcher(BaseFetcher):
    source_name = "Cutshort"
    BASE_URL = "https://cutshort.io"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
        for keyword in keywords[:3]:
            query = keyword.replace(" ", "+")
                                                                      
            slug = keyword.replace(" ", "-").lower()
            url = f"{self.BASE_URL}/jobs/{slug}-jobs"
            try:
                async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                results.extend(self._parse_listings(soup))
                logger.info(f"[Cutshort] '{keyword}' → {len(results)} listings so far")
            except Exception as e:
                logger.warning(f"[Cutshort] fetch error for '{keyword}': {e}")
        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        jobs: list[RawJob] = []
                                                                                              
        job_links = [
            a for a in soup.select("a[href]")
            if "/job/" in (a.get("href") or "")
        ]
        seen: set[str] = set()
        for link_el in job_links[:20]:
            try:
                href = link_el["href"]
                if href in seen:
                    continue
                seen.add(href)
                apply_link = _absolute_link(self.BASE_URL, href)
                title = _text(link_el).strip()
                if not title or len(title) < 3:
                    continue
                                                                             
                parent = link_el.find_parent(["li", "div", "article"])
                company = "Unknown"
                if parent:
                    company_el = parent.select_one(".company") or parent.select_one(".company-name")
                    if company_el:
                        company = _text(company_el) or "Unknown"
                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=None,
                    internship_type="Internship",
                    description=None,
                    apply_link=apply_link,
                    source=self.source_name,
                ))
            except Exception as e:
                logger.debug(f"[Cutshort] card parse error: {e}")
        return jobs


class WellfoundFetcher(BaseFetcher):
    """Wellfound (formerly AngelList Talent) — startup jobs.

    Strategy: Wellfound is a Next.js app.  The initial SSR HTML embeds
    job listing data in a <script id="__NEXT_DATA__"> JSON blob.  We
    extract that JSON directly — no JavaScript execution required.

    If the site returns 403 (blocked), we gracefully skip.
    """
    source_name = "Wellfound"
    BASE_URL = "https://wellfound.com"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        "Referer": "https://wellfound.com/",
    }

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        import json as _json
        results: list[RawJob] = []
        query = " ".join(keywords[:2])
        url = f"{self.BASE_URL}/jobs"
        params = {"q": query, "job_types": "Internship"}
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=25, follow_redirects=True
            ) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 403:
                    logger.warning("[Wellfound] 403 Forbidden — site is blocking scrapers")
                    return []
                resp.raise_for_status()

                                          
            soup = BeautifulSoup(resp.text, "lxml")
            next_data_tag = soup.select_one('script#__NEXT_DATA__')
            if next_data_tag and next_data_tag.string:
                try:
                    data = _json.loads(next_data_tag.string)
                    results = self._parse_next_data(data)
                    logger.info(f"[Wellfound] __NEXT_DATA__ → {len(results)} listings")
                except _json.JSONDecodeError:
                    logger.warning("[Wellfound] __NEXT_DATA__ JSON decode failed")

                                                                           
            if not results:
                results = self._parse_html(soup)
                logger.info(f"[Wellfound] HTML fallback → {len(results)} listings")

        except httpx.HTTPStatusError as e:
            logger.warning(f"[Wellfound] HTTP {e.response.status_code}: {e}")
        except Exception as e:
            logger.warning(f"[Wellfound] fetch error: {e}")
        return results

    def _parse_next_data(self, data: dict) -> list[RawJob]:
        """Extract jobs from __NEXT_DATA__ props."""
        jobs: list[RawJob] = []
        try:
                                                                     
            props = data.get("props", {}).get("pageProps", {})
            listings = (
                props.get("listings")
                or props.get("jobs")
                or props.get("results")
                or props.get("initialData", {}).get("results", [])
            )
            if not isinstance(listings, list):
                return []

            for item in listings[:25]:
                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("job_title")
                )
                if not title:
                    continue
                company = (
                    item.get("company", {}).get("name")
                    if isinstance(item.get("company"), dict)
                    else item.get("company_name", "Unknown")
                )
                location = item.get("location") or item.get("remote", "")
                slug = item.get("slug") or item.get("id", "")
                apply_link = f"{self.BASE_URL}/jobs/{slug}" if slug else None
                description = item.get("description") or item.get("snippet")
                jobs.append(RawJob(
                    title=title,
                    company=company or "Unknown",
                    location=location if isinstance(location, str) else None,
                    internship_type="Internship",
                    description=description[:500] if description else None,
                    apply_link=apply_link,
                    source=self.source_name,
                ))
        except Exception as e:
            logger.debug(f"[Wellfound] __NEXT_DATA__ parse error: {e}")
        return jobs

    def _parse_html(self, soup: BeautifulSoup) -> list[RawJob]:
        """Fallback: parse job cards from rendered HTML."""
        jobs: list[RawJob] = []
        cards = (
            soup.select('[data-test="JobListing"]')
            or soup.select('.styles_component__card')
            or soup.select('[class*="job-listing"]')
            or soup.select('div[class*="JobCard"]')
        )
        for card in cards[:25]:
            try:
                title_el = card.select_one('a') or card.select_one('h2')
                title = _text(title_el)
                if not title:
                    continue
                company_el = card.select_one('[class*="company"]') or card.select_one('h3')
                company = _text(company_el) or "Unknown"
                link_el = card.select_one('a[href]')
                apply_link = _absolute_link(self.BASE_URL, link_el.get('href')) if link_el else None
                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=None,
                    internship_type="Internship",
                    description=None,
                    apply_link=apply_link,
                    source=self.source_name,
                ))
            except Exception as e:
                logger.debug(f"[Wellfound] HTML card parse error: {e}")
        return jobs


class WorkAtAStartupFetcher(BaseFetcher):
    source_name = "WorkAtAStartup"
    BASE_URL = "https://www.workatastartup.com"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
                                                                                
        url = f"{self.BASE_URL}/internships"
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results.extend(self._parse_listings(soup))
            logger.info(f"[WorkAtAStartup] /internships → {len(results)} listings")
        except Exception as e:
            logger.warning(f"[WorkAtAStartup] fetch error: {e}")
        return results

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
                                                                             
        cards = (
            soup.select(".company-listing")
            or soup.select(".job-card")
            or soup.select(".job-listing")
            or soup.select("article")
        )
        jobs: list[RawJob] = []
        for card in cards[:20]:
            try:
                title_el = card.select_one("h2") or card.select_one(".job-name") or card.select_one("a")
                company_el = card.select_one(".company-name") or card.select_one(".company") or card.select_one("h3")
                location_el = card.select_one(".location") or card.select_one(".job-location")
                desc_el = card.select_one(".description") or card.select_one(".job-summary")
                link_el = card.select_one("a[href]")
                title = _text(title_el)
                company = _text(company_el) or "Unknown"
                location = _text(location_el)
                description = _text(desc_el)
                apply_link = link_el["href"] if link_el and link_el.has_attr("href") else None
                if apply_link and apply_link.startswith("/"):
                    apply_link = _absolute_link(self.BASE_URL, apply_link)
                if not title:
                    continue
                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type="Internship",
                    description=description,
                    apply_link=apply_link,
                    source=self.source_name,
                ))
            except Exception as e:
                logger.debug(f"[WorkAtAStartup] card parse error: {e}")
        return jobs


                                                                               
                                                                     
                                          
                                                                               

import re

                                                                          
                                              
DEFAULT_TELEGRAM_CHANNELS = [
    ("JobsAndInternshipsIndia", "Jobs & Internships India"),
    ("internshipsalert",        "Internships Alert"),
    ("internship_update",       "Internship Update"),
    ("HiringIndia",             "Hiring India"),
    ("TechJobsIndia",           "Tech Jobs India"),
]

                                                                  
INTERN_KEYWORDS = {
    "intern", "internship", "trainee", "training", "fresher",
    "final year", "pre-final", "3rd year", "hiring", "apply now",
    "stipend", "opportunity", "openings", "off campus",
}

                                                
APPLY_LINK_HINTS = {"apply", "form", "careers", "jobs", "join", "application", "internship"}


class TelegramChannelFetcher(BaseFetcher):
    """
    Scrapes public Telegram channels via https://t.me/s/<channel>.
    No authentication or bot token needed — uses Telegram's public web preview.
    Filters only messages that look like internship notices and extracts apply links.
    """
    source_name = "Telegram"
    BASE_URL = "https://t.me/s"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, channels: list[tuple[str, str]] | None = None):
        self.channels = channels or DEFAULT_TELEGRAM_CHANNELS

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
        async with httpx.AsyncClient(headers=self.HEADERS, timeout=20, follow_redirects=True) as client:
            for username, display_name in self.channels:
                try:
                    url = f"{self.BASE_URL}/{username}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"[Telegram] {username} → HTTP {resp.status_code}")
                        continue
                    soup = BeautifulSoup(resp.content, "lxml")                                             
                    jobs = self._parse_channel(soup, username, display_name)
                    results.extend(jobs)
                    logger.info(f"[Telegram] @{username} → {len(jobs)} notices")
                except Exception as e:
                    logger.warning(f"[Telegram] @{username} fetch error: {e}")
        return results

    def _parse_channel(self, soup: BeautifulSoup, username: str, display_name: str) -> list[RawJob]:
        messages = soup.select(".tgme_widget_message")
        jobs: list[RawJob] = []

        for msg in messages:
            try:
                text_el = msg.select_one(".tgme_widget_message_text")
                if not text_el:
                    continue
                raw_text = text_el.get_text(separator="\n", strip=True)
                if not self._is_internship_notice(raw_text):
                    continue

                                                  
                apply_link = None
                all_links = []
                for a in text_el.select("a[href]"):
                    href = a.get("href", "")
                    if not href or href.startswith("tg://"):
                        continue
                    link_text = a.get_text(strip=True).lower()
                    href_lower = href.lower()
                    if any(h in href_lower or h in link_text for h in APPLY_LINK_HINTS):
                        if apply_link is None:
                            apply_link = href
                    all_links.append(href)

                                                                 
                if not apply_link and all_links:
                    apply_link = all_links[0]

                                                                             
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                title = self._extract_title(lines)
                if not title:
                    continue

                company = self._extract_company(lines, raw_text)
                location_str = self._extract_location(raw_text)

                                
                extra: dict = {}
                low = raw_text.lower()
                if "remote" in low or "wfh" in low or "work from home" in low:
                    extra["mode"] = "remote"
                elif "hybrid" in low:
                    extra["mode"] = "hybrid"

                                     
                msg_link_el = msg.select_one(".tgme_widget_message_date")
                source_link = msg_link_el.get("href") if msg_link_el and msg_link_el.has_attr("href") else None

                jobs.append(RawJob(
                    title=title,
                    company=company or display_name,
                    location=location_str,
                    internship_type="Internship",
                    description=raw_text[:1000],                            
                    apply_link=apply_link or source_link,
                    source=f"Telegram/{username}",
                    extra={**extra, "channel": username, "source_link": source_link or ""},
                ))
            except Exception as e:
                logger.debug(f"[Telegram] @{username} message parse error: {e}")

        return jobs

    def _is_internship_notice(self, text: str) -> bool:
        low = text.lower()
        return any(kw in low for kw in INTERN_KEYWORDS)

    def _extract_title(self, lines: list[str]) -> str | None:
        """Use the first short line that looks like a role title."""
        for line in lines[:5]:
            clean = re.sub(r"[^a-zA-Z0-9 /\-&]", "", line).strip()
            if 4 < len(clean) < 80 and not clean.startswith("http"):
                return clean
        return None

    def _extract_company(self, lines: list[str], text: str) -> str | None:
        """Look for '@CompanyName' or 'at XYZ' patterns."""
        m = re.search(r"\bat\s+([A-Z][A-Za-z0-9\s&.\-]{2,40})", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"@([A-Za-z0-9_]{3,30})", text)
        if m:
            return m.group(1)
        return None

    def _extract_location(self, text: str) -> str | None:
        """Detect city names or remote keywords."""
        cities = ["bangalore", "mumbai", "delhi", "hyderabad", "chennai", "pune",
                  "kolkata", "noida", "gurgaon", "remote", "india", "pan india"]
        low = text.lower()
        for city in cities:
            if city in low:
                return city.title()
        return None


                                                                               
                               
                                                                               

class _GenericJobBoardFetcher(BaseFetcher):
    """
    Base for remote-first / startup job boards that serve SSR HTML.
    Subclasses only need to set source_name, BASE_URL, and SEARCH_PATTERN.
    """

    CARD_SELECTORS: list[str] = [
        ".job-card", ".job-listing", ".job-post", "article",
        "[data-job-id]", ".posting", ".position-card", ".card",
    ]
    TITLE_SELECTORS: list[str] = [
        ".job-title", ".posting-title", ".position-title",
        "h2", "h3", "a[href*='/job']", "a[href*='/position']", "a",
    ]
    COMPANY_SELECTORS: list[str] = [
        ".company-name", ".company", ".org-name", ".employer",
    ]
    LOCATION_SELECTORS: list[str] = [
        ".location", ".job-location", ".loc",
    ]
    DESC_SELECTORS: list[str] = [
        ".description", ".job-summary", ".excerpt", ".snippet",
    ]

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
        for keyword in keywords[:3]:
            url = self._build_search_url(keyword, location)
            try:
                async with httpx.AsyncClient(headers=HEADERS, timeout=25, follow_redirects=True) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                parsed = self._parse_listings(soup)
                results.extend(parsed)
                logger.info(f"[{self.source_name}] '{keyword}' → {len(parsed)} listings")
            except Exception as e:
                logger.warning(f"[{self.source_name}] fetch error for '{keyword}': {e}")
        return results

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/jobs?q={query}"

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        cards = None
        for sel in self.CARD_SELECTORS:
            cards = soup.select(sel)
            if cards:
                break
        if not cards:
            return []

        jobs: list[RawJob] = []
        for card in cards[:25]:
            try:
                title = self._find_text(card, self.TITLE_SELECTORS)
                if not title or len(title) < 3:
                    continue
                company = self._find_text(card, self.COMPANY_SELECTORS) or "Unknown"
                location = self._find_text(card, self.LOCATION_SELECTORS)
                description = self._find_text(card, self.DESC_SELECTORS)
                apply_link = self._find_link(card)

                extra: dict = {}
                loc_lower = (location or "").lower()
                if "remote" in loc_lower or "wfh" in loc_lower:
                    extra["mode"] = "remote"
                elif "hybrid" in loc_lower:
                    extra["mode"] = "hybrid"

                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=location,
                    internship_type=None,
                    description=description,
                    apply_link=apply_link,
                    source=self.source_name,
                    extra=extra,
                ))
            except Exception as e:
                logger.debug(f"[{self.source_name}] card parse error: {e}")
        return jobs

    def _find_text(self, card, selectors: list[str]) -> str | None:
        for sel in selectors:
            el = card.select_one(sel)
            if el:
                t = _text(el)
                if t:
                    return t
        return None

    def _find_link(self, card) -> str | None:
        for a in card.select("a[href]"):
            href = a.get("href", "")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                return _absolute_link(self.BASE_URL, href)
        return None


class ArcJobsFetcher(_GenericJobBoardFetcher):
    """Arc.dev — remote developer jobs."""
    source_name = "Arc.dev"
    BASE_URL = "https://arc.dev"

    def _build_search_url(self, keyword: str, location: str) -> str:
        slug = keyword.replace(" ", "-").lower()
        return f"{self.BASE_URL}/remote-jobs/{slug}"


class HimalayasFetcher(BaseFetcher):
    """Himalayas — remote-first job board with a FREE public JSON API.

    API docs: https://himalayas.app/jobs/api
    No authentication or API key required.
    Supports filtering by employment_type=Intern for internships.
    """
    source_name = "Himalayas"
    API_URL = "https://himalayas.app/jobs/api"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
        seen_ids: set[str] = set()

        for keyword in keywords[:3]:
            params = {
                "q": keyword,
                "limit": 20,
                "offset": 0,
            }
            try:
                async with httpx.AsyncClient(
                    headers=HEADERS, timeout=20, follow_redirects=True
                ) as client:
                    resp = await client.get(self.API_URL, params=params)
                    resp.raise_for_status()
                data = resp.json()
                jobs_list = data.get("jobs") or data.get("results") or []
                for item in jobs_list:
                    job_id = str(item.get("id", ""))
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    title = item.get("title") or item.get("name")
                    if not title:
                        continue

                    company_name = (
                        item.get("companyName")
                        or (item.get("company", {}).get("name") if isinstance(item.get("company"), dict) else None)
                        or item.get("company_name")
                        or "Unknown"
                    )
                    loc = item.get("location") or ""
                    if isinstance(loc, list):
                        loc = ", ".join(loc)

                    slug = item.get("slug") or item.get("id", "")
                    apply_link = item.get("applicationLink") or item.get("url")
                    if not apply_link and slug:
                        apply_link = f"https://himalayas.app/jobs/{slug}"

                    description = item.get("excerpt") or item.get("description") or ""
                    if len(description) > 500:
                        description = description[:500]

                                    
                    extra: dict = {}
                    emp_type = (item.get("employmentType") or item.get("employment_type") or "").lower()
                    if "remote" in loc.lower() or item.get("remote"):
                        extra["mode"] = "remote"

                    results.append(RawJob(
                        title=title,
                        company=company_name,
                        location=loc or "Remote",
                        internship_type=emp_type if emp_type else None,
                        description=description,
                        apply_link=apply_link,
                        source=self.source_name,
                        extra=extra,
                    ))
                logger.info(f"[Himalayas] '{keyword}' → {len(jobs_list)} jobs from API")
            except Exception as e:
                logger.warning(f"[Himalayas] API error for '{keyword}': {e}")

        return results


class OttaFetcher(_GenericJobBoardFetcher):
    """Otta — curated tech & startup jobs."""
    source_name = "Otta"
    BASE_URL = "https://app.otta.com"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
                                                                        
                                                            
        logger.warning(
            "[Otta] Skipping fetch — site is a fully client-rendered SPA. "
            "Configure Otta API credentials for job access."
        )
        return []


class TuringJobsFetcher(_GenericJobBoardFetcher):
    """Turing — remote software developer jobs."""
    source_name = "Turing"
    BASE_URL = "https://www.turing.com"

    def _build_search_url(self, keyword: str, location: str) -> str:
        slug = keyword.replace(" ", "-").lower()
        return f"{self.BASE_URL}/remote-developer-jobs/s/{slug}"


class LandingJobsFetcher(_GenericJobBoardFetcher):
    """Landing.jobs — European tech jobs."""
    source_name = "LandingJobs"
    BASE_URL = "https://landing.jobs"

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/jobs?q={query}"


class PangianFetcher(_GenericJobBoardFetcher):
    """Pangian — remote work community & job board."""
    source_name = "Pangian"
    BASE_URL = "https://pangian.com"

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/job-travel-remote?q={query}"


class PowerToFlyFetcher(_GenericJobBoardFetcher):
    """PowerToFly — diversity-focused remote & flexible jobs."""
    source_name = "PowerToFly"
    BASE_URL = "https://powertofly.com"

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/jobs?search={query}"


class AndelaFetcher(_GenericJobBoardFetcher):
    """Andela — global talent marketplace for remote engineers."""
    source_name = "Andela"
    BASE_URL = "https://andela.com"

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/jobs?q={query}"


class DeelCareersFetcher(_GenericJobBoardFetcher):
    """Deel — global payroll platform career listings."""
    source_name = "Deel"
    BASE_URL = "https://www.deel.com"

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/careers?search={query}"


class TrueUpFetcher(_GenericJobBoardFetcher):
    """TrueUp — startup job aggregator."""
    source_name = "TrueUp"
    BASE_URL = "https://www.trueup.io"

    def _build_search_url(self, keyword: str, location: str) -> str:
        query = keyword.replace(" ", "+")
        return f"{self.BASE_URL}/jobs?q={query}"
