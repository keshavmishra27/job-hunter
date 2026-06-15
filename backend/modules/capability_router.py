"""
Capability Router — decides *how* to read a source and implements fallback chains.

Flow:
    Source record (from DB)
    → resolve adapter via adapter_registry
    → try primary fetch_mode
    → if blocked / failed → try fallback_modes in order
    → update source.last_fetch_status

Fetch Strategies:
    html      → httpx + BeautifulSoup  (current default)
    browser   → Playwright headless     (stubbed — for JS-heavy pages)
    api       → direct JSON API calls
    imap      → email inbox scanning    (Gmail fetcher)
    telegram  → Telegram channel parser
    manual    → no-op, allows manual URL import only
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.source import Source
from backend.modules.adapter_registry import get_adapter
from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob


# ─── Fetch Modes ─────────────────────────────────────────────────────────────

class FetchMode(str, Enum):
    HTML = "html"
    BROWSER = "browser"
    API = "api"
    IMAP = "imap"
    TELEGRAM = "telegram"
    MANUAL = "manual"


class FetchBlockedError(Exception):
    """Raised when a fetch strategy is blocked (HTTP 403/429, CAPTCHA, etc.)."""
    pass


class FetchUnavailableError(Exception):
    """Raised when a fetch strategy is not implemented / not available."""
    pass


# ─── Fetch Result ────────────────────────────────────────────────────────────

@dataclass
class FetchResult:
    """Result of fetching from a single source."""
    source_name: str
    items: list[RawJob] = field(default_factory=list)
    status: str = "success"          # success | partial | failed | blocked | skipped
    mode_used: str = "html"          # which fetch_mode actually worked
    modes_tried: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0


# ─── Capability Router ──────────────────────────────────────────────────────

class CapabilityRouter:
    """
    Resolves a Source record to its adapter and fetch strategy,
    then executes with fallback chain support.
    """

    async def fetch_source(
        self,
        source: Source,
        keywords: list[str],
        location: str = "",
        *,
        applied_fingerprints: set[str] | None = None,
        applied_urls: set[str] | None = None,
        force_refresh: bool = False,
    ) -> FetchResult:
        """
        Fetch from a single source using its primary mode, falling back
        through fallback_modes if the primary fails or is blocked.
        """
        parser_type = source.parser_type
        if not parser_type:
            return FetchResult(
                source_name=source.name,
                status="skipped",
                error="No parser_type configured",
            )

        adapter_cls = get_adapter(parser_type)
        if adapter_cls is None:
            return FetchResult(
                source_name=source.name,
                status="skipped",
                error=f"No adapter registered for parser_type: {parser_type}",
            )

        # Build the ordered list of modes to try
        primary = source.fetch_mode or "html"
        fallbacks = source.fallback_modes or []
        modes_to_try = [primary] + [m for m in fallbacks if m != primary]

        result = FetchResult(source_name=source.name)
        start = datetime.utcnow()

        for mode in modes_to_try:
            result.modes_tried.append(mode)
            try:
                items = await self._fetch_with_mode(
                    adapter_cls=adapter_cls,
                    mode=mode,
                    keywords=keywords,
                    location=location,
                    applied_fingerprints=applied_fingerprints,
                    applied_urls=applied_urls,
                    force_refresh=force_refresh,
                )
                if items:
                    result.items = items
                    result.status = "success"
                    result.mode_used = mode
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                    result.duration_ms = int(elapsed)
                    logger.info(
                        f"[CapRouter] {source.name}: {len(items)} items via {mode} "
                        f"({result.duration_ms}ms)"
                    )
                    return result
                else:
                    # Empty result — try next mode
                    logger.debug(
                        f"[CapRouter] {source.name}: {mode} returned 0 items, trying next"
                    )
                    continue

            except FetchBlockedError as e:
                logger.warning(
                    f"[CapRouter] {source.name}: {mode} blocked — {e}. Trying next fallback."
                )
                continue

            except FetchUnavailableError as e:
                logger.debug(
                    f"[CapRouter] {source.name}: {mode} unavailable — {e}. Trying next fallback."
                )
                continue

            except Exception as e:
                logger.warning(
                    f"[CapRouter] {source.name}: {mode} error — {e}. Trying next fallback."
                )
                continue

        # All modes exhausted
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        result.duration_ms = int(elapsed)
        result.status = "failed"
        result.error = f"All modes failed: {modes_to_try}"
        logger.error(f"[CapRouter] {source.name}: all modes exhausted → failed")
        return result

    async def _fetch_with_mode(
        self,
        adapter_cls: type,
        mode: str,
        keywords: list[str],
        location: str,
        **kwargs: Any,
    ) -> list[RawJob]:
        """
        Execute a fetch using a specific mode.

        Currently all adapters use their own internal HTTP client (httpx),
        so mode selection is primarily for future extensibility:
          - 'html':     standard adapter.fetch() — httpx + BS4
          - 'browser':  stubbed — would inject Playwright page
          - 'api':      standard adapter.fetch() — adapter uses JSON endpoints
          - 'imap':     standard adapter.fetch() — Gmail fetcher reads inbox
          - 'telegram': standard adapter.fetch() — Telegram channel parser
          - 'manual':   no-op — source only accepts manual URL import
        """
        if mode == "manual":
            # Manual sources never auto-fetch
            raise FetchUnavailableError("Manual sources require manual import")

        if mode == "browser":
            # Browser automation is stubbed for now.
            # When Playwright is available, inject a browser page here.
            raise FetchUnavailableError(
                "Browser automation not yet implemented — falling back"
            )

        # For html, api, imap, telegram: use the adapter's native fetch()
        fetcher: BaseFetcher = adapter_cls()
        return await fetcher.fetch(keywords, location=location, **kwargs)

    async def fetch_sources(
        self,
        sources: list[Source],
        keywords: list[str],
        location: str = "",
        *,
        applied_fingerprints: set[str] | None = None,
        applied_urls: set[str] | None = None,
        force_refresh: bool = False,
        max_concurrency: int = 5,
    ) -> list[FetchResult]:
        """
        Fetch from multiple sources concurrently with bounded parallelism.
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_fetch(source: Source) -> FetchResult:
            async with semaphore:
                return await self.fetch_source(
                    source=source,
                    keywords=keywords,
                    location=location,
                    applied_fingerprints=applied_fingerprints,
                    applied_urls=applied_urls,
                    force_refresh=force_refresh,
                )

        tasks = [_bounded_fetch(s) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetch_results: list[FetchResult] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                fetch_results.append(FetchResult(
                    source_name=sources[i].name,
                    status="failed",
                    error=str(res),
                ))
            else:
                fetch_results.append(res)

        return fetch_results


# ─── Module-level singleton ─────────────────────────────────────────────────

_router_instance: CapabilityRouter | None = None


def get_capability_router() -> CapabilityRouter:
    """Get or create the singleton CapabilityRouter."""
    global _router_instance
    if _router_instance is None:
        _router_instance = CapabilityRouter()
    return _router_instance
