import httpx
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import unquote
import asyncio

from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob

class DuckDuckGoFetcher(BaseFetcher):
    source_name = "DuckDuckGo ATS"

    async def fetch(
        self,
        keywords: list[str],
        location: str = "",
        *,
        strategy: str | None = None,
        **kwargs,
    ) -> list[RawJob]:
        
        jobs = []
        dorks = [
            "site:boards.greenhouse.io",
            "site:jobs.lever.co",
            "site:jobs.ashbyhq.com",
            "site:apply.workable.com"
        ]
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            client.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            for keyword in keywords:
                for dork in dorks:
                    query = f"{dork} {keyword} {location}".strip()
                    try:
                        url = "https://html.duckduckgo.com/html/"
                        res = await client.post(url, data={"q": query})
                        res.raise_for_status()
                        
                        soup = BeautifulSoup(res.text, "html.parser")
                        results = soup.find_all("a", class_="result__snippet")
                        title_links = soup.find_all("a", class_="result__url")
                        title_elems = soup.find_all("a", class_="result__a")
                        
                        for i, result in enumerate(results):
                            if i >= len(title_links) or i >= len(title_elems):
                                break
                                
                            link = title_links[i].get("href", "")
                            if "uddg=" in link:
                                link = unquote(link.split("uddg=")[1].split("&")[0])
                            elif link.startswith("//"):
                                link = "https:" + link
                                
                            snippet = result.text.strip()
                            title = "Opportunity from Search"
                            company = "Unknown"
                            
                            title_elem = title_elems[i]
                            if title_elem:
                                full_title = title_elem.text.strip()
                                parts = full_title.split(" - ")
                                if len(parts) >= 2:
                                    title = parts[0].strip()
                                    company = parts[1].strip()
                                else:
                                    parts_pipe = full_title.split(" | ")
                                    if len(parts_pipe) >= 2:
                                        title = parts_pipe[0].strip()
                                        company = parts_pipe[1].strip()
                                    else:
                                        title = full_title
                            
                                                                          
                            if "job" not in link.lower() and link.count("/") < 4:
                                continue

                            jobs.append(
                                RawJob(
                                    title=title,
                                    company=company,
                                    location=location or "Remote/Flexible",
                                    internship_type="internship",
                                    description=snippet,
                                    apply_link=link,
                                    source=self.source_name,
                                )
                            )
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.warning(f"[{self.source_name}] Failed to fetch '{query}': {e}")
        
        return jobs
