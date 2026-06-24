import httpx
from bs4 import BeautifulSoup
from loguru import logger
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
from backend.modules.deduper import canonical_fingerprint
import asyncio

INDEED_BASE = "https://in.indeed.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

                                                  
EXPIRED_MARKERS = [
    "this job has expired",
    "this job is no longer available",
    "no longer accepting applications",
    "is not actively hiring",
]


class IndeedFetcher(BaseFetcher):
    source_name = "Indeed"

    async def fetch(self, keywords: list[str], location: str = "India", **kwargs) -> list[RawJob]:
        results: list[RawJob] = []
                                                                               
                                                                              
        force_refresh: bool = kwargs.get("force_refresh", False)
        applied_fingerprints = set() if force_refresh else kwargs.get("applied_fingerprints", set())
        applied_urls = set() if force_refresh else kwargs.get("applied_urls", set())
        if force_refresh:
            logger.info("[Indeed] force_refresh=True — bypassing applied fingerprint cache")
        seen_in_run = set()

                                    
        is_remote = location.lower() == "remote"
        base_location = location if not is_remote else "India"
        remote_param = "&sc=0kf%3Aattr%28DSQF7%29%3B" if is_remote else ""

        import urllib.parse
        
                       
        def build_url(query_keys, loc, start=0):
                                                                          
            quoted_keys = [f'"{k}"' if ' ' in k else k for k in query_keys[:3]]
            query = " OR ".join(quoted_keys)
            encoded_query = urllib.parse.quote_plus(query)
            encoded_loc = urllib.parse.quote_plus(loc)
            return f"{INDEED_BASE}/jobs?q={encoded_query}&l={encoded_loc}&fromage=14&start={start}{remote_param}"

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                
                                                           
                                                       
                                                      
                                                                   
                
                fallbacks = [
                    (keywords, base_location),
                    ([k for k in keywords if len(k) > 4][:2], base_location),                   
                ]
                if not is_remote and base_location != "India":
                    fallbacks.append(([k for k in keywords if len(k) > 4][:2], "India"))
                
                for attempt, (current_keywords, current_location) in enumerate(fallbacks):
                    if not current_keywords:
                        continue
                        
                    logger.info(f"[Indeed] Attempt {attempt} with keywords: {current_keywords}, location: {current_location}")
                    
                    start = 0
                    max_pages = 5
                    fresh_jobs_needed = 10
                    
                    while start < max_pages * 10:
                        url = build_url(current_keywords, current_location, start)
                        try:
                            resp = await client.get(url)
                            if resp.status_code == 403:
                                logger.warning(f"[Indeed] 403 Forbidden for {url}. Breaking pagination for this attempt.")
                                break
                            resp.raise_for_status()
                        except Exception as e:
                            logger.warning(f"[Indeed] Request failed for {url}: {e}")
                            break
                            
                        soup = BeautifulSoup(resp.text, "lxml")
                        cards = self._parse_cards(soup)
                        logger.info(f"[Indeed] Page {start//10} → {len(cards)} cards found")
                        
                        if not cards:
                            break
                            
                                                                   
                        to_enrich = []
                        for card in cards:
                                                  
                            temp_job = {
                                "title": card["title"],
                                "company": card["company"],
                                "location": card["location"],
                                "apply_link": card["apply_link"]
                            }
                            fingerprint = canonical_fingerprint(temp_job)
                            card["fingerprint"] = fingerprint
                            
                                         
                            if fingerprint in applied_fingerprints:
                                logger.debug(f"[Indeed] Skipped (Applied): {card['title']} at {card['company']}")
                                continue
                            if card["apply_link"] in applied_urls:
                                logger.debug(f"[Indeed] Skipped (Applied URL): {card['title']} at {card['company']}")
                                continue
                            if fingerprint in seen_in_run:
                                continue
                                
                            seen_in_run.add(fingerprint)
                            to_enrich.append(card)
                        
                        logger.info(f"[Indeed] Enriching {len(to_enrich)} fresh non-applied jobs")
                        
                        if to_enrich:
                            sem = asyncio.Semaphore(3)                                      
                            tasks = [self._enrich_card(client, card, sem) for card in to_enrich]
                            enriched = await asyncio.gather(*tasks, return_exceptions=True)
                            
                            added_in_page = 0
                            for item in enriched:
                                if isinstance(item, Exception) or item is None:
                                    continue
                                results.append(item)
                                added_in_page += 1
                                
                        if len(results) >= fresh_jobs_needed:
                            break
                            
                                                                                 
                        start += 10
                        await asyncio.sleep(1)                               
                    
                    if len(results) >= fresh_jobs_needed:
                                                                
                        break
                        
        except Exception as e:
            logger.warning(f"[Indeed] Global fetch error: {e}")

        logger.info(f"[Indeed] Total valid jobs retrieved: {len(results)}")
        return results

    def _parse_cards(self, soup: BeautifulSoup) -> list[dict]:
        """Parse search result cards into intermediate dicts (not RawJob yet)."""
        cards_data = []
        cards = soup.select("div.job_seen_beacon") or soup.select("div[data-jk]")

        for card in cards[:20]:
            try:
                title_el = (
                    card.select_one("h2.jobTitle span")
                    or card.select_one("a.jcs-JobTitle span")
                    or card.select_one("a.jcs-JobTitle")
                    or card.select_one("h2.jobTitle")
                )
                company_el = card.select_one("[data-testid='company-name']") or card.select_one(".companyName")
                location_el = card.select_one("[data-testid='text-location']") or card.select_one(".companyLocation")
                link_el = card.select_one("h2.jobTitle a") or card.select_one("a.jcs-JobTitle")
                date_el = card.select_one("[data-testid='myJobsStateDate']") or card.select_one(".date")
                snippet_el = card.select_one(".job-snippet") or card.select_one(".jobsearch-JobComponent-description")

                title = title_el.get_text(strip=True) if title_el else "Unknown"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location = location_el.get_text(strip=True) if location_el else None
                
                                                    
                jk = card.get("data-jk")
                href = link_el["href"] if link_el and link_el.get("href") else None
                
                if jk:
                    apply_link = f"{INDEED_BASE}/viewjob?jk={jk}"
                else:
                    apply_link = (INDEED_BASE + href) if href and href.startswith("/") else href
                    
                posted_date = self._safe_date(date_el.get_text(strip=True) if date_el else None)
                snippet = snippet_el.get_text(strip=True) if snippet_el else None

                                                      
                if not title or title == "Unknown":
                    continue
                    
                                                               
                if not apply_link:
                    continue

                cards_data.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "apply_link": apply_link,
                    "posted_date": posted_date,
                    "snippet": snippet,
                    "job_id": jk,
                })
            except Exception as e:
                logger.debug(f"[Indeed] card parse error: {e}")

        return cards_data

    async def _enrich_card(self, client: httpx.AsyncClient, card: dict, sem: asyncio.Semaphore) -> RawJob | None:
        """Fetch the detail page for a card to get full description and check expired status."""
        apply_link = card.get("apply_link")
        description = card.get("snippet")                                  

        if apply_link:
            try:
                async with sem:
                    resp = await client.get(apply_link, timeout=15)
                    if resp.status_code == 200:
                        detail_soup = BeautifulSoup(resp.text, "lxml")

                                                  
                        page_text = detail_soup.get_text(separator=" ").lower()
                        for marker in EXPIRED_MARKERS:
                            if marker in page_text:
                                logger.info(
                                    f"[Indeed] Skipping expired: {card['title']} @ {card['company']}"
                                )
                                return None                          

                                                      
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
            canonical_url=apply_link,
            fingerprint=card["fingerprint"],
            source=self.source_name,
            posted_date=card["posted_date"],
            extra={"source_job_id": card.get("job_id")}
        )
