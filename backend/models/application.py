import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("job_posts.id"))
    draft_id: Mapped[str | None] = mapped_column(String, ForeignKey("drafts.id"), nullable=True)

    status: Mapped[str] = mapped_column(String, default="applied")
    company_name: Mapped[str | None] = mapped_column(String)
    role_title: Mapped[str | None] = mapped_column(String)
    application_link: Mapped[str | None] = mapped_column(String)
    source: Mapped[str | None] = mapped_column(String)

    job_fingerprint: Mapped[str | None] = mapped_column(String, index=True)
    source_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)

    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)

                              
    thread_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    resume_used: Mapped[str | None] = mapped_column(String, nullable=True)
    response_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["JobPost"] = relationship("JobPost")
    draft: Mapped["Draft"] = relationship("Draft")
