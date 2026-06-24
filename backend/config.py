from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "job_hunter.db"

class Settings(BaseSettings):
                                                                        
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"
    website_url: str = "http://localhost:5173"
    secret_key: str = "changeme"

    openrouter_key: str = ""

    storage_dir: str = (ROOT_DIR / "storage").as_posix()
    faiss_index_path: str = (ROOT_DIR / "data" / "faiss_index").as_posix()

    govt_portal_urls: list[str] = []
    company_career_hosts: list[str] = []

    scheduler_interval_hours: int = 6
    max_emails_per_day: int = 20

    linkedin_email: str = ""
    linkedin_password: str = ""

    telegram_bot_token: str = ""
    github_token: str = ""
    apify_token: str = ""

                                          
                                                                 
    imap_user: str = ""
    imap_password: str = ""
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    gmail_days_back: int = 7

                                                    
    @property
    def gmail_user(self) -> str:
        return self.imap_user

    @property
    def gmail_app_password(self) -> str:
        return self.imap_password

    @property
    def gmail_imap_host(self) -> str:
        return self.imap_host

    @property
    def gmail_imap_port(self) -> int:
        return self.imap_port


@lru_cache
def get_settings() -> Settings:
    return Settings()