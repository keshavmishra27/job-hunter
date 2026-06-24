from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawJob:
    title: str
    company: str
    location: str | None
    internship_type: str | None
    description: str | None
    apply_link: str | None
    source: str
    posted_date: datetime | None = None
    canonical_url: str | None = None
    fingerprint: str | None = None
    opportunity_type: str = "internship"                              
    extra: dict = field(default_factory=dict)


class BaseFetcher(ABC):
    source_name: str = "unknown"

    @abstractmethod
    async def fetch(
        self,
        keywords: list[str],
        location: str = "",
        *,
        strategy: str | None = None,
        **kwargs,
    ) -> list[RawJob]:
        """
        Fetch raw job postings from the source.

        Args:
            keywords: search terms
            location: location filter
            strategy: optional fetch strategy hint from the CapabilityRouter
                      ("html", "browser", "api", etc.).  Adapters may ignore
                      this and use their own HTTP client, or use it to
                      switch between fetch approaches.
            **kwargs: additional options (applied_fingerprints, force_refresh, etc.)
        """
        ...

    def _safe_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
