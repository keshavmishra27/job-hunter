import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON
from backend.database import Base


class GithubAccount(Base):
    __tablename__ = "github_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    github_username: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime)


class RepoEntry(Base):
    __tablename__ = "repo_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    github_id: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    html_url: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String)
    languages_all: Mapped[dict | None] = mapped_column(JSON)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    watchers: Mapped[int] = mapped_column(Integer, default=0)
    size_kb: Mapped[int] = mapped_column(Integer, default=0)
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    visibility: Mapped[str] = mapped_column(String, default="public")
    default_branch: Mapped[str] = mapped_column(String, default="main")
    topics: Mapped[list | None] = mapped_column(JSON)
    last_push: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RepoAnalysis(Base):
    __tablename__ = "repo_analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id: Mapped[str] = mapped_column(String, ForeignKey("repo_entries.id"), unique=True)

    readme_content: Mapped[str | None] = mapped_column(Text)
    readme_length: Mapped[int] = mapped_column(Integer, default=0)
    has_readme: Mapped[bool] = mapped_column(Boolean, default=False)
    has_problem_statement: Mapped[bool] = mapped_column(Boolean, default=False)
    has_features_section: Mapped[bool] = mapped_column(Boolean, default=False)
    has_setup_instructions: Mapped[bool] = mapped_column(Boolean, default=False)
    has_architecture_info: Mapped[bool] = mapped_column(Boolean, default=False)
    has_screenshots: Mapped[bool] = mapped_column(Boolean, default=False)
    has_api_docs: Mapped[bool] = mapped_column(Boolean, default=False)
    has_future_scope: Mapped[bool] = mapped_column(Boolean, default=False)
    has_license: Mapped[bool] = mapped_column(Boolean, default=False)
    has_contributing: Mapped[bool] = mapped_column(Boolean, default=False)

    file_count: Mapped[int] = mapped_column(Integer, default=0)
    directory_count: Mapped[int] = mapped_column(Integer, default=0)
    folder_structure: Mapped[list | None] = mapped_column(JSON)
    has_tests: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ci_cd: Mapped[bool] = mapped_column(Boolean, default=False)
    has_docker: Mapped[bool] = mapped_column(Boolean, default=False)
    has_env_example: Mapped[bool] = mapped_column(Boolean, default=False)
    has_requirements: Mapped[bool] = mapped_column(Boolean, default=False)
    has_package_json: Mapped[bool] = mapped_column(Boolean, default=False)
    has_gitignore: Mapped[bool] = mapped_column(Boolean, default=False)

    has_ui: Mapped[bool] = mapped_column(Boolean, default=False)
    has_deployment: Mapped[bool] = mapped_column(Boolean, default=False)
    has_demo_link: Mapped[bool] = mapped_column(Boolean, default=False)

    analysis_signals: Mapped[dict | None] = mapped_column(JSON)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RepoScore(Base):
    __tablename__ = "repo_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id: Mapped[str] = mapped_column(String, ForeignKey("repo_entries.id"))
    role: Mapped[str] = mapped_column(String, nullable=False)

    uniqueness_score: Mapped[float] = mapped_column(Float, default=0.0)
    code_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    documentation_score: Mapped[float] = mapped_column(Float, default=0.0)
    uiux_score: Mapped[float] = mapped_column(Float, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)

    breakdown: Mapped[dict | None] = mapped_column(JSON)
    selection_reason: Mapped[str | None] = mapped_column(Text)
    is_top5: Mapped[bool] = mapped_column(Boolean, default=False)

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
