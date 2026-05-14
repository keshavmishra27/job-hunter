import asyncio
from loguru import logger

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
from backend.config import get_settings

settings = get_settings()


class LinkedInFetcher(BaseFetcher):
    source_name = "LinkedIn"

    async def fetch(self, keywords: list[str], location: str = "India") -> list[RawJob]:
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("[LinkedIn] Playwright not installed. Skipping.")
            return []

        results: list[RawJob] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            for keyword in keywords[:2]:
                try:
                    url = (
                        "https://www.linkedin.com/jobs/search/"
                        f"?keywords={keyword.replace(' ', '%20')}"
                        f"&location={location.replace(' ', '%20')}"
                        "&f_E=1&f_JT=I&sortBy=DD"
                    )
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(2)

                    cards = await page.query_selector_all(".job-search-card")
                    for card in cards[:15]:
                        try:
                            title = await (await card.query_selector(".base-search-card__title")).inner_text()
                            company = await (await card.query_selector(".base-search-card__subtitle")).inner_text()
                            location_el = await card.query_selector(".job-search-card__location")
                            location_text = await location_el.inner_text() if location_el else None
                            link_el = await card.query_selector("a.base-card__full-link")
                            link = await link_el.get_attribute("href") if link_el else None

                            results.append(RawJob(
                                title=title.strip(),
                                company=company.strip(),
                                location=location_text.strip() if location_text else None,
                                internship_type="Internship",
                                description=None,
                                apply_link=link,
                                source=self.source_name,
                            ))
                        except Exception as e:
                            logger.debug(f"[LinkedIn] card error: {e}")

                    logger.info(f"[LinkedIn] '{keyword}' → {len(results)} results so far")
                except Exception as e:
                    logger.warning(f"[LinkedIn] fetch error for '{keyword}': {e}")

            await browser.close()

        return results
