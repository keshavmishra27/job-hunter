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


# ── Keyword sets ──────────────────────────────────────────────────────────────

SUBJECT_KEYWORDS = {
    "internship", "intern", "career", "opportunity", "apply",
    "hiring", "trainee", "fresher", "stipend", "off campus",
    "opening", "recruitment", "placement",
}

BODY_KEYWORDS = {
    "apply now", "portal", "deadline", "selected", "shortlist",
    "last date", "register", "walk-in", "apply here", "application link",
    "google form", "apply before", "eligibility", "stipend",
}

SENDER_HINTS = {
    "careers", "hr", "recruit", "hiring", "talent", "noreply",
    "jobs", "placement", "internship", "campus",
}

# Links to always ignore
JUNK_LINK_PATTERNS = {
    "unsubscribe", "manage preferences", "opt-out", "optout",
    "mailto:", "tel:", "javascript:", "#", "privacy-policy",
    "privacy", "terms", "login", "signin", "sign-in",
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com/company", "youtube.com",
    "tracking", "click.email", "click.mailer",
    "list-manage.com", "mailchimp.com",
}

# Link URL hints that suggest an actual apply page
APPLY_LINK_HINTS = {
    "apply", "careers", "jobs", "forms.google", "internship",
    "recruit", "application", "register", "join", "form",
    "greenhouse.io", "lever.co", "workday.com", "icims.com",
    "smartrecruiters.com", "ashbyhq.com",
}


# ── HTML link extractor (stdlib) ──────────────────────────────────────────────

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


# ── Helper functions ──────────────────────────────────────────────────────────

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

        url_lower = url.lower()
        text_lower = (link.get("text") or "").lower()

        if any(h in url_lower or h in text_lower for h in APPLY_LINK_HINTS):
            preferred.append(url)
        else:
            external.append(url)

    return preferred[0] if preferred else (external[0] if external else None)


# ── Mail filter ───────────────────────────────────────────────────────────────

def _is_internship_mail(subject: str, sender: str, body_text: str, has_links: bool) -> bool:
    """
    Decide if an email is internship-related.
    Requires at least 2 signal matches from:
    - subject keywords
    - sender hints
    - body keywords
    - presence of external links
    """
    signals = 0
    subj_low = subject.lower()
    sender_low = sender.lower()
    body_low = body_text.lower()

    # Subject keyword match
    if any(kw in subj_low for kw in SUBJECT_KEYWORDS):
        signals += 1

    # Sender hint match (check local part and domain)
    if any(h in sender_low for h in SENDER_HINTS):
        signals += 1

    # Body keyword match
    if any(kw in body_low for kw in BODY_KEYWORDS):
        signals += 1

    # Has at least one external link
    if has_links:
        signals += 1

    return signals >= 2


# ── Mail parser ───────────────────────────────────────────────────────────────

def _clean_subject(subject: str) -> str:
    """Remove Re:, Fwd:, [tags] prefixes from subject line."""
    cleaned = re.sub(r"^(?:(?:Re|Fwd|FW|Fw)\s*:\s*)+", "", subject, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^\[.*?\]\s*", "", cleaned).strip()
    return cleaned


def _extract_company_from_sender(from_header: str) -> str:
    """Extract company name from the From header display name or domain."""
    display_name, email_addr = parseaddr(from_header)

    if display_name:
        # Clean common suffixes
        name = re.sub(r"\s*(Careers|Hiring|HR|Recruitment|Jobs|Team|Inc\.?|Ltd\.?|Pvt\.?)$", "", display_name, flags=re.IGNORECASE).strip()
        if name and len(name) > 1:
            return name

    # Fallback: extract from domain
    if email_addr:
        domain = email_addr.split("@")[-1] if "@" in email_addr else ""
        # Remove common TLDs and extract company name
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
    # Common patterns: "deadline: 15 June 2026", "last date: 20/06/2026", "apply before June 15"
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


# ── Main Fetcher ──────────────────────────────────────────────────────────────

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
            # Connect
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(user, password)
            mail.select("INBOX", readonly=True)

            # Search for recent emails
            since_date = (datetime.now(tz=timezone.utc) - timedelta(days=days_back)).strftime("%d-%b-%Y")
            status, msg_ids = mail.search(None, f'(SINCE "{since_date}")')
            if status != "OK" or not msg_ids[0]:
                logger.info("[Gmail] No emails found in date range")
                mail.logout()
                return []

            ids = msg_ids[0].split()
            logger.info(f"[Gmail] Found {len(ids)} emails in last {days_back} days")

            # Process each email (most recent first, cap at 100)
            for msg_id in reversed(ids[:100]):
                try:
                    raw_job = self._process_email(mail, msg_id, user)
                    if raw_job:
                        results.append(raw_job)
                except Exception as e:
                    logger.debug(f"[Gmail] Error processing email {msg_id}: {e}")
                    continue

            mail.logout()

        except imaplib.IMAP4.error as e:
            logger.error(f"[Gmail] IMAP error: {e}")
        except Exception as e:
            logger.error(f"[Gmail] Connection error: {e}")

        return results

    def _process_email(self, mail: imaplib.IMAP4_SSL, msg_id: bytes, user_email: str) -> RawJob | None:
        """Process a single email: filter → parse → extract → build RawJob."""
        status, data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data[0]:
            return None

        raw_email = data[0][1]
        msg = email_lib.message_from_bytes(raw_email)

        # Decode headers
        subject = _decode_header_value(msg.get("Subject", ""))
        from_header = _decode_header_value(msg.get("From", ""))
        _, sender_email = parseaddr(from_header)
        message_id = msg.get("Message-ID", "")

        # Parse date
        received_at = None
        date_header = msg.get("Date")
        if date_header:
            try:
                received_at = parsedate_to_datetime(date_header)
            except Exception:
                pass

        # Get body
        plain_text, html_text = _get_body(msg)

        # Extract links from HTML
        links = _extract_links_from_html(html_text) if html_text else []

        # Also extract bare URLs from plain text
        if plain_text:
            url_pattern = re.compile(r'https?://[^\s<>"\']+')
            for url_match in url_pattern.finditer(plain_text):
                url = url_match.group(0).rstrip(".,;:!?)")
                if not any(l["url"] == url for l in links):
                    links.append({"url": url, "text": ""})

        # Get readable text for filtering
        body_text = plain_text or _html_to_text(html_text) if html_text else ""
        has_external_links = any(
            l["url"].startswith(("http://", "https://"))
            and not _is_junk_link(l["url"])
            for l in links
        )

        # ── B. Mail Filter ──
        if not _is_internship_mail(subject, sender_email, body_text, has_external_links):
            return None

        # ── C. Mail Parser ──
        clean_subj = _clean_subject(subject)
        company = _extract_company_from_sender(from_header)
        location = _extract_location(body_text)
        deadline = _extract_deadline(body_text)
        mode = _infer_mode(body_text)

        # Use cleaned subject as title (role name is typically in the subject)
        title = clean_subj or "Untitled Internship"

        # ── D. Apply Link Extractor ──
        apply_link = _extract_apply_link(links)

        # Cap description
        description = (body_text[:1500] if body_text else "").strip()

        return RawJob(
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
        )
