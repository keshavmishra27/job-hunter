import re
from datetime import datetime, timezone
from loguru import logger


def _text_of(notice: dict) -> str:
    parts = [notice.get("title") or "", notice.get("description") or "", notice.get("eligibility_text") or ""]
    return " ".join(parts).lower()


                                                                                       
_GRAD_TRIGGERS = [
    "grad", "grads", "gard", "gards", "graduate", "graduates",
    "batch", "passout", "pass out", "pass-out",
    "graduating", "graduating in", "class of",
    "fresher", "freshers",
]


def _extract_grad_years(text: str) -> set[int]:
    """
    Extract graduation years explicitly mentioned in a job/internship posting.
    Handles patterns like:
      - "For 2024, 2025 grads"
      - "2024 batch"
      - "graduating in 2025"
      - "class of 2025"
      - "2024-2025 passouts"
      - "2025 gards" (typo for grads)
    """
    t = text.lower()
    years: set[int] = set()

    for trigger in _GRAD_TRIGGERS:
        if trigger not in t:
            continue
        for m in re.finditer(re.escape(trigger), t):
                                                                  
            window_start = max(0, m.start() - 100)
            window_end   = min(len(t), m.end() + 100)
            context = t[window_start:window_end]
            for yr in re.findall(r'\b(202[0-9]|203[0-2])\b', context):
                years.add(int(yr))

    return years


def _year_fit_score(notice: dict, profile: dict | None = None) -> float:
    t = _text_of(notice)

                                                            
    CONFIRM = ["3rd year", "3rd-year", "third year", "pre-final", "prefinal", "pre final", "3rd"]
    for kw in CONFIRM:
        if kw in t:
            return 1.0

                                                             
    EXCLUDE = [
        "final year only", "only final year", "final year students only",
        "post graduate", "postgraduate", "post-graduate",
        "mba required", "mba preferred", "phd", "experienced professional",
        "minimum 2 years", "minimum 3 years", "minimum 5 years",
        "2+ years", "3+ years", "5+ years",
    ]
    for kw in EXCLUDE:
        if kw in t:
            return 0.0

                                             
                                                                  
                                                               
    if profile:
        user_grad_year = profile.get("graduation_year")
        if user_grad_year:
            mentioned_years = _extract_grad_years(t)
            if mentioned_years:
                if user_grad_year in mentioned_years:
                    logger.debug(
                        f"[YearFit] Grad year {user_grad_year} found in posting years {mentioned_years} → eligible"
                    )
                    return 1.0
                else:
                    logger.debug(
                        f"[YearFit] Grad year {user_grad_year} NOT in posting years {mentioned_years} → not eligible"
                    )
                    return 0.0

                                                                 
    return 1.0


def _role_score(notice: dict, profile: dict) -> tuple[float, list[str]]:
    preferred = [r.lower() for r in (profile.get("preferred_roles") or [])]
    if not preferred:
        return 0.5, []
    text = _text_of(notice)
    matched = []
    for role in preferred:
        words = [w for w in role.split() if len(w) > 2]
        if any(w in text for w in words):
            matched.append(role)
    return min(len(matched) / max(len(preferred), 1), 1.0), matched


def _skill_score(notice: dict, profile: dict) -> tuple[float, list[str]]:
    skills = [s.lower() for s in (profile.get("skills") or [])]
    if not skills:
        return 0.4, []
    text = _text_of(notice)
    matched = [s for s in skills if s in text]
    return min(len(matched) / max(len(skills), 1), 1.0), matched


def _location_score(notice: dict, profile: dict) -> float:
    mode = (notice.get("mode") or "offline")
    if mode == "remote":
        return 1.0
    loc = (notice.get("location") or "").lower()
    allowed = [loc.lower() for loc in profile.get("location_rule", {}).get("offline_allowed", [])]
    if any(a in loc or loc in a for a in allowed if a):
        return 1.0
    return 0.3


def _company_score(notice: dict, profile: dict) -> float:
                                                                              
    preferred_companies = [c.lower() for c in (profile.get("preferred_companies") or [])]
    if not preferred_companies:
        return 0.5
    comp = (notice.get("company") or "").lower()
    if comp in preferred_companies:
        return 1.0
    return 0.3


def _deadline_urgency_score(notice: dict) -> float:
    d = notice.get("deadline")
    if not d:
                                                   
        return 0.5
    try:
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        days_left = (d - now).days
        if days_left < 0:
            return 0.0
        return max(0.0, 1.0 - days_left / 30)
    except Exception:
        return 0.5


def score_notice_detailed(notice: dict, profile: dict, github_repos: list[dict] | None = None) -> dict:
    """Score a notice on a 0-10 scale and return breakdown and matched skills/projects."""
    year = _year_fit_score(notice, profile)
    role, matched_roles = _role_score(notice, profile)
    skill, matched_skills = _skill_score(notice, profile)
    loc = _location_score(notice, profile)
    comp = _company_score(notice, profile)
    urgency = _deadline_urgency_score(notice)

                        
    weights = {
        "year_fit": 0.25,
        "role_match": 0.20,
        "skill_match": 0.20,
        "location_fit": 0.10,
        "company_fit": 0.10,
        "deadline_urgency": 0.15,
    }

    breakdown = {
        "year_fit": year,
        "role_match": role,
        "skill_match": skill,
        "location_fit": loc,
        "company_fit": comp,
        "deadline_urgency": urgency,
    }

    total = sum(breakdown[k] * weights.get(k, 0) for k in breakdown)
    score_0_10 = round(total * 10, 3)
    logger.debug(f"[InternScorer] breakdown={breakdown} -> score={score_0_10}")

    return {
        "score": score_0_10,
        "breakdown": breakdown,
        "matched_skills": matched_skills,
        "matched_roles": matched_roles,
    }
