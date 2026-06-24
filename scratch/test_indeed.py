import httpx
from bs4 import BeautifulSoup
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

url = "https://in.indeed.com/jobs?q=internship&l=India&fromage=7"
resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
print(f"Status: {resp.status_code}")
print(f"Final URL: {resp.url}")
print(f"Content-Type: {resp.headers.get('content-type', '?')}")
print(f"Body size: {len(resp.text)} chars")

soup = BeautifulSoup(resp.text, "lxml")

                              
title = soup.title.get_text() if soup.title else "No title"
print(f"Page title: {title}")

                            
for sel in ["div.job_seen_beacon", "div[data-jk]", ".jobsearch-ResultsList", 
            ".mosaic-zone", "#mosaic-provider-jobcards", ".job_seen_beacon",
            "td.resultContent", ".resultContent", "a.jcs-JobTitle"]:
    items = soup.select(sel)
    if items:
        print(f"\n'{sel}': {len(items)} matches")

                        
scripts = soup.find_all("script", type="application/ld+json")
for s in scripts:
    try:
        data = json.loads(s.string)
        if isinstance(data, list):
            print(f"\nJSON-LD: {len(data)} items, type={data[0].get('@type', '?') if data else '?'}")
        else:
            print(f"\nJSON-LD type: {data.get('@type', '?')}")
    except:
        pass

                                        
for h in soup.select("h1, h2, h3"):
    text = h.get_text(strip=True)
    if text:
        print(f"Heading: {text}")

                          
with open("scratch/indeed_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("\nSaved to scratch/indeed_page.html")
