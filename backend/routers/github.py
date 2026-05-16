import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from loguru import logger

from backend.database import get_db
from backend.config import get_settings
from backend.models.github import GithubAccount, RepoEntry, RepoAnalysis, RepoScore
from backend.modules.github_client import GithubClient
from backend.modules.repo_analyzer import analyze_repo
from backend.modules.repo_scorer import compute_repo_score, rank_and_select_top5, generate_selection_reason
from backend.modules.role_profiles import list_roles
from backend.modules.repo_improvements import generate_repo_intelligence

router = APIRouter(prefix="/github", tags=["github"])
settings = get_settings()


class ConnectPayload(BaseModel):
    token: str
    user_id: str = "demo-user-1"


class RolePayload(BaseModel):
    role: str


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("/roles")
async def get_roles():
    return {"roles": list_roles()}


@router.post("/connect")
async def connect_github(payload: ConnectPayload, db: AsyncSession = Depends(get_db)):
    client = GithubClient(payload.token)
    try:
        user_info = await client.get_user()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid GitHub token: {e}")

    existing = await db.execute(
        select(GithubAccount).where(GithubAccount.user_id == payload.user_id)
    )
    account = existing.scalar_one_or_none()

    if account:
        account.github_username = user_info["login"]
        account.token_hash = payload.token
        account.connected_at = datetime.utcnow()
    else:
        account = GithubAccount(
            user_id=payload.user_id,
            github_username=user_info["login"],
            token_hash=payload.token,
        )
        db.add(account)

    await db.commit()
    return {"status": "connected", "github_user": user_info}


@router.get("/status")
async def get_status(user_id: str = "demo-user-1", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GithubAccount).where(GithubAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return {"connected": False}
    return {
        "connected": True,
        "github_username": account.github_username,
        "last_synced": account.last_synced,
    }


@router.post("/sync")
async def sync_repos(
    background_tasks: BackgroundTasks,
    user_id: str = "demo-user-1",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GithubAccount).where(GithubAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="GitHub account not connected")

    client = GithubClient(account.token_hash)
    raw_repos = await client.list_repos()

    synced = 0
    for raw in raw_repos:
        if raw.get("fork"):
            continue

        existing = await db.execute(
            select(RepoEntry).where(RepoEntry.github_id == raw["id"])
        )
        repo = existing.scalar_one_or_none()

        if not repo:
            repo = RepoEntry(
                user_id=user_id,
                github_id=raw["id"],
                name=raw["name"],
                full_name=raw["full_name"],
                url=raw.get("url", ""),
                html_url=raw.get("html_url", ""),
                description=raw.get("description"),
                language=raw.get("language"),
                stars=raw.get("stargazers_count", 0),
                forks=raw.get("forks_count", 0),
                open_issues=raw.get("open_issues_count", 0),
                watchers=raw.get("watchers_count", 0),
                size_kb=raw.get("size", 0),
                is_fork=raw.get("fork", False),
                is_archived=raw.get("archived", False),
                visibility=raw.get("visibility", "public"),
                default_branch=raw.get("default_branch", "main"),
                topics=raw.get("topics", []),
                last_push=_parse_dt(raw.get("pushed_at")),
                created_at=_parse_dt(raw.get("created_at")),
            )
            db.add(repo)
        else:
            repo.stars = raw.get("stargazers_count", 0)
            repo.forks = raw.get("forks_count", 0)
            repo.description = raw.get("description")
            repo.language = raw.get("language")
            repo.topics = raw.get("topics", [])
            repo.last_push = _parse_dt(raw.get("pushed_at"))
            repo.fetched_at = datetime.utcnow()

        synced += 1

    account.last_synced = datetime.utcnow()
    await db.commit()

    return {"status": "synced", "repos_synced": synced}


@router.post("/analyze")
async def analyze_all_repos(
    user_id: str = "demo-user-1",
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(GithubAccount).where(GithubAccount.user_id == user_id)
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="GitHub account not connected")

    repos_result = await db.execute(
        select(RepoEntry).where(
            RepoEntry.user_id == user_id,
            RepoEntry.is_archived == False,
        )
    )
    repos = repos_result.scalars().all()
    if not repos:
        return {"analyzed": 0}

    client = GithubClient(account.token_hash)
    owner = account.github_username
    analyzed = 0

    for repo in repos:
        try:
            readme_task = client.get_readme(owner, repo.name)
            tree_task = client.get_repo_tree(owner, repo.name, repo.default_branch)
            readme, tree = await asyncio.gather(readme_task, tree_task, return_exceptions=True)

            if isinstance(readme, Exception):
                readme = None
            if isinstance(tree, Exception):
                tree = []

            signals = analyze_repo(readme, tree, {
                "name": repo.name,
                "description": repo.description or "",
                "topics": repo.topics or [],
                "homepage": None,
            })

            existing_analysis = await db.execute(
                select(RepoAnalysis).where(RepoAnalysis.repo_id == repo.id)
            )
            analysis = existing_analysis.scalar_one_or_none()

            if not analysis:
                analysis = RepoAnalysis(repo_id=repo.id)
                db.add(analysis)

            analysis.readme_content = readme[:8000] if readme else None
            analysis.readme_length = signals.get("readme_length", 0)
            analysis.has_readme = signals.get("has_readme", False)
            analysis.has_problem_statement = signals.get("has_problem_statement", False)
            analysis.has_features_section = signals.get("has_features_section", False)
            analysis.has_setup_instructions = signals.get("has_setup_instructions", False)
            analysis.has_architecture_info = signals.get("has_architecture_info", False)
            analysis.has_screenshots = signals.get("has_screenshots", False)
            analysis.has_api_docs = signals.get("has_api_docs", False)
            analysis.has_future_scope = signals.get("has_future_scope", False)
            analysis.file_count = signals.get("file_count", 0)
            analysis.directory_count = signals.get("directory_count", 0)
            analysis.folder_structure = signals.get("top_level_dirs", [])
            analysis.has_tests = signals.get("has_tests", False)
            analysis.has_ci_cd = signals.get("has_ci_cd", False)
            analysis.has_docker = signals.get("has_docker", False)
            analysis.has_env_example = signals.get("has_env_example", False)
            analysis.has_requirements = signals.get("has_requirements", False)
            analysis.has_package_json = signals.get("has_package_json", False)
            analysis.has_gitignore = signals.get("has_gitignore", False)
            analysis.has_ui = signals.get("has_ui", False)
            analysis.has_deployment = signals.get("has_deployment", False)
            analysis.has_demo_link = signals.get("has_demo_link", False)
            analysis.has_license = signals.get("has_license", False)
            analysis.has_contributing = signals.get("has_contributing", False)
            analysis.analysis_signals = signals
            analysis.analyzed_at = datetime.utcnow()

            analyzed += 1

        except Exception as e:
            logger.warning(f"[Analyzer] Failed for {repo.name}: {e}")
            continue

    await db.commit()
    return {"analyzed": analyzed}


@router.get("/top5")
async def get_top5(
    role: str = Query("fullstack"),
    user_id: str = "demo-user-1",
    db: AsyncSession = Depends(get_db),
):
    repos_result = await db.execute(
        select(RepoEntry).where(
            RepoEntry.user_id == user_id,
            RepoEntry.is_archived == False,
        )
    )
    repos = repos_result.scalars().all()
    if not repos:
        return {"role": role, "top5": [], "all_repos": []}

    repo_ids = [r.id for r in repos]
    analyses_result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.repo_id.in_(repo_ids))
    )
    analyses = {a.repo_id: a for a in analyses_result.scalars().all()}

    all_analyses_list = [a.analysis_signals or {} for a in analyses.values()]

    scored = []
    for repo in repos:
        analysis = analyses.get(repo.id)
        if not analysis:
            signals = {}
        else:
            signals = analysis.analysis_signals or {
                "has_readme": analysis.has_readme,
                "readme_length": analysis.readme_length,
                "has_problem_statement": analysis.has_problem_statement,
                "has_features_section": analysis.has_features_section,
                "has_setup_instructions": analysis.has_setup_instructions,
                "has_architecture_info": analysis.has_architecture_info,
                "has_screenshots": analysis.has_screenshots,
                "has_tests": analysis.has_tests,
                "has_ci_cd": analysis.has_ci_cd,
                "has_docker": analysis.has_docker,
                "has_ui": analysis.has_ui,
                "has_deployment": analysis.has_deployment,
                "has_demo_link": analysis.has_demo_link,
                "file_count": analysis.file_count,
                "directory_count": analysis.directory_count,
                "topics": repo.topics or [],
                "description": repo.description or "",
            }

        score_result = compute_repo_score(signals, role, all_analyses_list)

        last_push = None
        if repo.last_push:
            last_push = repo.last_push.isoformat()

        scored.append({
            "repo_id": repo.id,
            "github_id": repo.github_id,
            "name": repo.name,
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "description": repo.description,
            "language": repo.language,
            "stars": repo.stars,
            "forks": repo.forks,
            "topics": repo.topics or [],
            "last_push": last_push,
            "has_readme": getattr(analysis, "has_readme", False) if analysis else False,
            "has_ui": getattr(analysis, "has_ui", False) if analysis else False,
            "has_tests": getattr(analysis, "has_tests", False) if analysis else False,
            "has_deployment": getattr(analysis, "has_deployment", False) if analysis else False,
            "has_demo_link": getattr(analysis, "has_demo_link", False) if analysis else False,
            "readme_length": getattr(analysis, "readme_length", 0) if analysis else 0,
            "file_count": getattr(analysis, "file_count", 0) if analysis else 0,
            "directory_count": getattr(analysis, "directory_count", 0) if analysis else 0,
            "folder_structure": getattr(analysis, "folder_structure", []) if analysis else [],
            **score_result,
            "analyzed": analysis is not None,
        })

    ranked = rank_and_select_top5(scored, role)
    top5 = [r for r in ranked if r["is_top5"]]

    await _upsert_scores(top5, role, db)

    return {
        "role": role,
        "top5": top5,
        "all_repos": ranked,
        "total": len(ranked),
    }


async def _upsert_scores(top5: list[dict], role: str, db: AsyncSession):
    for item in top5:
        await db.execute(
            delete(RepoScore).where(
                RepoScore.repo_id == item["repo_id"],
                RepoScore.role == role,
            )
        )
        score = RepoScore(
            repo_id=item["repo_id"],
            role=role,
            uniqueness_score=item["uniqueness_score"],
            code_quality_score=item["code_quality_score"],
            documentation_score=item["documentation_score"],
            uiux_score=item["uiux_score"],
            final_score=item["final_score"],
            breakdown=item["breakdown"],
            selection_reason=item.get("selection_reason"),
            is_top5=True,
        )
        db.add(score)
    await db.commit()


@router.get("/repos/{repo_id}/details")
async def get_repo_details(
    repo_id: str,
    role: str = Query("fullstack"),
    db: AsyncSession = Depends(get_db),
):
    repo_result = await db.execute(select(RepoEntry).where(RepoEntry.id == repo_id))
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    analysis_result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.repo_id == repo_id)
    )
    analysis = analysis_result.scalar_one_or_none()

    signals = {}
    if analysis:
        signals = analysis.analysis_signals or {}

    score_result = compute_repo_score(signals, role)
    intelligence = generate_repo_intelligence(signals, role)

    analysis_dict = {
        "has_readme": getattr(analysis, "has_readme", False),
        "readme_length": getattr(analysis, "readme_length", 0),
        "has_problem_statement": getattr(analysis, "has_problem_statement", False),
        "has_features_section": getattr(analysis, "has_features_section", False),
        "has_setup_instructions": getattr(analysis, "has_setup_instructions", False),
        "has_architecture_info": getattr(analysis, "has_architecture_info", False),
        "has_screenshots": getattr(analysis, "has_screenshots", False),
        "has_api_docs": getattr(analysis, "has_api_docs", False),
        "has_future_scope": getattr(analysis, "has_future_scope", False),
        "has_tests": getattr(analysis, "has_tests", False),
        "has_ci_cd": getattr(analysis, "has_ci_cd", False),
        "has_docker": getattr(analysis, "has_docker", False),
        "has_ui": getattr(analysis, "has_ui", False),
        "has_deployment": getattr(analysis, "has_deployment", False),
        "has_demo_link": getattr(analysis, "has_demo_link", False),
        "has_license": getattr(analysis, "has_license", False),
        "has_contributing": getattr(analysis, "has_contributing", False),
        "file_count": getattr(analysis, "file_count", 0),
        "directory_count": getattr(analysis, "directory_count", 0),
        "folder_structure": getattr(analysis, "folder_structure", []),
    } if analysis else None

    return {
        "repo_id": repo_id,
        "name": repo.name,
        "full_name": repo.full_name,
        "html_url": repo.html_url,
        "description": repo.description,
        "language": repo.language,
        "languages_all": repo.languages_all,
        "stars": repo.stars,
        "forks": repo.forks,
        "topics": repo.topics,
        "last_push": repo.last_push.isoformat() if repo.last_push else None,
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "analysis": analysis_dict,
        "scores": score_result,
        "role": role,
        "signal_reasons": intelligence["signal_reasons"],
        "improvement_tips": intelligence["improvement_tips"],
    }


@router.post("/webhook")
async def github_webhook(payload: dict):
    event = payload.get("action")
    repo_name = payload.get("repository", {}).get("name", "unknown")
    logger.info(f"[Webhook] Event={event} repo={repo_name}")
    return {"received": True}
