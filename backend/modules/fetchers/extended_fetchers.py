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

    async def fetch(self, keywords: list[str], location: str = "India") -> list[RawJob]:
        results: list[RawJob] = []
        # Fetch once combining top 2 keywords — LinkedIn search handles OR well
        query = " OR ".join(keywords[:2])
        params = {
            "keywords": query,
            "location": location or "India",
            "f_JT": "I",           # Job type = Internship
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

                # Infer mode from location text
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

    # Kept for interface compatibility
    def _parse_json(self, data: dict) -> list[RawJob]:
        return []



class FounditFetcher(BaseFetcher):
    source_name = "Foundit"
    BASE_URL = "https://www.foundit.in"

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
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

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
        results: list[RawJob] = []
        for keyword in keywords[:3]:
            # Freshersworld slug-based URL: more reliable than ?searchkey= query param
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
        # Freshersworld renders server-side; try multiple known card selectors
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

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
        results: list[RawJob] = []
        for keyword in keywords[:3]:
            query = keyword.replace(" ", "+")
            # Use the slug URL format for better server-side rendering
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
        # Cutshort is JS-rendered; the SSR shell exposes job links in <a href="/job/..."> tags
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
                # Company is often in the sibling/parent text; try to grab it
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
    source_name = "Wellfound"
    BASE_URL = "https://wellfound.com"

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
        # Wellfound blocks unauthenticated scrapers with 403 Forbidden.
        # This source is disabled until a valid auth token or API key is available.
        logger.warning(
            "[Wellfound] Skipping fetch — site returns 403 for unauthenticated requests. "
            "Configure a session cookie or use the Wellfound API instead."
        )
        return []

    def _parse_listings(self, soup: BeautifulSoup) -> list[RawJob]:
        return []


class WorkAtAStartupFetcher(BaseFetcher):
    source_name = "WorkAtAStartup"
    BASE_URL = "https://www.workatastartup.com"

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
        results: list[RawJob] = []
        # The /search endpoint returns 404; use /internships browse page instead
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
        # Page is partially SSR; try known card and company-listing selectors
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


# ─────────────────────────────────────────────────────────────────────────────
# Telegram public channel scraper — uses t.me/s/<channel> web preview
# No bot token or authentication required.
# ─────────────────────────────────────────────────────────────────────────────

import re

# Curated list of active public Telegram channels with internship notices.
# Each entry: (channel_username, display_name)
DEFAULT_TELEGRAM_CHANNELS = [
    ("JobsAndInternshipsIndia", "Jobs & Internships India"),
    ("internshipsalert",        "Internships Alert"),
    ("internship_update",       "Internship Update"),
    ("HiringIndia",             "Hiring India"),
    ("TechJobsIndia",           "Tech Jobs India"),
]

# Keywords that signal an internship notice (message-level filter)
INTERN_KEYWORDS = {
    "intern", "internship", "trainee", "training", "fresher",
    "final year", "pre-final", "3rd year", "hiring", "apply now",
    "stipend", "opportunity", "openings", "off campus",
}

# Keywords that indicate a link is an apply link
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

    async def fetch(self, keywords: list[str], location: str = "") -> list[RawJob]:
        results: list[RawJob] = []
        async with httpx.AsyncClient(headers=self.HEADERS, timeout=20, follow_redirects=True) as client:
            for username, display_name in self.channels:
                try:
                    url = f"{self.BASE_URL}/{username}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"[Telegram] {username} → HTTP {resp.status_code}")
                        continue
                    soup = BeautifulSoup(resp.content, "lxml")  # use .content (bytes) for correct encoding
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

                # Extract apply links from message
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

                # Fallback: use first external link as apply link
                if not apply_link and all_links:
                    apply_link = all_links[0]

                # Infer title from first non-empty line (often the role name)
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                title = self._extract_title(lines)
                if not title:
                    continue

                company = self._extract_company(lines, raw_text)
                location_str = self._extract_location(raw_text)

                # Mode detection
                extra: dict = {}
                low = raw_text.lower()
                if "remote" in low or "wfh" in low or "work from home" in low:
                    extra["mode"] = "remote"
                elif "hybrid" in low:
                    extra["mode"] = "hybrid"

                # Source channel link
                msg_link_el = msg.select_one(".tgme_widget_message_date")
                source_link = msg_link_el.get("href") if msg_link_el and msg_link_el.has_attr("href") else None

                jobs.append(RawJob(
                    title=title,
                    company=company or display_name,
                    location=location_str,
                    internship_type="Internship",
                    description=raw_text[:1000],  # cap at 1000 chars for DB
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
