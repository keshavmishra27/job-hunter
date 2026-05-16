import math
from datetime import datetime, timezone
from loguru import logger


OFFLINE_ALLOWED = {"delhi ncr", "gurgaon", "noida", "gurugram", "delhi"}

WEIGHTS = {
    "project_overlap": 0.35,
    "skill_match": 0.30,
    "role_match": 0.15,
    "location_fit": 0.10,
    "recency": 0.10,
}

# GitHub repo matching keywords
REPO_TECH_MAPPING = {
    "frontend": ["react", "vue", "angular", "svelte", "next", "nuxt", "html", "css", "js", "typescript"],
    "backend": ["fastapi", "django", "flask", "node", "express", "spring", "java", "python", "go", "rust"],
    "fullstack": ["react", "vue", "next", "nuxt", "fastapi", "django", "flask", "node", "express"],
    "ai": ["tensorflow", "pytorch", "keras", "sklearn", "huggingface", "openai", "langchain", "rag", "llm", "ml"],
    "data": ["pandas", "numpy", "sklearn", "tensorflow", "pytorch", "sql", "spark", "hadoop"],
    "devops": ["docker", "kubernetes", "aws", "gcp", "azure", "ci", "cd", "terraform", "ansible"],
}


def _location_fit(job: dict, profile: dict) -> float:
    mode = (job.get("mode") or "offline").lower()
    if mode == "remote":
        return 1.0
    location = (job.get("location") or "").lower()
    allowed = [loc.lower() for loc in profile.get("location_rule", {}).get("offline_allowed", [])]
    if any(a in location or location in a for a in allowed):
        return 1.0
    return 0.0


def _hard_filter(job: dict, profile: dict) -> bool:
    mode = (job.get("mode") or "offline").lower()
    if mode == "remote":
        return True
    location = (job.get("location") or "").lower()
    allowed = [loc.lower() for loc in profile.get("location_rule", {}).get("offline_allowed", [])]
    if any(a in location or location in a for a in allowed):
        return True
    logger.debug(f"[Ranker] Hard-filtered out: {job['title']} @ {job['company']} ({location})")
    return False


def _build_search_text(job: dict) -> str:
    parts = [
        job.get("title") or "",
        job.get("description") or "",
        job.get("company") or "",
    ]
    return " ".join(parts).lower()


def _skill_match(job: dict, profile: dict) -> tuple[float, list[str]]:
    profile_skills = [s.lower() for s in (profile.get("skills") or [])]
    if not profile_skills:
        return 0.5, []
    text = _build_search_text(job)
    matched = [s for s in profile_skills if s in text]
    score = min(len(matched) / max(len(profile_skills), 1), 1.0)
    return score, matched


def _role_match(job: dict, profile: dict) -> float:
    title = (job.get("title") or "").lower()
    preferred = [r.lower() for r in (profile.get("preferred_roles") or [])]
    if not preferred:
        return 0.5
    for role in preferred:
        words = role.split()
        if any(w in title for w in words):
            return 1.0
    return 0.2


def _project_overlap(job: dict, profile: dict, github_repos: list[dict] | None = None) -> tuple[float, list[str]]:
    """
    Score project overlap using both resume projects AND GitHub repos.
    GitHub repos are weighted higher (they're more detailed).
    """
    projects = profile.get("projects") or []
    text = _build_search_text(job)
    job_title = (job.get("title") or "").lower()
    job_desc = (job.get("description") or "").lower()
    
    resume_score = 0.0
    github_score = 0.0
    matched_projects = []
    
    # Score resume projects (simple keyword matching)
    if projects:
        for project in projects:
            words = [w.lower() for w in project.split() if len(w) > 3]
            if not words:
                continue
            hits = [w for w in words if w in text]
            ratio = len(hits) / len(words)
            if ratio > 0:
                matched_projects.append(project)
                if ratio > resume_score:
                    resume_score = ratio
    
    # Score GitHub repos (tech stack matching) => weight higher than resume
    best_github_repo = None
    if github_repos:
        for repo in github_repos:
            repo_score = _score_github_repo_overlap(repo, job_title, job_desc, text)
            if repo_score > github_score:
                github_score = repo_score
                best_github_repo = repo
        
        # Add best matching GitHub repo to matched list if score is good
        if best_github_repo and github_score > 0.15:
            repo_name = best_github_repo.get("name", "GitHub project")
            if repo_name not in matched_projects:
                matched_projects.append(f"[GitHub] {repo_name}")
    
    #  summation GitHub scores weighted 70%, resume scores 30%
    if github_repos and github_score > 0:
        final_score = (github_score * 0.7) + (resume_score * 0.3)
    else:
        final_score = resume_score
    
    return min(final_score, 1.0), matched_projects


def _extract_job_tech_requirements(job_title: str, job_desc: str, full_text: str) -> set[str]:
    """Extract specific technology keywords from job requirements."""
    tech_keywords = {
        
        "react", "vue", "angular", "svelte", "next", "nuxt", "html", "css",
        
        "fastapi", "django", "flask", "node", "express", "spring", "java",
    
        "python", "javascript", "typescript", "go", "rust", "cpp", "java", "c#",
    
        "tensorflow", "pytorch", "keras", "sklearn", "pandas", "numpy",
        "huggingface", "openai", "langchain", "rag", "llm", "ml", "ai",
        # DevOps
        "docker", "kubernetes", "aws", "gcp", "azure", "ci", "cd",

        "sql", "postgres", "mongodb", "redis", "firebase",
        # Others
        "api", "rest", "graphql", "microservices", "kubernetes", "websocket",
    }
    found = set()
    text_lower = full_text.lower()
    for tech in tech_keywords:
        if tech in text_lower:
            found.add(tech)
    return found


def _score_github_repo_overlap(repo: dict, job_title: str, job_desc: str, full_text: str) -> float:
    """
    Score how well a GitHub repo matches a job.
    More sophisticated: extracts job requirements and scores repo relevance.
    """
    job_techs = _extract_job_tech_requirements(job_title, job_desc, full_text)
    
   
    if not job_techs:
        return 0.1  
    
    # Extract repo tech stack
    repo_desc = (repo.get("description") or "").lower()
    repo_topics = [t.lower() for t in (repo.get("topics") or [])]
    repo_language = (repo.get("language") or "").lower()
    repo_text = f"{repo_desc} {' '.join(repo_topics)} {repo_language}".lower()
    
    # Find how many jobs required techs are in the repo
    repo_tech_matches = sum(1 for tech in job_techs if tech in repo_text)
    
    # what fraction of required techs does this repo have?
    if not repo_tech_matches:
        base_score = 0.0  # No matching tech = no overlap
    else:
        # if repo has some of the job's tech stack
        base_score = min(repo_tech_matches / len(job_techs), 1.0)
    
    # Quality multiplier
    analysis_signals = repo.get("analysis_signals") or {}
    quality_mult = 1.0
    
    if analysis_signals.get("has_readme"):
        quality_mult += 0.1
    if analysis_signals.get("has_problem_statement"):
        quality_mult += 0.1
    if analysis_signals.get("has_architecture_info"):
        quality_mult += 0.15
    if analysis_signals.get("has_deployment"):
        quality_mult += 0.1
    if analysis_signals.get("has_tests"):
        quality_mult += 0.1
    if analysis_signals.get("has_ui"):
        quality_mult += 0.05
    
    # Apply multiplier but cap at 1.0
    final_score = base_score * min(quality_mult, 2.0)
    return min(final_score, 1.0)


def _recency(job: dict) -> float:
    posted = job.get("posted_date")
    if not posted:
        return 0.5
    if isinstance(posted, str):
        try:
            posted = datetime.fromisoformat(posted)
        except ValueError:
            return 0.5
    now = datetime.now(tz=timezone.utc)
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    days_old = (now - posted).days
    return max(0.0, 1.0 - days_old / 30)


def score_job(job: dict, profile: dict, github_repos: list[dict] | None = None) -> dict:
    proj_score, matched_projects = _project_overlap(job, profile, github_repos)
    skill_score, matched_skills = _skill_match(job, profile)
    breakdown = {
        "project_overlap": proj_score,
        "skill_match": skill_score,
        "role_match": _role_match(job, profile),
        "location_fit": _location_fit(job, profile),
        "recency": _recency(job),
    }
    total = sum(WEIGHTS[k] * v for k, v in breakdown.items())
    return {
        "score": round(total, 4),
        "breakdown": breakdown,
        "matched_skills": matched_skills,
        "matched_projects": matched_projects,
    }


def rank_jobs(jobs: list[dict], profile: dict, github_repos: list[dict] | None = None) -> list[dict]:
    passed: list[dict] = []

    for job in jobs:
        if not _hard_filter(job, profile):
            continue
        result = score_job(job, profile, github_repos)
        job["score"] = result["score"]
        job["score_breakdown"] = result["breakdown"]
        job["matched_skills"] = result["matched_skills"]
        job["matched_projects"] = result["matched_projects"]
        passed.append(job)

    passed.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"[Ranker] {len(jobs)} jobs → {len(passed)} after hard filters, ranked.")
    return passed
