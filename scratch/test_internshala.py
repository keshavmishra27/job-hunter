import httpx
from bs4 import BeautifulSoup
import sys
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Check Internshala more details - mode, stipend, etc.
url = "https://internshala.com/internships/keywords-internship"
resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
soup = BeautifulSoup(resp.text, "lxml")

cards = soup.select(".individual_internship")
print(f"Total Internshala cards: {len(cards)}")

for i, card in enumerate(cards[:3]):
    print(f"\n=== CARD {i} ===")
    # title
    title_el = card.select_one(".job-title-href") or card.select_one(".job-internship-name")
    title = title_el.get_text(strip=True) if title_el else "Unknown"
    print(f"  Title: {title}")
    
    # company  
    company_el = card.select_one(".company_name") or card.select_one(".company-name")
    company = company_el.get_text(strip=True) if company_el else "Unknown"
    print(f"  Company: {company}")
    
    # location - try multiple
    loc_el = card.select_one("#location_names") or card.select_one("[class*='location']")
    location = loc_el.get_text(strip=True) if loc_el else None
    print(f"  Location: {location}")
    
    # link
    link_el = card.select_one("a.job-title-href")
    href = link_el["href"] if link_el and link_el.get("href") else None
    print(f"  Link: {href}")
    
    # mode (work from home indicator)
    mode_el = card.select_one(".work_from_home") or card.select_one("[class*='work_from']")
    print(f"  WFH indicator: {mode_el.get_text(strip=True) if mode_el else 'None'}")
    
    # type (part-time / full-time)
    type_el = card.select_one(".internship_other_details_container .item_body")
    print(f"  Type: {type_el.get_text(strip=True) if type_el else 'None'}")
    
    # Stipend
    stipend_el = card.select_one(".stipend")
    print(f"  Stipend: {stipend_el.get_text(strip=True) if stipend_el else 'None'}")

    # Status/date
    date_el = card.select_one(".status-inactive") or card.select_one(".status-success")
    print(f"  Status: {date_el.get_text(strip=True) if date_el else 'None'}")

    # Actively hiring?
    hiring = card.select_one(".actively-hiring-badge") or card.select_one("[class*='actively']")
    print(f"  Actively hiring: {hiring.get_text(strip=True) if hiring else 'No'}")

# Now test Indeed
print("\n\n=== INDEED TEST ===")
url = "https://in.indeed.com/jobs?q=internship&l=India&fromage=7"
resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
soup = BeautifulSoup(resp.text, "lxml")

cards = soup.select("div.job_seen_beacon") or soup.select("div[data-jk]")
print(f"Total Indeed cards: {len(cards)}")

for i, card in enumerate(cards[:3]):
    title_el = card.select_one("h2.jobTitle span")
    company_el = card.select_one("[data-testid='company-name']") or card.select_one(".companyName")
    loc_el = card.select_one("[data-testid='text-location']") or card.select_one(".companyLocation")
    print(f"  [{i}] {title_el.get_text(strip=True) if title_el else 'Unknown'} @ {company_el.get_text(strip=True) if company_el else 'Unknown'} | {loc_el.get_text(strip=True) if loc_el else '?'}")
