"""
Unified opportunity models — the universal backbone for all lanes.

Opportunity: shared table for internships, notices, and freelance gigs.
FreelanceDetails: freelance-specific fields (budget, client, etc.).
ApplicationTracker: unified status tracking across all lanes.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class Opportunity(Base):
    """Unified opportunity backbone — powers all three lanes."""
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Classification ──────────────────────────────────────────────────
    opportunity_type: Mapped[str] = mapped_column(String)
    # internship | notice | freelance

    source: Mapped[str] = mapped_column(String)
    # source display name (e.g. "Internshala", "Upwork")

    source_group: Mapped[str | None] = mapped_column(String, nullable=True)
    # internship | startup | remote | notice | freelance
    # mirrors Source.source_group for fast filtering

    # ── Core Fields ─────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String)
    organization: Mapped[str] = mapped_column(String)  # company or client name
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    mode: Mapped[str | None] = mapped_column(String, nullable=True)
    # remote | hybrid | offline

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_link: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Deduplication ───────────────────────────────────────────────────
    fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Scoring ─────────────────────────────────────────────────────────
    score: Mapped[float | None] = mapped_column(Float, nullable=True) # Fit score
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    matched_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    matched_projects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    
    # ── Competition Estimator ───────────────────────────────────────────
    competition_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_label: Mapped[str | None] = mapped_column(String, nullable=True)
    competition_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Tracking ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String, default="new")
    # new | saved | drafted | applied | rejected | expired

    # ── Timestamps ──────────────────────────────────────────────────────
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Notice-specific (nullable for non-notice types) ─────────────────
    eligibility_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_status: Mapped[str | None] = mapped_column(String, nullable=True)
    # eligible | maybe | not_eligible

    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stipend: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Relationships ───────────────────────────────────────────────────
    freelance_details: Mapped["FreelanceDetails"] = relationship(
        "FreelanceDetails", back_populates="opportunity", uselist=False
    )
    tracking: Mapped[list["ApplicationTracker"]] = relationship(
        "ApplicationTracker", back_populates="opportunity"
    )


class FreelanceDetails(Base):
    """Freelance-specific fields, linked 1:1 to an Opportunity."""
    __tablename__ = "freelance_details"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id: Mapped[str] = mapped_column(String, ForeignKey("opportunities.id"), unique=True)

    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_type: Mapped[str | None] = mapped_column(String, nullable=True)  # fixed / hourly
    currency: Mapped[str | None] = mapped_column(String, default="USD")
    deliverables: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_type: Mapped[str | None] = mapped_column(String, nullable=True)  # individual / company / startup
    client_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    client_reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    project_length: Mapped[str | None] = mapped_column(String, nullable=True)  # short / medium / long
    payment_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=True)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="freelance_details")


class ApplicationTracker(Base):
    """Unified tracking for opportunities across all lanes."""
    __tablename__ = "application_tracker"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id: Mapped[str] = mapped_column(String, ForeignKey("opportunities.id"))
    user_id: Mapped[str] = mapped_column(String)
    lane_type: Mapped[str] = mapped_column(String)  # internship | notice | freelance
    status: Mapped[str] = mapped_column(String, default="saved")
    # saved | queued | applied | interview | rejected | ghosted | offer
    
    # Autopilot fields
    resume_used_id: Mapped[str | None] = mapped_column(String, nullable=True)
    answers_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    portal_type: Mapped[str | None] = mapped_column(String, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    in_progress_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="tracking")
