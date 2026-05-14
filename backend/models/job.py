import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class JobPost(Base):
    __tablename__ = "job_posts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String)
    mode: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    apply_link: Mapped[str | None] = mapped_column(String)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="new")
    content_hash: Mapped[str | None] = mapped_column(String, unique=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    matches: Mapped[list["JobMatch"]] = relationship("JobMatch", back_populates="job")
    drafts: Mapped[list["Draft"]] = relationship("Draft", back_populates="job")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("job_posts.id"))
    score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON)
    matched_projects: Mapped[list | None] = mapped_column(JSON)
    matched_skills: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["JobPost"] = relationship("JobPost", back_populates="matches")
