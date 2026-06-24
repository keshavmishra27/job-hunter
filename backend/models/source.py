"""
Source model — every platform is a backend record, not a UI button.

Each source describes *what* it is, *how* to fetch from it, *how reliable*
it is, and *what to try if the primary mode fails*.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True)

                                                                          
    source_type: Mapped[str] = mapped_column(String)
                                                                                        

    source_group: Mapped[str] = mapped_column(String, default="internship")
                                                        
                                     

    category: Mapped[str] = mapped_column(String, default="internship")
                                                                                 

                                                                          
    fetch_mode: Mapped[str] = mapped_column(String, default="html")
                                                     

    auth_requirement: Mapped[str] = mapped_column(String, default="none")
                                               

    reliability: Mapped[str] = mapped_column(String, default="medium")
                                        

    fallback_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)
                                                       
                                                   

                                                                          
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_type: Mapped[str | None] = mapped_column(String, nullable=True)
                                                    

                                                                          
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    fetch_frequency_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_fetch_status: Mapped[str | None] = mapped_column(String, nullable=True)
                                          

    last_fetch_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
                                            

                                                                          
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())
