import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sent_email_id: Mapped[str] = mapped_column(String, ForeignKey("sent_emails.id"))
    due_date: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="pending")
    note: Mapped[str | None] = mapped_column(Text)

    sent_email: Mapped["SentEmail"] = relationship("SentEmail", back_populates="follow_ups")
