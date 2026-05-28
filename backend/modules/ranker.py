import math
import re
from datetime import datetime, timezone
from loguru import logger
from backend.modules.internship_matcher import detect_year_fit


OFFLINE_ALLOWED = {"Delhi NCR", "Gurgaon", "Noida","Delhi","ghaziabad(hybrid)","ghaziabad","delhi(hybrid)","faridabad","agra, uttar pradesh","uttar pradesh","delhi, delhi","okhla, delhi","paschim vihar, delhi","saket, delhi","naraina, delhi, delhi","hauz khas, delhi, delhi","dilshad garden, delhi, delhi","tilak nagar, delhi, delhi","kirti nagar, delhi, delhi","connaught place, delhi, delhi","badarpur, delhi, delhi","india","India"}

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


# ─────────────────────────────────────────────────────────────────────────────
# Domain adjacency floor map
#
# If a candidate has any skill from a domain GROUP, jobs in the same group
# get a minimum skill_match floor.
#
# Floor tiers (mirror the scoring prompt):
#   0.90 → exact skill match (handled by literal matching already)
#   0.70 → same domain, closely related skill → floor = 0.70
#   0.60 → same broad domain (AI sibling) → floor = 0.60
#   0.50 → adjacent domain using same fundamentals → floor = 0.50
#   0.30 → transferable skill overlap → floor = 0.30
# ─────────────────────────────────────────────────────────────────────────────

# Map of skill-fragment → set of domain tags this skill belongs to.
_SKILL_TO_DOMAIN_TAGS: dict[str, set[str]] = {
    # GenAI / Agentic / LLM
    "genai":           {"ai", "ml", "nlp", "cv", "data_science"},
    "generative":      {"ai", "ml", "nlp", "cv", "data_science"},
    "agentic":         {"ai", "ml", "nlp", "data_science"},
    "llm":             {"ai", "ml", "nlp", "data_science"},
    "large language":  {"ai", "ml", "nlp", "data_science"},
    "langchain":       {"ai", "ml", "nlp"},
    "crewai":          {"ai", "ml"},
    "autogen":         {"ai", "ml"},
    "rag":             {"ai", "ml", "nlp"},
    "openai":          {"ai", "ml", "nlp"},
    "huggingface":     {"ai", "ml", "nlp", "cv"},
    "hugging face":    {"ai", "ml", "nlp", "cv"},
    "transformers":    {"ai", "ml", "nlp"},
    "stable diffusion":{"ai", "cv"},
    "diffusion":       {"ai", "cv"},
    # ML
    "machine learning":{"ml", "ai", "data_science"},
    "deep learning":   {"ml", "ai", "cv", "nlp"},
    "tensorflow":      {"ml", "ai", "cv"},
    "pytorch":         {"ml", "ai", "cv"},
    "keras":           {"ml", "ai"},
    "scikit":          {"ml", "data_science"},
    "sklearn":         {"ml", "data_science"},
    "xgboost":         {"ml", "data_science"},
    # NLP
    "nlp":             {"nlp", "ai", "ml"},
    "natural language": {"nlp", "ai", "ml"},
    "spacy":           {"nlp", "ml"},
    "nltk":            {"nlp", "ml"},
    "bert":            {"nlp", "ai", "ml"},
    # Computer Vision
    "computer vision": {"cv", "ai", "ml"},
    "opencv":          {"cv", "ml"},
    "yolo":            {"cv", "ml", "ai"},
    "cnn":             {"cv", "ml", "ai"},
    # Data Science
    "data science":    {"data_science", "ml"},
    "data analytics":  {"data_science"},
    "data analysis":   {"data_science"},
    "pandas":          {"data_science", "ml"},
    "numpy":           {"data_science", "ml"},
    "tableau":         {"data_science"},
    "power bi":        {"data_science"},
    # Web
    "react":           {"frontend", "web"},
    "fastapi":         {"backend", "web"},
    "django":          {"backend", "web"},
    "flask":           {"backend", "web"},
    "full stack":      {"frontend", "backend", "web"},
    "node":            {"backend", "web"},
    "frontend":        {"frontend", "web"},
    "backend":         {"backend", "web"},
    # DevOps
    "docker":          {"devops", "cloud"},
    "kubernetes":      {"devops", "cloud"},
    "aws":             {"devops", "cloud"},
    "gcp":             {"devops", "cloud"},
    "azure":           {"devops", "cloud"},
    "devops":          {"devops", "cloud"},
    # Automation
    "selenium":        {"automation", "qa"},
    "automation":      {"automation"},
    "rpa":             {"automation"},
}

# Job title/description fragment → domain tags that job belongs to.
_JOB_TO_DOMAIN_TAGS: dict[str, set[str]] = {
    # AI / GenAI
    "generative ai":   {"ai"},
    "llm":             {"ai", "nlp"},
    "large language":  {"ai", "nlp"},
    "agentic":         {"ai"},
    "genai":           {"ai"},
    # ML
    "machine learning":{"ml", "ai"},
    "deep learning":   {"ml", "ai"},
    "neural":          {"ml", "ai"},
    "tensorflow":      {"ml", "ai"},
    "pytorch":         {"ml", "ai"},
    # NLP
    "nlp":             {"nlp", "ai", "ml"},
    "natural language": {"nlp", "ai", "ml"},
    "text classification": {"nlp", "ml"},
    "sentiment":       {"nlp", "ml"},
    # CV
    "computer vision": {"cv", "ai", "ml"},
    "image processing":{"cv", "ml"},
    "object detection":{"cv", "ml", "ai"},
    "cnn":             {"cv", "ml", "ai"},
    # Data Science
    "data science":    {"data_science", "ml"},
    "data analytics":  {"data_science"},
    "data analyst":    {"data_science"},
    "data engineer":   {"data_science", "backend"},
    "business intelligence": {"data_science"},
    "power bi":        {"data_science"},
    "tableau":         {"data_science"},
    # Web
    "frontend":        {"frontend", "web"},
    "backend":         {"backend", "web"},
    "full stack":      {"frontend", "backend", "web"},
    "fullstack":       {"frontend", "backend", "web"},
    "react":           {"frontend", "web"},
    "django":          {"backend", "web"},
    "fastapi":         {"backend", "web"},
    "node":            {"backend", "web"},
    # DevOps
    "devops":          {"devops", "cloud"},
    "cloud":           {"cloud", "devops"},
    "aws":             {"cloud", "devops"},
    "kubernetes":      {"devops", "cloud"},
    "docker":          {"devops", "cloud"},
    # Automation
    "automation":      {"automation"},
    "rpa":             {"automation"},
    "qa":              {"qa", "automation"},
    "testing":         {"qa", "automation"},
}

# Domain-pair → adjacency floor (what skill_match score should be floored to)
# "same"    = exact same domain tag → 0.70 floor
# "sibling" = AI sub-domain siblings (nlp ↔ cv ↔ ml ↔ ai) → 0.60 floor
# "adjacent"= related but different top-level domain → 0.50 floor
_AI_DOMAIN_TAGS = {"ai", "ml", "nlp", "cv"}


def _get_domain_floor(profile_skills: list[str], job_text: str) -> float:
    """
    Compute the minimum skill_match score (floor) based on domain adjacency
    between the candidate's skills and the job description.

    Returns a floor value between 0.0 (no floor) and 0.70.
    """
    text_lower = job_text.lower()

    # --- Collect candidate domain tags from skills ---
    candidate_tags: set[str] = set()
    for skill in profile_skills:
        skill_lower = skill.lower()
        for fragment, tags in _SKILL_TO_DOMAIN_TAGS.items():
            if fragment in skill_lower:
                candidate_tags |= tags

    if not candidate_tags:
        return 0.0

    # --- Collect job domain tags from job text ---
    job_tags: set[str] = set()
    for fragment, tags in _JOB_TO_DOMAIN_TAGS.items():
        if fragment in text_lower:
            job_tags |= tags

    if not job_tags:
        return 0.0

    # --- Determine overlap and floor ---
    overlap = candidate_tags & job_tags

    if not overlap:
        return 0.0

    # Same exact domain tag match → strong floor
    if overlap:
        # Both candidate and job are AI sub-domains → AI sibling floor
        ai_candidate = bool(candidate_tags & _AI_DOMAIN_TAGS)
        ai_job = bool(job_tags & _AI_DOMAIN_TAGS)
        if ai_candidate and ai_job:
            # Direct same-tag hit (e.g., both "ml") → 0.70 floor
            same_tag = candidate_tags & job_tags & _AI_DOMAIN_TAGS
            if same_tag:
                return 0.70
            # Sibling AI tags (e.g., candidate has "ai", job has "cv") → 0.60 floor
            return 0.60

        # Non-AI same domain (web, devops, etc.) → 0.70 floor for exact match
        non_ai_same = (
            (candidate_tags & {"frontend", "backend", "web"}) &
            (job_tags & {"frontend", "backend", "web"})
        )
        if non_ai_same:
            return 0.70

        # Adjacent domain overlap (e.g., data_science ↔ ml) → 0.50 floor
        data_candidate = bool(candidate_tags & {"data_science"})
        ml_job = bool(job_tags & {"ml", "ai"})
        if data_candidate and ml_job:
            return 0.50

        ml_candidate = bool(candidate_tags & {"ml", "ai"})
        data_job = bool(job_tags & {"data_science"})
        if ml_candidate and data_job:
            return 0.50

        # General overlap in same non-AI domain
        if overlap:
            return 0.40

    return 0.0


def _extract_tech_from_text(text: str) -> set[str]:
    """Extract recognized tech keywords from any text string."""
    found = set()
    text_lower = text.lower()
    for tech in TECH_KEYWORDS_SET:
        if " " in tech:
            if tech in text_lower:
                found.add(tech)
        else:
            if re.search(rf'(?<!\w){re.escape(tech)}(?!\w)', text_lower):
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

    matched = []
    for s in profile_skills:
        if re.search(rf'(?<!\w){re.escape(s)}(?!\w)', text):
            matched.append(s)

    literal_score = min(len(matched) / max(len(profile_skills), 1), 1.0)

    # Apply domain adjacency floor — ensures same-domain jobs (e.g. CV for an AI
    # candidate) never score unfairly low just because the exact sub-skill isn't
    # literally mentioned in the job description.
    domain_floor = _get_domain_floor(profile_skills, text)
    score = max(literal_score, domain_floor)

    if domain_floor > literal_score:
        logger.debug(
            f"[SkillMatch] Domain floor {domain_floor:.2f} applied "
            f"(literal={literal_score:.2f}) for: {job.get('title')} @ {job.get('company')}"
        )

    return score, matched


def _role_match(job: dict, profile: dict) -> float:
    title = (job.get("title") or "").lower()
    preferred = [r.lower() for r in (profile.get("preferred_roles") or [])]
    if not preferred:
        return 0.5
        
    ignore_words = {"intern", "internship", "fresher", "developer", "engineer", "student"}
    
    best_score = 0.2
    for role in preferred:
        if re.search(rf'(?<!\w){re.escape(role)}(?!\w)', title):
            return 1.0
            
        words = [w for w in role.split() if w not in ignore_words]
        if not words:
            continue
            
        matches = [w for w in words if re.search(rf'(?<!\w){re.escape(w)}(?!\w)', title)]
        
        if len(matches) == len(words):
            return 1.0
        elif len(matches) > 0:
            best_score = max(best_score, 0.6)
            
    return best_score


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
    # Score ALL repos and pick the TOP 3 most relevant per job.
    if github_repos:
        scored_repos = []
        for repo in github_repos:
            tech_score = _score_github_repo_overlap(repo, job_title, job_desc, text, job_techs)
            if tech_score <= 0:
                continue
            # Name + topic relevance bonus
            repo_name = (repo.get("name") or "").lower()
            repo_topics_list = [t.lower() for t in (repo.get("topics") or [])]
            repo_desc_text = (repo.get("description") or "").lower()
            name_words = [w for w in re.split(r'[-_\s]+', repo_name) if len(w) > 2]
            topic_words = [w for w in repo_topics_list if len(w) > 2]
            desc_words = [w for w in re.split(r'[-_\s]+', repo_desc_text) if len(w) > 3]
            all_repo_words = set(name_words + topic_words + desc_words)

            title_hits = sum(1 for w in all_repo_words if w in job_title)
            text_hits = sum(1 for w in all_repo_words if w in text)
            name_bonus = min(title_hits * 0.15 + text_hits * 0.03, 0.40)
            combined = tech_score + name_bonus
            scored_repos.append((combined, tech_score, repo))

        if scored_repos:
            scored_repos.sort(key=lambda x: x[0], reverse=True)
            # Pick top 3 relevant repos (not just 1)
            top_repos = scored_repos[:3]
            best_tech = top_repos[0][1]
            github_score = best_tech
            for _, _, rp in top_repos:
                rp_name = rp.get("name", "GitHub project")
                matched_projects.append(f"[GitHub] {rp_name}")

    # Combine: GitHub weighted 70%, resume 30% (when GitHub data exists)
    if github_repos and github_score > 0:
        final_score = (github_score * 0.7) + (resume_score * 0.3)
    else:
        final_score = resume_score

    return min(final_score, 1.0), matched_projects


def _extract_job_tech_requirements(job_title: str, job_desc: str, full_text: str) -> set[str]:
    """Thin wrapper — delegates to the shared extractor."""
    return _extract_tech_from_text(full_text)





# Domain-specific keyword groups for deep README matching
# These distinguish sub-domains within AI/ML (e.g. CNN vs GenAI vs NLP)
_DOMAIN_KEYWORDS = {
    "genai": {
        "generative", "llm", "large language model", "gpt", "chatbot", "chat bot",
        "prompt", "prompt engineering", "rag", "retrieval augmented",
        "langchain", "llamaindex", "openai", "anthropic", "gemini",
        "stable diffusion", "diffusion model", "text generation",
        "fine-tuning", "fine tuning", "lora", "qlora",
        "embedding", "vector database", "vector store", "chromadb", "pinecone",
        "agent", "agentic", "crewai", "autogen", "multi-agent",
        "transformer", "huggingface", "tokenizer",
    },
    "computer_vision": {
        "cnn", "convolutional", "image classification", "image classifier",
        "object detection", "yolo", "resnet", "vgg", "inception",
        "image segmentation", "opencv", "computer vision",
        "face detection", "face recognition", "ocr",
        "image processing", "pixel", "convolution",
        "cat", "dog", "mnist", "cifar", "imagenet",
    },
    "nlp": {
        "nlp", "natural language", "text classification", "sentiment",
        "named entity", "ner", "pos tagging", "tokenization",
        "text mining", "word2vec", "glove", "spacy", "nltk",
        "text summarization", "machine translation",
    },
    "data_science": {
        "pandas", "numpy", "matplotlib", "seaborn", "plotly",
        "data analysis", "data visualization", "eda",
        "exploratory", "jupyter", "notebook", "kaggle",
        "regression", "classification", "clustering",
        "random forest", "xgboost", "lightgbm",
    },
    "web_dev": {
        "react", "vue", "angular", "nextjs", "express",
        "fastapi", "django", "flask", "rest api", "graphql",
        "frontend", "backend", "fullstack", "full stack",
        "crud", "authentication", "jwt", "oauth",
        "responsive", "spa", "single page",
    },
    "devops": {
        "docker", "kubernetes", "ci/cd", "pipeline",
        "terraform", "ansible", "aws", "gcp", "azure",
        "deployment", "infrastructure", "monitoring",
    },
}


def _detect_domain(text: str) -> dict[str, int]:
    """Count how many keywords from each domain appear in text."""
    text_lower = text.lower()
    scores = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[domain] = count
    return scores


def _score_github_repo_overlap(
    repo: dict,
    job_title: str,
    job_desc: str,
    full_text: str,
    job_techs: set[str] | None = None,
) -> float:
    """
    Score how well a GitHub repo matches a job.

    Uses 4 strategies:
      1. Specificity-weighted tech intersection
      2. Category-based fallback
      3. Semantic name/topic matching
      4. Deep README content domain matching (distinguishes CNN vs GenAI etc.)
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

    # Include README content for deep matching
    readme = (repo.get("readme_content") or "").lower()
    deep_text = f"{repo_text} {readme[:3000]}"  # Cap README to avoid noise

    repo_techs = _extract_tech_from_text(deep_text)

    # --- Strategy 1: specificity-weighted tech intersection ---
    direct_score = 0.0
    if job_techs and repo_techs:
        common = repo_techs & job_techs
        if common:
            specific = common - GENERIC_TECHS
            generic = common & GENERIC_TECHS
            weighted_hits = len(specific) * 1.0 + len(generic) * 0.2

            job_specific = job_techs - GENERIC_TECHS
            job_generic = job_techs & GENERIC_TECHS
            weighted_total = max(len(job_specific) * 1.0 + len(job_generic) * 0.2, 1.0)

            direct_score = min(weighted_hits / weighted_total, 1.0)

    # --- Strategy 2: category-based matching (capped lower, fallback only) ---
    category_score = 0.0
    category = _get_job_category(job_title)
    if category and category in REPO_TECH_MAPPING:
        cat_techs = REPO_TECH_MAPPING[category]
        cat_matches = sum(1 for t in cat_techs if t in deep_text)
        if cat_matches >= 1:
            category_score = min(cat_matches / len(cat_techs), 0.35)

    base_score = max(direct_score, category_score)
    if base_score == 0.0:
        return 0.0

    # --- Strategy 3: semantic name/topic match against job title ---
    repo_name_lower = (repo.get("name") or "").lower()
    name_words = set(w for w in re.split(r'[-_\s]+', repo_name_lower) if len(w) > 2)
    topic_words = set(w for w in repo_topics if len(w) > 2)
    semantic_words = name_words | topic_words

    title_words = set(w for w in re.split(r'[-_\s]+', job_title) if len(w) > 2)
    semantic_hits = sum(1 for w in semantic_words if w in job_title or w in job_desc)
    title_overlap = len(semantic_words & title_words)
    semantic_bonus = min(title_overlap * 0.12 + semantic_hits * 0.04, 0.30)
    base_score = min(base_score + semantic_bonus, 1.0)

    # --- Strategy 4: deep README domain matching ---
    # Detects whether repo is about GenAI vs CNN vs NLP etc., and checks
    # if the job is in the same domain. Penalizes domain mismatches.
    if readme:
        job_domains = _detect_domain(f"{job_title} {job_desc}")
        repo_domains = _detect_domain(deep_text)

        if job_domains and repo_domains:
            # Find the job's primary domain
            job_primary = max(job_domains, key=job_domains.get)
            repo_primary = max(repo_domains, key=repo_domains.get)

            if job_primary == repo_primary:
                # Same domain — boost score
                base_score = min(base_score + 0.15, 1.0)
                logger.debug(
                    f"[RepoOverlap] Domain MATCH: repo='{repo.get('name')}' "
                    f"job_domain={job_primary} repo_domain={repo_primary}"
                )
            elif repo_domains.get(job_primary, 0) > 0:
                # Repo has some relevance to job domain but it's not primary
                pass  # no penalty, no bonus
            else:
                # Domain mismatch — penalize (e.g. CNN repo for GenAI job)
                base_score *= 0.4
                logger.debug(
                    f"[RepoOverlap] Domain MISMATCH: repo='{repo.get('name')}' "
                    f"job_domain={job_primary} repo_domain={repo_primary} "
                    f"— score reduced to {base_score:.3f}"
                )

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
    ranked = []
    for j in jobs:
        if not _hard_filter(j, profile):
            continue
        sc = score_job(j, profile, github_repos)
        # Drop garbage matches that score below 25%
        if sc["score"] < 0.25:
            continue
            
        j["score"] = sc["score"]
        j["score_breakdown"] = sc["breakdown"]
        j["matched_skills"] = sc["matched_skills"]
        j["matched_projects"] = sc["matched_projects"]
        ranked.append(j)
    return sorted(ranked, key=lambda x: x["score"], reverse=True)
