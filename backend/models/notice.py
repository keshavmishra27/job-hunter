import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    eligibility_text: Mapped[str | None] = mapped_column(Text)
    eligibility_status: Mapped[str] = mapped_column(String, default="unknown")
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    location: Mapped[str | None] = mapped_column(String)
    stipend: Mapped[str | None] = mapped_column(String)
    portal_link: Mapped[str | None] = mapped_column(String)
    source_link: Mapped[str | None] = mapped_column(String)
    raw_text: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="new")
    content_hash: Mapped[str | None] = mapped_column(String, unique=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    links: Mapped[list["NoticeLink"]] = relationship("NoticeLink", back_populates="notice")


class NoticeLink(Base):
    __tablename__ = "notice_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    notice_id: Mapped[str] = mapped_column(String, ForeignKey("notices.id"))
    url: Mapped[str] = mapped_column(String)
    kind: Mapped[str | None] = mapped_column(String)
    is_clean: Mapped[bool] = mapped_column(Boolean, default=True)

    notice: Mapped["Notice"] = relationship("Notice", back_populates="links")
