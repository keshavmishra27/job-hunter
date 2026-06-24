"""
Freelance Scoring Engine — scores freelance gigs on a 0–1 scale.

This is a SEPARATE scoring brain from the internship scorer (ranker.py / internship_scorer.py).
Different weights, different factors, different logic.
"""
import re
import math
from datetime import datetime, timezone
from loguru import logger


                                                                              

FREELANCE_WEIGHTS = {
    "skill_match":        0.30,
    "budget_fit":         0.20,
    "task_clarity":       0.15,
    "client_quality":     0.15,
    "deadline_fit":       0.10,
    "project_relevance":  0.10,
}

                                                                    
_TECH_KEYWORDS: set[str] | None = None


def _get_tech_keywords() -> set[str]:
    """Lazy-load tech keywords from the ranker module to avoid circular imports."""
    global _TECH_KEYWORDS
    if _TECH_KEYWORDS is None:
        try:
            from backend.modules.ranker import TECH_KEYWORDS_SET
            _TECH_KEYWORDS = TECH_KEYWORDS_SET
        except ImportError:
            _TECH_KEYWORDS = {
                "python", "javascript", "typescript", "react", "vue", "angular",
                "fastapi", "django", "flask", "node", "express",
                "tensorflow", "pytorch", "pandas", "numpy",
                "docker", "kubernetes", "aws", "gcp", "azure",
                "sql", "postgres", "mongodb", "redis",
                "machine learning", "deep learning", "nlp", "llm",
                "langchain", "openai", "huggingface",
            }
    return _TECH_KEYWORDS


def _extract_tech(text: str) -> set[str]:
    """Extract recognized tech keywords from text."""
    found = set()
    text_lower = text.lower()
    for tech in _get_tech_keywords():
        if " " in tech:
            if tech in text_lower:
                found.add(tech)
        else:
            if re.search(rf'(?<!\w){re.escape(tech)}(?!\w)', text_lower):
                found.add(tech)
    return found


                                                                              

def _skill_match(opp: dict, profile: dict) -> tuple[float, list[str]]:
    """Score 0–1 based on tech keyword overlap between gig and user skills."""
    profile_skills = [s.lower() for s in (profile.get("skills") or [])]
    if not profile_skills:
        return 0.5, []

    text = " ".join(filter(None, [
        opp.get("title", ""),
        opp.get("description", ""),
        " ".join(opp.get("required_skills") or []),
    ])).lower()

    matched = []
    for s in profile_skills:
        if re.search(rf'(?<!\w){re.escape(s)}(?!\w)', text):
            matched.append(s)

                                              
    req_skills = [s.lower() for s in (opp.get("required_skills") or [])]
    for rs in req_skills:
        for ps in profile_skills:
            if ps in rs or rs in ps:
                if ps not in matched:
                    matched.append(ps)

    score = min(len(matched) / max(len(profile_skills), 1), 1.0)
    return score, matched


def _budget_fit(opp: dict, profile: dict) -> float:
    """
    Score 0–1 based on budget range vs user expectations.
    
    If no budget info: 0.5 (neutral).
    If budget is above user's minimum: score scales up.
    If budget is below user's minimum: score drops.
    """
    budget_min = opp.get("budget_min")
    budget_max = opp.get("budget_max")

    if budget_min is None and budget_max is None:
        return 0.5                            

                                                                   
    budget = budget_max or budget_min or 0

                                                         
    user_min_rate = profile.get("hourly_rate_min", 10)
    user_max_rate = profile.get("hourly_rate_max", 50)

    budget_type = opp.get("budget_type", "fixed")

    if budget_type == "hourly":
                                      
        if budget >= user_max_rate:
            return 1.0
        elif budget >= user_min_rate:
            return 0.6 + 0.4 * (budget - user_min_rate) / max(user_max_rate - user_min_rate, 1)
        else:
            return max(0.1, budget / max(user_min_rate, 1))
    else:
                                                                              
        if budget >= 500:
            return 1.0
        elif budget >= 200:
            return 0.8
        elif budget >= 50:
            return 0.5
        elif budget > 0:
            return 0.3
        return 0.5


def _task_clarity(opp: dict) -> float:
    """
    Score 0–1 based on how well the gig is described.
    
    A well-described gig has:
    - Long description (300+ chars)
    - Deliverables mentioned
    - Required skills listed
    - Clear timeline
    """
    desc = opp.get("description") or ""
    deliverables = opp.get("deliverables") or ""
    req_skills = opp.get("required_skills") or []

    score = 0.0

                        
    desc_len = len(desc)
    if desc_len > 500:
        score += 0.35
    elif desc_len > 200:
        score += 0.25
    elif desc_len > 50:
        score += 0.15
    else:
        score += 0.05

                          
    if deliverables and len(deliverables) > 20:
        score += 0.25
    elif deliverables:
        score += 0.10

                            
    if len(req_skills) >= 3:
        score += 0.25
    elif len(req_skills) >= 1:
        score += 0.15

                                 
    if opp.get("delivery_time_days") or opp.get("deadline"):
        score += 0.15

    return min(score, 1.0)


def _client_quality(opp: dict) -> float:
    """
    Score 0–1 based on client trustworthiness signals.
    
    - Client rating (out of 5)
    - Payment verification
    - Number of reviews
    """
    rating = opp.get("client_rating")
    verified = opp.get("payment_verified", False)
    reviews = opp.get("client_reviews_count", 0)

    score = 0.3                            

                                 
    if rating is not None:
        score = min(rating / 5.0, 1.0) * 0.5

                            
    if verified:
        score += 0.25

                        
    if reviews and reviews > 0:
        review_score = min(math.log(reviews + 1) / math.log(100), 1.0) * 0.25
        score += review_score

    return min(score, 1.0)


def _deadline_fit(opp: dict) -> float:
    """
    Score 0–1 based on delivery timeline reasonableness.
    
    - Very short (< 3 days): low score (rushed)
    - Medium (1–4 weeks): high score (sweet spot)
    - Long (> 3 months): slightly lower (long commitment)
    """
    days = opp.get("delivery_time_days")
    deadline = opp.get("deadline")

    if days is None and deadline:
        try:
            d = deadline if isinstance(deadline, datetime) else datetime.fromisoformat(str(deadline))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            days = (d - datetime.now(tz=timezone.utc)).days
        except Exception:
            pass

    if days is None:
        return 0.5                              

    if days < 0:
        return 0.0           
    if days <= 2:
        return 0.3              
    if days <= 7:
        return 0.7                    
    if days <= 30:
        return 1.0              
    if days <= 90:
        return 0.8              
    return 0.6                  


def _project_relevance(opp: dict, profile: dict, github_repos: list[dict] | None = None) -> tuple[float, list[str]]:
    """
    Score 0–1 based on project overlap with user's portfolio.
    Reuses tech-keyword extraction logic.
    """
    projects = profile.get("projects") or []
    text = " ".join(filter(None, [
        opp.get("title", ""),
        opp.get("description", ""),
    ])).lower()

    gig_techs = _extract_tech(text)
    if not gig_techs:
        return 0.3, []

    best_score = 0.0
    matched_projects = []

    for project in projects:
        proj_techs = _extract_tech(project)
        if proj_techs and gig_techs:
            common = proj_techs & gig_techs
            if common:
                ps = len(common) / max(len(proj_techs), len(gig_techs))
                if ps > best_score:
                    best_score = ps
                    matched_projects.append(project)

                                       
    if github_repos:
        for repo in github_repos:
            repo_text = " ".join(filter(None, [
                repo.get("description", ""),
                " ".join(repo.get("topics") or []),
                repo.get("language", ""),
            ])).lower()
            repo_techs = _extract_tech(repo_text)
            if repo_techs and gig_techs:
                common = repo_techs & gig_techs
                if common:
                    rs = len(common) / max(len(repo_techs), len(gig_techs))
                    if rs > best_score:
                        best_score = rs
                    matched_projects.append(f"[GitHub] {repo.get('name', 'repo')}")

    return min(best_score, 1.0), matched_projects[:5]


                                                                              

def score_freelance(opp: dict, profile: dict, github_repos: list[dict] | None = None) -> dict:
    """
    Score a single freelance opportunity on a 0–1 scale.
    
    Returns:
        {
            "score": float,
            "breakdown": {factor: float, ...},
            "matched_skills": [str, ...],
            "matched_projects": [str, ...],
        }
    """
    skill_score, matched_skills = _skill_match(opp, profile)
    budget = _budget_fit(opp, profile)
    clarity = _task_clarity(opp)
    client = _client_quality(opp)
    deadline = _deadline_fit(opp)
    relevance, matched_projects = _project_relevance(opp, profile, github_repos)

    breakdown = {
        "skill_match": skill_score,
        "budget_fit": budget,
        "task_clarity": clarity,
        "client_quality": client,
        "deadline_fit": deadline,
        "project_relevance": relevance,
    }

    total = sum(FREELANCE_WEIGHTS[k] * v for k, v in breakdown.items())

    logger.debug(
        f"[FreelanceScorer] breakdown={breakdown} → score={total:.4f} | "
        f"title='{opp.get('title', '')[:50]}'"
    )

    return {
        "score": round(total, 4),
        "breakdown": breakdown,
        "matched_skills": matched_skills,
        "matched_projects": matched_projects,
    }


def _hard_filter_freelance(opp: dict, profile: dict) -> bool:
    """Hard filters for freelance gigs — drop obviously irrelevant items."""
    title = (opp.get("title") or "").strip().lower()
    if not title or title == "unknown":
        return False
    return True


def rank_freelance(
    opps: list[dict],
    profile: dict,
    github_repos: list[dict] | None = None,
) -> list[dict]:
    """Hard-filter, score, and rank a list of freelance opportunities."""
    ranked = []
    for opp in opps:
        if not _hard_filter_freelance(opp, profile):
            continue
        sc = score_freelance(opp, profile, github_repos)
                                        
        if sc["score"] < 0.20:
            continue
        opp["score"] = sc["score"]
        opp["score_breakdown"] = sc["breakdown"]
        opp["matched_skills"] = sc["matched_skills"]
        opp["matched_projects"] = sc["matched_projects"]
        ranked.append(opp)

    return sorted(ranked, key=lambda x: x["score"], reverse=True)
