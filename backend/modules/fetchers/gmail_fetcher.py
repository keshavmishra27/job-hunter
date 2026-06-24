"""
Gmail Inbox Fetcher — IMAP-based internship mail scanner.

Connects to Gmail via IMAP SSL, filters internship-related emails,
parses company/role/link details, and produces RawJob objects that
plug directly into the existing normalize → score → dedup pipeline.

Uses only Python stdlib: imaplib, email, html.parser — zero new deps.
"""

import imaplib
import email as email_lib
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from loguru import logger

from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
from backend.config import get_settings


                                                                                

SUBJECT_KEYWORDS = {
                         
    "internship", "intern", "trainee", "stipend", "off campus",
                                                                         
    "job", "jobs", "career", "opportunity", "apply", "hiring",
    "vacancy", "vacancies", "opening", "openings", "recruitment",
    "placement", "fresher", "freshers", "walk-in", "walkin",
    "position", "role", "joining", "offer letter", "shortlist",
    "selected", "job fair", "campus drive", "off-campus",
    "data entry", "developer", "engineer", "analyst", "designer",
    "work from home", "wfh", "remote",
}

BODY_KEYWORDS = {
    "apply now", "apply here", "apply before", "apply by",
    "application link", "portal", "deadline", "last date",
    "selected", "shortlist", "shortlisted", "register",
    "walk-in", "walkin", "google form", "eligibility",
    "stipend", "salary", "ctc", "lpa", "per month",
    "job description", "key responsibilities", "requirements",
    "experience required", "qualification", "resume", "cv",
    "interview", "job role", "join us", "we are hiring",
    "immediate joining", "urgent requirement", "openings",
}

SENDER_HINTS = {
    "careers", "hr", "recruit", "hiring", "talent", "noreply",
    "jobs", "placement", "internship", "campus", "no-reply",
    "info", "alert", "notification", "updates", "team",
}

                                                                                       
                                                                                            
TRUSTED_PORTAL_BRANDS = {
    "naukri", "indeed", "foundit", "linkedin", "glassdoor",
    "monster", "shine", "iimjobs", "instahyre", "cutshort",
    "wellfound", "angel", "hirist", "freshersworld", "apna",
    "internshala", "letsintern", "hirect", "workindia", "rozgaar",
    "timesjobs", "careerbuilder", "simplyhired", "ziprecruiter",
    "dice", "snaphunt", "lever", "greenhouse", "workday", "icims",
    "smartrecruiters", "ashbyhq", "breezy",
}

def _is_trusted_sender(email_addr: str) -> bool:
    """Check if sender is from a known job portal (substring match on domain)."""
    domain = _sender_domain(email_addr)
    return any(brand in domain for brand in TRUSTED_PORTAL_BRANDS)

                        
JUNK_LINK_PATTERNS = {
    "unsubscribe", "manage preferences", "opt-out", "optout",
    "mailto:", "tel:", "javascript:", "#", "privacy-policy",
    "privacy", "terms", "login", "signin", "sign-in",
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com/company", "youtube.com",
    "tracking", "click.email", "click.mailer",
    "list-manage.com", "mailchimp.com",
}

                                                  
APPLY_LINK_HINTS = {
    "apply", "careers", "jobs", "forms.google", "internship",
    "recruit", "application", "register", "join", "form",
    "greenhouse.io", "lever.co", "workday.com", "icims.com",
    "smartrecruiters.com", "ashbyhq.com",
    "naukri.com", "indeed.com", "foundit.in", "internshala.com",
}


                                                                                

class _LinkExtractor(HTMLParser):
    """Extract all <a href> links from HTML content."""

    def __init__(self):
        super().__init__()
        self.links: list[dict] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attr_dict = dict(attrs)
            href = attr_dict.get("href", "")
            if href:
                self._current_href = href
                self._current_text = []

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href is not None:
            self.links.append({
                "url": self._current_href,
                "text": " ".join(self._current_text).strip(),
            })
            self._current_href = None
            self._current_text = []


class _TextExtractor(HTMLParser):
    """Extract plain text from HTML, stripping tags."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.parts)


                                                                                

def _decode_header_value(raw: str | None) -> str:
    """Decode RFC 2047 encoded header values."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


def _get_body(msg: email_lib.message.Message) -> tuple[str, str]:
    """
    Extract (plain_text, html_text) from a MIME message.
    Handles multipart and single-part messages.
    """
    plain = ""
    html = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if content_type == "text/plain" and not plain:
                    plain = text
                elif content_type == "text/html" and not html:
                    html = text
            except Exception:
                continue
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    html = text
                else:
                    plain = text
        except Exception:
            pass

    return plain, html


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text using stdlib parser."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.get_text()


def _extract_links_from_html(html: str) -> list[dict]:
    """Extract all links from HTML body."""
    extractor = _LinkExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.links


def _is_junk_link(url: str) -> bool:
    """Check if a URL is a tracking/junk/navigation link."""
    low = url.lower()
    return any(pat in low for pat in JUNK_LINK_PATTERNS)


def _extract_apply_link(links: list[dict]) -> str | None:
    """
    From a list of extracted links, find the most likely 'apply' URL.
    Ignores junk links. Prefers links matching APPLY_LINK_HINTS.
    Falls back to first external link.
    """
    preferred: list[str] = []
    external: list[str] = []

    for link in links:
        url = link.get("url", "")
        if not url or not url.startswith(("http://", "https://")):
            continue
        if _is_junk_link(url):
            continue

                              
        if any(pat in url.lower() for pat in [
            "subscriptions.indeed.com", "support.indeed.com", "indeed.com/legal", "indeed.onelink.me",
            "/hp?co=", "/messages?", "/notifications?", "indeed.com/jobs?q=", "cm.naukri.com",
            "unsubscribe", "manage-preferences", "privacy-policy"
        ]):
            continue

        url_lower = url.lower()
        text_lower = (link.get("text") or "").lower()

        if any(h in url_lower or h in text_lower for h in APPLY_LINK_HINTS):
            preferred.append(url)
        else:
            external.append(url)

    return preferred[0] if preferred else (external[0] if external else None)


def _sender_domain(email_addr: str) -> str:
    """Extract domain from email address."""
    if "@" in email_addr:
        return email_addr.split("@")[-1].lower()
    return ""


                                                                                

def _is_internship_mail(subject: str, sender: str, body_text: str, has_links: bool) -> bool:
    """
    Decide if an email is job/internship-related.
    - Emails from TRUSTED_JOB_PORTALS auto-pass (signal = 99).
    - Otherwise requires at least 2 signal matches from:
      subject keywords, sender hints, body keywords, external links.
    """
    signals = 0
    subj_low = subject.lower()
    sender_low = sender.lower()
    body_low = body_text.lower()

                                                                               
                                                
    if _is_trusted_sender(sender):
        if any(kw in subj_low for kw in SUBJECT_KEYWORDS) or "alert" in subj_low or "digest" in subj_low or "matching" in subj_low or "recommended" in subj_low:
            return True

    has_subj = any(kw in subj_low for kw in SUBJECT_KEYWORDS)
    has_sender = any(h in sender_low for h in SENDER_HINTS)
    has_body = any(kw in body_low for kw in BODY_KEYWORDS)

    if has_subj:
        signals += 1
    if has_sender:
        signals += 1
    if has_body:
        signals += 1
    if has_links:
        signals += 1

                                                          
    if not (has_subj or has_body):
        return False

    return signals >= 2


                                                                                

def _clean_subject(subject: str) -> str:
    """Remove Re:, Fwd:, [tags] prefixes from subject line."""
    cleaned = re.sub(r"^(?:(?:Re|Fwd|FW|Fw)\s*:\s*)+", "", subject, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^\[.*?\]\s*", "", cleaned).strip()
    return cleaned


def _extract_company_from_sender(from_header: str) -> str:
    """Extract company name from the From header display name or domain."""
    display_name, email_addr = parseaddr(from_header)

    if display_name:
                               
        name = re.sub(r"\s*(Careers|Hiring|HR|Recruitment|Jobs|Team|Inc\.?|Ltd\.?|Pvt\.?)$", "", display_name, flags=re.IGNORECASE).strip()
        if name and len(name) > 1:
            return name

                                   
    if email_addr:
        domain = email_addr.split("@")[-1] if "@" in email_addr else ""
                                                     
        company_part = domain.split(".")[0] if domain else ""
        if company_part and company_part not in ("gmail", "yahoo", "outlook", "hotmail", "mail", "noreply"):
            return company_part.replace("-", " ").replace("_", " ").title()

    return "Unknown"


def _extract_location(text: str) -> str | None:
    """Detect city names or remote keywords from email text."""
    cities = [
        "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "chennai",
        "pune", "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad",
        "jaipur", "lucknow", "chandigarh", "indore", "kochi", "trivandrum",
        "remote", "pan india", "work from home",
    ]
    low = text.lower()
    for city in cities:
        if city in low:
            return city.replace("bengaluru", "Bangalore").title()
    return None


def _extract_deadline(text: str) -> datetime | None:
    """Try to find a deadline date in the email text."""
                                                                                                
    patterns = [
        r"(?:deadline|last\s*date|apply\s*(?:before|by))\s*[:\-]?\s*(\d{1,2}[\s/\-]\w+[\s/\-]\d{4})",
        r"(?:deadline|last\s*date|apply\s*(?:before|by))\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"(?:deadline|last\s*date|apply\s*(?:before|by))\s*[:\-]?\s*(\w+\s+\d{1,2},?\s*\d{4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            date_str = m.group(1).strip()
            for fmt in ("%d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%B %d %Y", "%d %b %Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
    return None


def _infer_mode(text: str) -> str:
    """Detect work mode from email text."""
    low = text.lower()
    if any(k in low for k in ("remote", "work from home", "wfh", "virtual")):
        return "remote"
    if "hybrid" in low:
        return "hybrid"
    return "offline"


                                                                                

class GmailFetcher(BaseFetcher):
    """
    Scans Gmail inbox via IMAP, filters internship-related mails,
    extracts company/role/link details, and produces RawJob objects.

    Requires GMAIL_USER and GMAIL_APP_PASSWORD in settings.
    """
    source_name = "Gmail"

    async def fetch(self, keywords: list[str], location: str = "", **kwargs) -> list[RawJob]:
        """
        Fetch internship-related emails from Gmail inbox.
        Runs IMAP in a thread to avoid blocking the async event loop.
        """
        settings = get_settings()

        if not settings.gmail_user or not settings.gmail_app_password:
            logger.warning("[Gmail] No credentials configured — skipping inbox scan. "
                           "Set GMAIL_USER and GMAIL_APP_PASSWORD in .env")
            return []

        import asyncio
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None,
                self._fetch_sync,
                settings.gmail_user,
                settings.gmail_app_password,
                settings.gmail_imap_host,
                settings.gmail_imap_port,
                settings.gmail_days_back,
            )
            logger.info(f"[Gmail] Fetched {len(results)} internship notices from inbox")
            return results
        except Exception as e:
            logger.error(f"[Gmail] Fetch failed: {e}")
            return []

    def _fetch_sync(
        self,
        user: str,
        password: str,
        host: str,
        port: int,
        days_back: int,
    ) -> list[RawJob]:
        """Synchronous IMAP fetch — runs in a thread executor."""
        results: list[RawJob] = []

        try:
                     
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(user, password)
            mail.select("INBOX", readonly=True)

                                      
            since_date = (datetime.now(tz=timezone.utc) - timedelta(days=days_back)).strftime("%d-%b-%Y")
            status, msg_ids = mail.search(None, f'(SINCE "{since_date}")')
            if status != "OK" or not msg_ids[0]:
                logger.info("[Gmail] No emails found in date range")
                mail.logout()
                return []

            ids = msg_ids[0].split()
            logger.info(f"[Gmail] Found {len(ids)} emails in last {days_back} days")

                                          
                                                                                
                                                                              
            candidates = []
            for msg_id in reversed(ids[:200]):
                try:
                                                                     
                    status, data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
                    if status != "OK" or not data[0]:
                        continue
                    header_bytes = data[0][1]
                    header_msg = email_lib.message_from_bytes(header_bytes)
                    subj = _decode_header_value(header_msg.get("Subject", ""))
                    from_hdr = _decode_header_value(header_msg.get("From", ""))
                    _, sender_addr = parseaddr(from_hdr)

                                                                                     
                    is_trusted = _is_trusted_sender(sender_addr)
                    has_kw = any(kw in subj.lower() for kw in SUBJECT_KEYWORDS)
                    has_sender_hint = any(h in sender_addr.lower() for h in SENDER_HINTS)

                    if is_trusted or has_kw or has_sender_hint:
                        candidates.append(msg_id)
                except Exception:
                    continue

            logger.info(f"[Gmail] {len(candidates)} candidates after header pre-filter")

                                                                        
            for msg_id in candidates[:50]:
                try:
                    extracted_jobs = self._process_email(mail, msg_id, user)
                    if extracted_jobs:
                        results.extend(extracted_jobs)
                except Exception as e:
                    logger.debug(f"[Gmail] Error processing email {msg_id}: {e}")
                    continue

            mail.logout()

        except imaplib.IMAP4.error as e:
            logger.error(f"[Gmail] IMAP error: {e}")
        except Exception as e:
            logger.error(f"[Gmail] Connection error: {e}")

        return results

    def _process_email(self, mail: imaplib.IMAP4_SSL, msg_id: bytes, user_email: str) -> list[RawJob]:
        """Process a single email: filter → parse → extract → build RawJob."""
        status, data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data[0]:
            return []

        raw_email = data[0][1]
        msg = email_lib.message_from_bytes(raw_email)

                        
        subject = _decode_header_value(msg.get("Subject", ""))
        from_header = _decode_header_value(msg.get("From", ""))
        _, sender_email = parseaddr(from_header)
        message_id = msg.get("Message-ID", "")

                    
        received_at = None
        date_header = msg.get("Date")
        if date_header:
            try:
                received_at = parsedate_to_datetime(date_header)
            except Exception:
                pass

                  
        plain_text, html_text = _get_body(msg)

                                 
        links = _extract_links_from_html(html_text) if html_text else []

                                                
        if plain_text:
            url_pattern = re.compile(r'https?://[^\s<>"\']+')
            for url_match in url_pattern.finditer(plain_text):
                url = url_match.group(0).rstrip(".,;:!?)")
                if not any(l["url"] == url for l in links):
                    links.append({"url": url, "text": ""})

                                         
        body_text = plain_text or _html_to_text(html_text) if html_text else ""
        has_external_links = any(
            l["url"].startswith(("http://", "https://"))
            and not _is_junk_link(l["url"])
            for l in links
        )

                              
        if not _is_internship_mail(subject, sender_email, body_text, has_external_links):
            return []

                              
        clean_subj = _clean_subject(subject)
        company = _extract_company_from_sender(from_header)
        location = _extract_location(body_text)
        deadline = _extract_deadline(body_text)
        mode = _infer_mode(body_text)

                                                                              
        title = clean_subj or "Untitled Internship"
        
                         
        description = (body_text[:1500] if body_text else "").strip()

                                                             
                                                                          
                                                                             
        JOB_LINK_URL_PATTERNS = {
            "indeed.com/rc/clk",                                  
            "indeed.com/pagead/clk",                                        
            "indeed.com/viewjob",
            "naukri.com/job-listings",
            "naukri.com/job-detail",
            "naukri.com/dl?",                                                   
            "instahyre.com/job/",
            "internshala.com/internship/detail",
            "linkedin.com/jobs/view",
            "glassdoor.com/job-listing",
            "cutshort.io/j/",
            "wellfound.com/jobs/",
            "foundit.in/job/",
            "apna.co/job/",
            "link.internshala.com/v1/emailclick",                       
            "cutshort.io/api/tracking",                              
            "mailesp.glassdoor.com",                                  
            "e.linkedin.com",                                        
            "naukri.com/job-listings",
            "naukri.com/job-detail",
            "naukri.com/dl?",
        }

                                                                   
        NAV_LINK_TEXTS = {
            "apply", "apply now", "view job", "view jobs", "view all",
            "view all jobs", "click here", "read more", "view details",
            "website", "company website", "see all", "see more",
            "unsubscribe", "manage alerts", "manage job alerts",
            "unsubscribe from this job alert", "edit this job alert",
            "privacy policy", "terms", "terms of service",
            "indeed terms of service", "help centre", "help center",
            "since yesterday", "for last 7 days", "for last 14 days",
            "learn more", "sign in", "log in", "download app",
            "get the app", "contact us", "click now", "click now!",
            "view all articles", "report a problem", "security advice",
            "know more", "explore now", "download now",
        }

                                                                                  
        NAV_URL_PATTERNS = {
            "subscriptions.indeed.com",
            "support.indeed.com",
            "indeed.com/legal",
            "indeed.onelink.me",
            "/hp?co=",
            "/messages?",
            "/notifications?",
            "indeed.com/jobs?q=",                                         
            "cm.naukri.com",                                                 
        }

        is_digest = _is_trusted_sender(sender_email) or "alert" in subject.lower() or "digest" in subject.lower()

        jobs = []
        seen_urls = set()
        for link in links:
            url = link.get("url", "")
            text = (link.get("text") or "").strip()

            if not url or not url.startswith(("http://", "https://")):
                continue
            if _is_junk_link(url):
                continue
            if url in seen_urls:
                continue

            url_lower = url.lower()
            low_text = text.lower().strip()

                                             
            if any(pat in url_lower for pat in NAV_URL_PATTERNS):
                continue

                                                              
            is_job_url = any(pat in url_lower for pat in JOB_LINK_URL_PATTERNS)

            if is_job_url:
                                                                                   
                if len(text) >= 5 and low_text not in NAV_LINK_TEXTS:
                    job_title = text[:120]
                else:
                    job_title = title                             

                seen_urls.add(url)
                jobs.append(RawJob(
                    title=job_title,
                    company=company,
                    location=location,
                    internship_type="Internship",
                    description=description,
                    apply_link=url,
                    source="Gmail",
                    posted_date=received_at,
                    extra={
                        "mode": mode,
                        "source_type": "email",
                        "sender_email": sender_email,
                        "subject": subject,
                        "message_id": message_id,
                        "deadline": deadline.isoformat() if deadline else None,
                        "is_digest": True,
                    },
                ))
            elif is_digest and len(text) >= 10 and low_text not in NAV_LINK_TEXTS:
                                                                            
                                                                                        
                seen_urls.add(url)
                jobs.append(RawJob(
                    title=text[:120],
                    company=company,
                    location=location,
                    internship_type="Internship",
                    description=description,
                    apply_link=url,
                    source="Gmail",
                    posted_date=received_at,
                    extra={
                        "mode": mode,
                        "source_type": "email",
                        "sender_email": sender_email,
                        "subject": subject,
                        "message_id": message_id,
                        "deadline": deadline.isoformat() if deadline else None,
                        "is_digest": True,
                    },
                ))

                                                                            
        if jobs:
            return jobs

                                                              
        apply_link = _extract_apply_link(links)
        return [RawJob(
            title=title,
            company=company,
            location=location,
            internship_type="Internship",
            description=description,
            apply_link=apply_link,
            source="Gmail",
            posted_date=received_at,
            extra={
                "mode": mode,
                "source_type": "email",
                "sender_email": sender_email,
                "subject": subject,
                "message_id": message_id,
                "deadline": deadline.isoformat() if deadline else None,
            },
        )]
