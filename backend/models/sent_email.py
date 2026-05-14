import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class SentEmail(Base):
    __tablename__ = "sent_emails"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id: Mapped[str] = mapped_column(String, ForeignKey("drafts.id"))
    recipient: Mapped[str] = mapped_column(String)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

    draft: Mapped["Draft"] = relationship("Draft", back_populates="sent_emails")
    follow_ups: Mapped[list["FollowUp"]] = relationship("FollowUp", back_populates="sent_email")
