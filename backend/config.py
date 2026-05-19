from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite+aiosqlite:///./data/job_hunter.db"
    website_url: str = "http://localhost:5173"
    secret_key: str = "changeme"

    openai_api_key: str = ""
    groq_api_key: str = ""
    openrouter_key: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    storage_dir: str = "./storage"
    faiss_index_path: str = "./data/faiss_index"

    govt_portal_urls: list[str] = []
    company_career_hosts: list[str] = []

    scheduler_interval_hours: int = 6
    max_emails_per_day: int = 20

    linkedin_email: str = ""
    linkedin_password: str = ""

    telegram_bot_token: str = ""
    github_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()