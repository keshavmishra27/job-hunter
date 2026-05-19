import math
import re
from datetime import datetime, timezone
from loguru import logger
from backend.modules.internship_matcher import detect_year_fit


OFFLINE_ALLOWED = {"delhi ncr", "gurgaon", "noida", "gurugram", "delhi"}

# Substrings that indicate a job is remote / WFH even when mode field is missing
REMOTE_HINTS = {"remote", "wfh", "work from home", "work-from-home", "anywhere in india", "pan india"}

WEIGHTS = {
    "project_overlap": 0.35,
    "skill_match": 0.30,
    "role_match": 0.15,
    "location_fit": 0.10,
    "recency": 0.10,
}

# GitHub repo matching keywords (for category-level fallback)
REPO_TECH_MAPPING = {
    "frontend": ["react", "vue", "angular", "svelte", "next", "nuxt", "html", "css", "js", "typescript"],
    "backend": ["fastapi", "django", "flask", "node", "express", "spring", "java", "python", "go", "rust"],
    "fullstack": ["react", "vue", "next", "nuxt", "fastapi", "django", "flask", "node", "express"],
    "ai": ["tensorflow", "pytorch", "keras", "sklearn", "huggingface", "openai", "langchain", "rag", "llm", "ml", "python"],
    "data": ["pandas", "numpy", "sklearn", "tensorflow", "pytorch", "sql", "spark", "hadoop"],
    "devops": ["docker", "kubernetes", "aws", "gcp", "azure", "ci", "cd", "terraform", "ansible"],
}

# Title words that map to a REPO_TECH_MAPPING category (for fallback when job desc is sparse)
REPO_CATEGORY_HINTS = {
    "ai": "ai",
    "ml": "ai",
    "machine learning": "ai",
    "deep learning": "ai",
    "data science": "data",
    "data analyst": "data",
    "nlp": "ai",
    "computer vision": "ai",
    "generative": "ai",
    "llm": "ai",
    "backend": "backend",
    "frontend": "frontend",
    "fullstack": "fullstack",
    "full stack": "fullstack",
    "devops": "devops",
    "cloud": "devops",
}

# Master set of recognized tech keywords (shared by job AND project extraction)
TECH_KEYWORDS_SET = {
    # Frontend
    "react", "vue", "angular", "svelte", "nextjs", "nuxtjs", "html", "css",
    # Backend
    "fastapi", "django", "flask", "express", "spring boot", "node",
    # Languages
    "python", "javascript", "typescript", "golang", "rust", "java", "kotlin", "cpp",
    # AI/ML frameworks
    "tensorflow", "pytorch", "keras", "sklearn", "scikit-learn",
    "pandas", "numpy", "huggingface", "openai", "langchain",
    "computer vision", "deep learning", "machine learning",
    "natural language processing", "nlp",
    # LLM / GenAI
    "llm", "rag", "transformers", "bert", "gpt", "llama",
    "stable diffusion", "diffusion", "embedding", "vector database",
    "chromadb", "pinecone", "weaviate", "faiss",
    "crewai", "autogen", "agentops", "agentic",
    # DevOps
    "docker", "kubernetes", "terraform", "ansible",
    # Cloud
    "aws", "gcp", "azure",
    # Databases
    "sql", "postgres", "postgresql", "mongodb", "redis", "firebase",
    # Tools
    "graphql", "websocket", "microservices", "git", "github",
    # Automation
    "selenium", "playwright", "puppeteer", "automation",
    "rpa", "robotic process automation",
}

# Generic techs that appear in almost every job — downweight in matching
GENERIC_TECHS = {
    "python", "javascript", "typescript", "java", "html", "css",
    "git", "github", "sql", "node", "c",
}


def _extract_tech_from_text(text: str) -> set[str]:
    """Extract recognized tech keywords from any text string."""
    found = set()
    text_lower = text.lower()
    for tech in TECH_KEYWORDS_SET:
        if " " in tech:
            if tech in text_lower:
                found.add(tech)
        else:
            if re.search(rf'\b{re.escape(tech)}\b', text_lower):
                found.add(tech)
    return found


def _get_job_category(job_title: str) -> str | None:
    """Map a job title to a broad tech category using REPO_CATEGORY_HINTS."""
    title_lower = job_title.lower()
    for hint, category in REPO_CATEGORY_HINTS.items():
        if hint in title_lower:
            return category
    return None


def _is_remote(job: dict) -> bool:
    """Check if a job is remote/WFH using mode field and location hints."""
    mode = (job.get("mode") or "").lower()
    if mode == "remote":
        return True
    location = (job.get("location") or "").lower()
    description = (job.get("description") or "").lower()
    combined = f"{location} {description}"
    return any(hint in combined for hint in REMOTE_HINTS)


def _location_fit(job: dict, profile: dict) -> float:
    if _is_remote(job):
        return 1.0
    location = (job.get("location") or "").lower()
    allowed = [loc.lower() for loc in profile.get("location_rule", {}).get("offline_allowed", [])]
    if any(a in location or location in a for a in allowed):
        return 1.0
    return 0.0


def _is_expired(job: dict, max_days: int = 30) -> bool:
    """Return True if the job is older than max_days (treat it as expired)."""
    posted = job.get("posted_date")
    if not posted:
        return False  # No date info → keep it, don't drop blindly
    try:
        if isinstance(posted, str):
            posted = datetime.fromisoformat(posted)
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(tz=timezone.utc) - posted).days
        return days_old > max_days
    except Exception:
        return False


def _experience_filter(job: dict) -> bool:
    """Return True (keep) if the job does not require prior experience."""
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    result = detect_year_fit(text)
    if result == "not_eligible":
        logger.debug(
            f"[Ranker] Dropped (experience required): {job.get('title')} @ {job.get('company')}"
        )
        return False
    return True


def _detect_duration_months(text: str) -> int | None:
    """Extract internship duration in months from text.
    
    Returns the maximum month count found, or None if no duration is mentioned.
    Handles patterns like:
      - "Duration: 6 Months"
      - "3-6 months"
      - "3 to 6 months"  
      - "contract length: 6 months"
      - "Internship Duration: 6 Months"
      - "6 month internship"
    """
    if not text:
        return None
    t = text.lower()
    
    max_months = None
    
    # Pattern: "X-Y months" or "X to Y months" (take the max)
    range_pattern = re.findall(r'(\d+)\s*(?:to|-)\s*(\d+)\s*months?', t)
    for low, high in range_pattern:
        val = int(high)
        if max_months is None or val > max_months:
            max_months = val
    
    # Pattern: standalone "X months" or "X month"
    single_pattern = re.findall(r'(\d+)\s*months?', t)
    for m in single_pattern:
        val = int(m)
        # Ignore unreasonable values (> 24 months is probably not a duration)
        if val > 24:
            continue
        if max_months is None or val > max_months:
            max_months = val
    
    # Pattern: "X weeks" — convert to months (4 weeks ≈ 1 month)
    week_pattern = re.findall(r'(\d+)\s*weeks?', t)
    for w in week_pattern:
        val_months = int(w) / 4.0
        int_months = math.ceil(val_months)
        if max_months is None or int_months > max_months:
            max_months = int_months
    
    return max_months


# Maximum internship duration the user is willing to do (in months)
MAX_DURATION_MONTHS = 6


def _duration_filter(job: dict) -> bool:
    """Return True (keep) if the internship duration is <= MAX_DURATION_MONTHS.
    
    Jobs with no detectable duration are kept (benefit of the doubt).
    """
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    months = _detect_duration_months(text)
    if months is not None and months > MAX_DURATION_MONTHS:
        logger.debug(
            f"[Ranker] Dropped (duration {months}mo > {MAX_DURATION_MONTHS}mo): "
            f"{job.get('title')} @ {job.get('company')}"
        )
        return False
    return True


def _hard_filter(job: dict, profile: dict) -> bool:
    """Hard filters — always applied regardless of profile settings."""
    # 0. Drop jobs with missing/unknown titles
    title = (job.get("title") or "").strip().lower()
    if not title or title == "unknown":
        logger.debug(
            f"[Ranker] Dropped (unknown title): {job.get('company')}"
        )
        return False

    # 1. Drop expired postings
    if _is_expired(job):
        logger.debug(
            f"[Ranker] Dropped (expired): {job.get('title')} @ {job.get('company')}"
        )
        return False

    # 2. Drop jobs requiring experience that the user doesn't have
    if not _experience_filter(job):
        return False

    # 3. Drop internships longer than MAX_DURATION_MONTHS
    if not _duration_filter(job):
        return False

    # 4. Location filter — always enforced when offline_allowed cities are set.
    #    Remote jobs always pass. Offline jobs must match an allowed city.
    #    If offline_allowed is empty/unset, all locations pass (no restriction).
    location_rule = profile.get("location_rule") or {}
    allowed_cities = [loc.lower() for loc in (location_rule.get("offline_allowed") or [])]

    if allowed_cities:  # Only filter when the user has explicitly set cities
        if _is_remote(job):
            return True  # Remote jobs always pass
        location = (job.get("location") or "").lower()
        if any(a in location or location in a for a in allowed_cities):
            return True
        logger.debug(
            f"[Ranker] Dropped (location mismatch): {job.get('title')} @ "
            f"{job.get('company')} | location='{location}' not in {allowed_cities}"
        )
        return False

    return True  # No city restriction set — let everything through


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
    Score project overlap using resume projects AND GitHub repos.

    Strategy (in priority order):
      1. Tech-keyword intersection: extract recognized tech keywords from both
         the project string and the job text, then compute Jaccard-style overlap.
         This is robust — works even when project names are short like "LLM Chatbot".
      2. Raw word fallback: any project-title word (>3 chars) that appears
         literally in the job text also counts, as a secondary signal.
      3. GitHub repo matching: match repo language/topics against job tech
         requirements; fall back to category matching when job desc is sparse.
    """
    projects = profile.get("projects") or []
    text = _build_search_text(job)
    job_title = (job.get("title") or "").lower()
    job_desc = (job.get("description") or "").lower()

    # Extract tech keywords from the full job text
    job_techs = _extract_tech_from_text(text)

    resume_score = 0.0
    github_score = 0.0
    matched_projects = []

    # --- Resume project scoring ---
    if projects:
        for project in projects:
            proj_score = 0.0

            # Strategy 1: tech-keyword intersection
            proj_techs = _extract_tech_from_text(project)
            if proj_techs and job_techs:
                common = proj_techs & job_techs
                if common:
                    # Score = fraction of project's techs that the job requires
                    proj_score = len(common) / max(len(proj_techs), len(job_techs))
                    logger.debug(
                        f"[ProjectOverlap] '{project[:40]}' tech match: {common} score={proj_score:.2f}"
                    )

            # Strategy 2: raw word fallback (project words appear in job text)
            if proj_score == 0.0:
                words = [w.lower() for w in project.split() if len(w) > 3]
                if words:
                    hits = [w for w in words if w in text]
                    if hits:
                        proj_score = len(hits) / len(words)

            if proj_score > 0:
                matched_projects.append(project)
                if proj_score > resume_score:
                    resume_score = proj_score

    # --- GitHub repo scoring ---
    # Score ALL repos, then pick the most relevant one per job using
    # name-relevance tiebreaking (avoids showing the same repo every time).
    if github_repos:
        scored_repos = []
        for repo in github_repos:
            tech_score = _score_github_repo_overlap(repo, job_title, job_desc, text, job_techs)
            if tech_score <= 0:
                continue
            # Name + topic relevance: prefer repos whose name/topics match the job
            repo_name = (repo.get("name") or "").lower()
            repo_topics_list = [t.lower() for t in (repo.get("topics") or [])]
            repo_desc_text = (repo.get("description") or "").lower()
            name_words = [w for w in re.split(r'[-_\s]+', repo_name) if len(w) > 2]
            topic_words = [w for w in repo_topics_list if len(w) > 2]
            desc_words = [w for w in re.split(r'[-_\s]+', repo_desc_text) if len(w) > 3]
            all_repo_words = set(name_words + topic_words + desc_words)

            # Match against job title (high value) and full text (lower value)
            title_hits = sum(1 for w in all_repo_words if w in job_title)
            text_hits = sum(1 for w in all_repo_words if w in text)
            # Title match is worth more than body match
            name_bonus = min(title_hits * 0.15 + text_hits * 0.03, 0.40)
            combined = tech_score + name_bonus
            scored_repos.append((combined, tech_score, repo))

        if scored_repos:
            # Sort by combined score descending to pick the MOST relevant repo per job
            scored_repos.sort(key=lambda x: x[0], reverse=True)
            best_combined, best_tech, best_repo = scored_repos[0]
            github_score = best_tech
            repo_name = best_repo.get("name", "GitHub project")
            matched_projects.append(f"[GitHub] {repo_name}")

    # Combine: GitHub weighted 70%, resume 30% (when GitHub data exists)
    if github_repos and github_score > 0:
        final_score = (github_score * 0.7) + (resume_score * 0.3)
    else:
        final_score = resume_score

    return min(final_score, 1.0), matched_projects


def _extract_job_tech_requirements(job_title: str, job_desc: str, full_text: str) -> set[str]:
    """Thin wrapper — delegates to the shared extractor."""
    return _extract_tech_from_text(full_text)





def _score_github_repo_overlap(
    repo: dict,
    job_title: str,
    job_desc: str,
    full_text: str,
    job_techs: set[str] | None = None,
) -> float:
    """
    Score how well a GitHub repo matches a job.

    Uses specificity-weighted tech matching + semantic name/topic matching
    to ensure different repos are selected for different jobs.
    """
    if job_techs is None:
        job_techs = _extract_tech_from_text(full_text)

    # Build repo tech text: description + topics + primary language + ALL languages
    repo_desc = (repo.get("description") or "").lower()
    repo_topics = [t.lower() for t in (repo.get("topics") or [])]
    repo_language = (repo.get("language") or "").lower()
    languages_all = repo.get("languages_all") or {}
    all_lang_names = " ".join(k.lower() for k in languages_all.keys())
    repo_text = f"{repo_desc} {' '.join(repo_topics)} {repo_language} {all_lang_names}"

    repo_techs = _extract_tech_from_text(repo_text)

    # --- Strategy 1: specificity-weighted tech intersection ---
    direct_score = 0.0
    if job_techs and repo_techs:
        common = repo_techs & job_techs
        if common:
            # Specific techs (pytorch, langchain, etc.) worth 1.0 each
            # Generic techs (python, javascript, etc.) worth 0.2 each
            specific = common - GENERIC_TECHS
            generic = common & GENERIC_TECHS
            weighted_hits = len(specific) * 1.0 + len(generic) * 0.2

            job_specific = job_techs - GENERIC_TECHS
            job_generic = job_techs & GENERIC_TECHS
            weighted_total = max(len(job_specific) * 1.0 + len(job_generic) * 0.2, 1.0)

            direct_score = min(weighted_hits / weighted_total, 1.0)
            logger.debug(
                f"[RepoOverlap] repo='{repo.get('name')}' job='{job_title[:30]}' "
                f"specific={specific} generic={generic} score={direct_score:.3f}"
            )

    # --- Strategy 2: category-based matching (capped lower, fallback only) ---
    category_score = 0.0
    category = _get_job_category(job_title)
    if category and category in REPO_TECH_MAPPING:
        cat_techs = REPO_TECH_MAPPING[category]
        cat_matches = sum(1 for t in cat_techs if t in repo_text)
        if cat_matches >= 1:
            category_score = min(cat_matches / len(cat_techs), 0.35)  # cap at 0.35

    base_score = max(direct_score, category_score)
    if base_score == 0.0:
        return 0.0

    # --- Strategy 3: semantic name/topic match against job title ---
    # This ensures repos with relevant names score higher for matching jobs
    repo_name_lower = (repo.get("name") or "").lower()
    name_words = set(w for w in re.split(r'[-_\s]+', repo_name_lower) if len(w) > 2)
    topic_words = set(w for w in repo_topics if len(w) > 2)
    semantic_words = name_words | topic_words

    title_words = set(w for w in re.split(r'[-_\s]+', job_title) if len(w) > 2)
    semantic_hits = sum(1 for w in semantic_words if w in job_title or w in job_desc)
    title_overlap = len(semantic_words & title_words)
    semantic_bonus = min(title_overlap * 0.12 + semantic_hits * 0.04, 0.30)
    base_score = min(base_score + semantic_bonus, 1.0)

    # Quality multiplier: reward well-documented, tested repos
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

    return min(base_score * min(quality_mult, 2.0), 1.0)


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
    dropped = len(jobs) - len(passed)
    if dropped:
        logger.info(f"[Ranker] {len(jobs)} jobs → {len(passed)} ranked ({dropped} dropped by strict location filter).")
    else:
        logger.info(f"[Ranker] {len(jobs)} jobs ranked (no hard filter active).")
    return passed
