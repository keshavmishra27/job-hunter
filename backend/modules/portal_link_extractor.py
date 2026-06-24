import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, urljoin
import httpx
from loguru import logger

TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|mc_eid|mc_cid|ref|oref|_hsenc|_hsmi)", re.I)


def _strip_tracking_params(url: str) -> str:
    try:
        parsed = urlparse(url)
        qs = parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in qs if not TRACKING_PARAMS.match(k)]
        new_query = urlencode(filtered)
        cleaned = urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip('/'), parsed.params, new_query, ''))
        return cleaned
    except Exception:
        return url


def _canonicalize(url: str) -> str:
                                                           
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return urlunparse((parsed.scheme.lower() or 'https', parsed.netloc.lower(), path, '', parsed.query or '', ''))
    except Exception:
        return url


async def resolve_final_url(url: str, timeout: int = 10) -> tuple[str, str]:
    """Follow redirects and return (final_url, content_type)."""
                                                                
    if not url or not url.startswith(("http://", "https://")):
        return url, ''
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                                                               
            try:
                r = await client.head(url)
                r.raise_for_status()
            except Exception:
                r = await client.get(url)
            final = str(r.url)
            ctype = r.headers.get('content-type', '')
            return final, ctype
    except Exception as e:
        logger.debug(f"[PortalLink] resolve failed for {url}: {e}")
        return url, ''


async def clean_and_resolve_links(links: list[dict], base_url: str | None = None, follow: bool = True) -> list[dict]:
                                                  
    SKIP_SCHEMES = ("javascript:", "tg://", "mailto:", "data:", "tel:", "sms:", "void(", "#")
    out = []
    seen = set()
    for l in links:
        raw = l.get('url') or l.get('href') or l.get('text')
        if not raw:
            continue
                                                          
        if any(raw.startswith(s) for s in SKIP_SCHEMES):
            continue
        if base_url and not raw.startswith(('http://', 'https://')):
            raw = urljoin(base_url, raw)
                                               
        if not raw.startswith(('http://', 'https://')):
            continue

        cleaned = _strip_tracking_params(raw)
        cleaned = _canonicalize(cleaned)

        final_url = cleaned
        content_type = ''
        if follow:
            final_url, content_type = await resolve_final_url(cleaned)
            final_url = _strip_tracking_params(final_url)
            final_url = _canonicalize(final_url)

        if final_url in seen:
            continue
        seen.add(final_url)

        kind = l.get('kind')
        low = final_url.lower()
        if 'forms.gle' in low or 'docs.google.com/forms' in low:
            kind = 'google_form'
        elif low.endswith('.pdf') or 'application/pdf' in (content_type or ''):
            kind = 'pdf'
        elif any(k in low for k in ['apply', 'career', 'jobs', 'recruit']):
            kind = kind or 'portal'

        out.append({'url': final_url, 'text': l.get('text') or final_url, 'kind': kind, 'content_type': content_type})

    return out
