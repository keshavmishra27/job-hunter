"""
Source model — every platform is a backend record, not a UI button.

Each source describes *what* it is, *how* to fetch from it, *how reliable*
it is, and *what to try if the primary mode fails*.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True)

    # ── Classification ──────────────────────────────────────────────────
    source_type: Mapped[str] = mapped_column(String)
    # internship_board | startup_board | remote_board | freelance_board | notice_channel

    source_group: Mapped[str] = mapped_column(String, default="internship")
    # internship | startup | remote | notice | freelance
    # UI groups sources by this field

    category: Mapped[str] = mapped_column(String, default="internship")
    # kept for backward compat with old queries (internship / notice / freelance)

    # ── Fetch Capability ────────────────────────────────────────────────
    fetch_mode: Mapped[str] = mapped_column(String, default="html")
    # html | browser | api | imap | telegram | manual

    auth_requirement: Mapped[str] = mapped_column(String, default="none")
    # none | api_key | oauth | session | manual

    reliability: Mapped[str] = mapped_column(String, default="medium")
    # high | medium | low | experimental

    fallback_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ordered fallback chain e.g. ["browser", "manual"]
    # tried in order after primary fetch_mode fails

    # ── Source Identity ─────────────────────────────────────────────────
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # maps to adapter class name in adapter_registry

    # ── Operational State ───────────────────────────────────────────────
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    fetch_frequency_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_fetch_status: Mapped[str | None] = mapped_column(String, nullable=True)
    # success | partial | failed | blocked

    last_fetch_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # how many items came back on last fetch

    # ── Metadata ────────────────────────────────────────────────────────
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())
