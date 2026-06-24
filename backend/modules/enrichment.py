"""
Enrichment Layer — fetch full details for accepted opportunities asynchronously.

Once a posting passes eligibility and ranking, enrichment fetches:
  - Full description (from apply_link page)
  - Stipend / duration extraction
  - Application method (direct / portal / Google Form)
  - Active / expired status
  - Company profile snippets

This layer is designed to run asynchronously so the pipeline stays fast.
"""
from __future__ import annotations

from datetime import datetime
from loguru import logger
import httpx

from backend.modules.notice_extractor import (
    extract_from_html,
    extract_from_pdf_bytes,
    parse_text_fields,
)
from backend.modules.portal_link_extractor import clean_and_resolve_links


async def enrich_opportunity(opp: dict, timeout: int = 10) -> dict:
    """
    Enrich a single opportunity dict with additional details fetched
    from its apply_link.

    Returns the enriched dict (mutated in-place for convenience).
    """
    apply_link = opp.get("apply_link")
    if not apply_link or not apply_link.startswith(("http://", "https://")):
        return opp

                                                                                
    source = (opp.get("source") or "")
    if source.startswith("Telegram/") or source == "Gmail":
        return opp

    parsed: dict = {}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(apply_link)
            if resp.status_code != 200:
                logger.debug(f"[Enrichment] {apply_link} returned {resp.status_code}")
                return opp

            content_type = resp.headers.get("content-type", "").lower()
            if apply_link.lower().endswith(".pdf") or content_type.startswith("application/pdf"):
                parsed = extract_from_pdf_bytes(resp.content)
            else:
                parsed = extract_from_html(resp.text, base_url=apply_link)

                                     
            try:
                raw_links = parsed.get("links") or []
                parsed["links"] = await clean_and_resolve_links(
                    raw_links, base_url=apply_link, follow=True
                )
            except Exception:
                pass

    except Exception as e:
        logger.debug(f"[Enrichment] Failed to fetch {apply_link}: {e}")
                                                        
        parsed = parse_text_fields(opp.get("description") or "")

    if not parsed:
        parsed = parse_text_fields(opp.get("description") or "")

                         
    if parsed.get("raw_text") and not opp.get("description"):
        opp["description"] = parsed["raw_text"]

    if parsed.get("location") and not opp.get("location"):
        opp["location"] = parsed["location"]

    if parsed.get("eligibility_text") and not opp.get("eligibility_text"):
        opp["eligibility_text"] = parsed["eligibility_text"]

    if parsed.get("deadline") and not opp.get("deadline"):
        opp["deadline"] = parsed["deadline"]

    if parsed.get("stipend") and not opp.get("stipend"):
        opp["stipend"] = parsed["stipend"]

                                       
    links = parsed.get("links") or []
    for link in links:
        if link.get("kind") in ("portal", "google_form"):
            opp["portal_link"] = link.get("url")
            break

    opp["enriched_at"] = datetime.utcnow()

    return opp


async def enrich_batch(
    opportunities: list[dict],
    max_concurrency: int = 3,
    timeout: int = 10,
) -> list[dict]:
    """
    Enrich a batch of opportunities with bounded concurrency.
    Returns the same list with enriched data applied in-place.
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded_enrich(opp: dict) -> dict:
        async with semaphore:
            return await enrich_opportunity(opp, timeout=timeout)

    tasks = [_bounded_enrich(opp) for opp in opportunities]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"[Enrichment] Error enriching {opportunities[i].get('title')}: {result}")
            enriched.append(opportunities[i])
        else:
            enriched.append(result)

    logger.info(f"[Enrichment] Enriched {len(enriched)} opportunities")
    return enriched
