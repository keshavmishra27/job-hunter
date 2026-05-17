import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True)
    source_type: Mapped[str] = mapped_column(String)  # structured / semi-structured / unstructured
    base_url: Mapped[str | None] = mapped_column(String)
    fetch_frequency_minutes: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    parser_type: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())
