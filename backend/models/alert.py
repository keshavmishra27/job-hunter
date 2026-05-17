import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    notice_id: Mapped[str | None] = mapped_column(String, ForeignKey("notices.id"))
    user_id: Mapped[str | None] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    notice = relationship("Notice")
