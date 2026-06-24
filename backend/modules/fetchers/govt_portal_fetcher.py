import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.config import get_settings
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob


class GovtPortalFetcher(BaseFetcher):
    source_name = "GovtPortal"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        """Scaffold for semi-structured government portals: find PDF links and announcement pages.
        Returns RawJob entries with the PDF or announcement link in `apply_link`.
        """
        results: list[RawJob] = []
        settings = get_settings()
        sample_portals = settings.govt_portal_urls or []

        if not sample_portals:
            logger.warning("[GovtPortal] no govt_portal_urls configured; skipping government portal fetch")
            return results

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for portal in sample_portals:
                try:
                    resp = await client.get(portal)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "lxml")
                                                              
                    links = soup.select("a[href]")[:60]
                    for a in links:
                        href = a.get("href")
                        text = a.get_text(strip=True) or "Notice"
                        if not href:
                            continue
                        if href.lower().endswith(".pdf") or "circular" in text.lower() or "notification" in text.lower():
                            link = href if href.startswith("http") else portal.rstrip("/") + "/" + href.lstrip("/")
                            results.append(RawJob(
                                title=text[:200],
                                company="Government",
                                location=None,
                                internship_type=None,
                                description=None,
                                apply_link=link,
                                source=self.source_name,
                            ))
                    logger.info(f"[GovtPortal] scanned {portal} → {len(results)} candidates so far")
                except Exception as e:
                    logger.debug(f"[GovtPortal] fetch error {portal}: {e}")

        return results
