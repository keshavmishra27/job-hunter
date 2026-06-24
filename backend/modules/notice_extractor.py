import re
import io
from datetime import datetime
from urllib.parse import urljoin
from typing import Optional
from bs4 import BeautifulSoup
from loguru import logger


DATE_PATTERNS = [
    r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})",
    r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
]


def _find_dates(text: str) -> Optional[datetime]:
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            s = m.group(1)
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s.replace('-', '/'), fmt)
                except Exception:
                    continue
    return None


def _extract_links_from_soup(soup: BeautifulSoup, base_url: Optional[str] = None) -> list[dict]:
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        url = urljoin(base_url or "", href)
        text = a.get_text(" ", strip=True) or url
        kind = None
        low = url.lower()
        if "google.com/forms" in low or "forms.gle" in low or "docs.google.com/forms" in low:
            kind = "google_form"
        elif "apply" in low or "career" in low or "jobs" in low or "recruit" in low:
            kind = "portal"
        elif low.endswith(".pdf"):
            kind = "pdf"
        links.append({"url": url, "text": text, "kind": kind})
    return links


def parse_text_fields(text: str) -> dict:
    t = text or ""
    res = {
        "eligibility_text": None,
        "deadline": None,
        "stipend": None,
        "location": None,
        "raw_text": t,
        "links": [],
    }

    low = t.lower()
                            
    elig_triggers = ["3rd year", "3rd-year", "third year", "pre-final", "prefinal", "pre final", "3rd"]
    for trig in elig_triggers:
        if trig in low:
            res["eligibility_text"] = trig
            break

             
    st = re.search(r"(rs\.?\s?[\d,]+|₹\s?[\d,]+|stipend[:\s]\s?[\d,]+)", t, flags=re.I)
    if st:
        res["stipend"] = st.group(0)

              
    loc = re.search(r"(location[:\s]\s*([A-Za-z.,\s\-]+))", t, flags=re.I)
    if loc:
        res["location"] = loc.group(2).strip()

              
    d = _find_dates(t)
    if d:
        res["deadline"] = d

           
    urls = re.findall(r"https?://[\w\-\./?&=%#]+", t)
    for u in urls:
        kind = "portal" if any(k in u.lower() for k in ["apply", "career", "jobs", "forms.gle", "google.com/forms"]) else None
        res["links"].append({"url": u, "text": u, "kind": kind})

    return res


def extract_from_html(html: str, base_url: Optional[str] = None) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = None
    for sel in ("h1", "title", "h2"):
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break

                                   
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    body_text = "\n".join(paragraphs).strip() or soup.get_text(" ", strip=True)

    parsed = parse_text_fields(body_text)
    links = _extract_links_from_soup(soup, base_url=base_url)
                        
    existing_urls = {l["url"] for l in parsed["links"]}
    for l in links:
        if l["url"] not in existing_urls:
            parsed["links"].append(l)

    return {
        "title": title,
        "raw_text": parsed["raw_text"],
        "eligibility_text": parsed["eligibility_text"],
        "deadline": parsed["deadline"],
        "stipend": parsed["stipend"],
        "location": parsed["location"],
        "links": parsed["links"],
    }


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str | None:
                      
    try:
        from pdfminer.high_level import extract_text

        try:
            text = extract_text(io.BytesIO(pdf_bytes))
        except Exception:
                                                                               
            text = None
        if text:
            return text
    except Exception:
        pass

                
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                continue
        return "\n".join(pages)
    except Exception:
        logger.debug("No PDF parser available or failed to parse PDF")
        return None


def extract_from_pdf_bytes(pdf_bytes: bytes) -> dict:
    text = extract_text_from_pdf_bytes(pdf_bytes) or ""
    parsed = parse_text_fields(text)
    return {
        "title": None,
        "raw_text": parsed["raw_text"],
        "eligibility_text": parsed["eligibility_text"],
        "deadline": parsed["deadline"],
        "stipend": parsed["stipend"],
        "location": parsed["location"],
        "links": parsed["links"],
    }
