"""
Upwork Fetcher — fetches freelance gigs from Upwork RSS feeds.

Upwork provides public RSS feeds for job searches that don't require API keys.
Feed URL: https://www.upwork.com/ab/feed/jobs/rss?q={keyword}&sort=recency
"""
import re
from datetime import datetime
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob


class UpworkFetcher(BaseFetcher):
    source_name = "Upwork"
    RSS_URL = "https://www.upwork.com/ab/feed/jobs/rss"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        import httpx

        jobs: list[RawJob] = []
        query = " ".join(keywords[:3])

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(self.RSS_URL, params={"q": query, "sort": "recency"})
                if resp.status_code != 200:
                    logger.warning(f"[Upwork] RSS feed returned {resp.status_code}")
                    return jobs

                               
                text = resp.text
                items = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)

                for item in items[:30]:
                    title = _xml_tag(item, "title") or "Untitled"
                    link = _xml_tag(item, "link") or ""
                    description = _xml_tag(item, "description") or ""
                    pub_date = _xml_tag(item, "pubDate")

                                                     
                    budget_min, budget_max, budget_type = _parse_upwork_budget(description)

                                                     
                    skills = _parse_upwork_skills(description)

                    posted = None
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            posted = parsedate_to_datetime(pub_date)
                        except Exception:
                            pass

                    jobs.append(RawJob(
                        title=_clean_html(title),
                        company="Upwork Client",
                        location="Remote",
                        internship_type=None,
                        description=_clean_html(description),
                        apply_link=link,
                        source=self.source_name,
                        posted_date=posted,
                        opportunity_type="freelance",
                        extra={
                            "budget_min": budget_min,
                            "budget_max": budget_max,
                            "budget_type": budget_type,
                            "currency": "USD",
                            "required_skills": skills,
                            "remote_only": True,
                            "payment_verified": True,                     
                        },
                    ))

        except Exception as e:
            logger.error(f"[Upwork] Fetch failed: {e}")

        logger.info(f"[Upwork] Fetched {len(jobs)} gigs for query: {query}")
        return jobs


def _xml_tag(xml: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)
    if m:
        content = m.group(1).strip()
        if content.startswith("<![CDATA["):
            content = content[9:]
        if content.endswith("]]>"):
            content = content[:-3]
        return content
    return None


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_upwork_budget(desc: str) -> tuple[float | None, float | None, str | None]:
    text = desc.lower()
                                                     
    hourly = re.search(r"hourly\s*range?\s*:?\s*\$?([\d,.]+)\s*-\s*\$?([\d,.]+)", text)
    if hourly:
        return float(hourly.group(1).replace(",", "")), float(hourly.group(2).replace(",", "")), "hourly"

    fixed = re.search(r"budget\s*:?\s*\$?([\d,.]+)\s*-\s*\$?([\d,.]+)", text)
    if fixed:
        return float(fixed.group(1).replace(",", "")), float(fixed.group(2).replace(",", "")), "fixed"

    single = re.search(r"budget\s*:?\s*\$?([\d,.]+)", text)
    if single:
        val = float(single.group(1).replace(",", ""))
        return val, val, "fixed"

    return None, None, None


def _parse_upwork_skills(desc: str) -> list[str]:
    m = re.search(r"skills?\s*:?\s*(.*?)(?:\n|<br|$)", desc, re.IGNORECASE)
    if m:
        raw = _clean_html(m.group(1))
        skills = [s.strip() for s in raw.split(",") if s.strip()]
        return skills[:10]
    return []
