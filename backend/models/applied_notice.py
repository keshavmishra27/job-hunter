import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class AppliedNotice(Base):
    __tablename__ = "applied_notices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    notice_id: Mapped[str] = mapped_column(String, ForeignKey("notices.id"))
    user_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="saved")  # saved/viewed/opened/applied/dismissed
    notes: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    notice = relationship("Notice")
