import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("job_posts.id"))
    subject: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    linkedin_message: Mapped[str | None] = mapped_column(Text)
    attachment_checklist: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped["JobPost"] = relationship("JobPost", back_populates="drafts")
    sent_emails: Mapped[list["SentEmail"]] = relationship("SentEmail", back_populates="draft")
