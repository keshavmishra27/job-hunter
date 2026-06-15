"""
Competition Estimator Module

Calculates a Competition Advantage score (0.0 to 1.0) indicating how likely 
an opportunity is to have lower competition. Higher score = less competition.
"""

from datetime import datetime, timezone
import re
from loguru import logger
from backend.modules.ranker import TECH_KEYWORDS_SET

# Base advantage by source (0.0 to 1.0, higher is better/less crowded)
SOURCE_CROWD_LEVEL = {
    # Low competition (direct/niche)
    "CompanyCareers": 0.90,
    "Wellfound":      0.80,
    "WorkAtAStartup": 0.85,
    "TrueUp":         0.80,
    "Arc.dev":        0.75,
    "Himalayas":      0.75,
    "Cutshort":       0.70,
    # Medium competition
    "Internshala":    0.50,
    "Naukri":         0.45,
    "Foundit":        0.50,
    "Freshersworld":  0.45,
    # High competition (mass boards)
    "Indeed":         0.20,
    "LinkedIn":       0.15,
}

# Heuristic keywords for company size
STARTUP_KEYWORDS = {"startup", "early-stage", "seed", "series a", "small team", "founding", "stealth"}
LARGE_COMPANY_KEYWORDS = {"mnc", "fortune 500", "established", "enterprise", "global team"}

def _recency_advantage(item: dict) -> tuple[float, str | None]:
    """Calculate advantage based on recency.
    Returns (score, reason_string)
    """
    posted = item.get("posted_date") or item.get("posted_at")
    if not posted:
        return 0.5, "Unknown posting date"
    
    if isinstance(posted, str):
        try:
            posted = datetime.fromisoformat(posted)
        except ValueError:
            return 0.5, "Unknown posting date format"
            
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
        
    days_old = (datetime.now(tz=timezone.utc) - posted).days
    
    if days_old <= 3:
        return 1.0, f"Very recent (posted {days_old} days ago)"
    elif days_old <= 7:
        return 0.8, f"Recent (posted {days_old} days ago)"
    elif days_old <= 14:
        return 0.5, f"Moderately recent (posted {days_old} days ago)"
    elif days_old <= 30:
        return 0.2, f"Older post ({days_old} days ago)"
    else:
        return 0.0, f"Stale post ({days_old} days ago)"


def _source_crowd_advantage(source: str) -> tuple[float, str | None]:
    """Calculate advantage based on source platform."""
    # Match the source string exactly or fuzzy
    base_score = 0.5
    reason = f"Standard platform ({source})"
    
    for known_source, score in SOURCE_CROWD_LEVEL.items():
        if known_source.lower() in source.lower():
            base_score = score
            if score >= 0.7:
                reason = f"Less crowded source ({known_source})"
            elif score <= 0.3:
                reason = f"High competition platform ({known_source})"
            else:
                reason = f"Standard platform ({known_source})"
            break
            
    return base_score, reason


def _company_size_advantage(item: dict) -> tuple[float, str | None]:
    """Calculate advantage based on estimated company size."""
    desc = (item.get("description") or "").lower()
    
    if any(k in desc for k in STARTUP_KEYWORDS):
        return 0.8, "Likely startup or small team"
        
    if any(k in desc for k in LARGE_COMPANY_KEYWORDS):
        return 0.2, "Large/established enterprise"
        
    return 0.5, "Unknown company size"


def _role_specificity_advantage(title: str) -> tuple[float, str | None]:
    """Calculate advantage based on how niche the role is."""
    title_lower = title.lower()
    
    # Generic penalization
    if title_lower == "intern" or title_lower == "developer" or title_lower == "engineer":
        return 0.1, "Extremely generic title"
        
    # Check for niche techs in the title
    niche_count = 0
    for tech in TECH_KEYWORDS_SET:
        if " " in tech:
            if tech in title_lower:
                niche_count += 1
        else:
            if re.search(rf'(?<!\w){re.escape(tech)}(?!\w)', title_lower):
                niche_count += 1
                
    if niche_count >= 2:
        return 0.9, f"Highly specific role ({niche_count} tech keywords)"
    elif niche_count == 1:
        return 0.7, "Specific role title"
        
    return 0.4, "Standard role title"


def _applicant_signal_advantage(item: dict) -> tuple[float, str | None]:
    """Use real applicant counts if available (Future-proofing)."""
    # Currently fetchers don't populate this, but we'll reserve the spot.
    # If None, the parent function redistributes weight.
    return None, None


def _label_from_score(score: float) -> str:
    """Map a 0-1 score to a categorical label."""
    if score >= 0.66:
        return "low"
    elif score >= 0.33:
        return "medium"
    return "high"


def estimate_competition(item: dict) -> dict:
    """
    Computes a Competition Advantage score (0.0 - 1.0) and associated reasons.
    Higher score = Less Competition.
    """
    reasons = []
    
    rec_score, rec_reason = _recency_advantage(item)
    if rec_reason: reasons.append(rec_reason)
        
    src_score, src_reason = _source_crowd_advantage(item.get("source", ""))
    if src_reason: reasons.append(src_reason)
        
    co_score, co_reason = _company_size_advantage(item)
    # Only append reason if it's a strong signal, omit "Unknown company size" noise
    if co_score != 0.5: reasons.append(co_reason)
        
    role_score, role_reason = _role_specificity_advantage(item.get("title", ""))
    if role_score != 0.4: reasons.append(role_reason)

    app_score, app_reason = _applicant_signal_advantage(item)
    
    if app_score is not None:
        if app_reason: reasons.append(app_reason)
        advantage = (
            0.40 * rec_score +
            0.25 * src_score +
            0.20 * co_score +
            0.15 * app_score
        )
    else:
        # Redistribute the 0.15 weight if no applicant signal
        advantage = (
            0.40 * rec_score +
            0.35 * src_score +
            0.25 * co_score
        )
        
    # Boost slightly if it's highly specific role
    if role_score >= 0.7:
        advantage = min(advantage + 0.1, 1.0)
        
    # Cap between 0 and 1
    advantage = max(0.0, min(1.0, advantage))

    # Clean up reasons (max 3, sorted by importance heuristically)
    # Just return top 3
    final_reasons = reasons[:3] if reasons else ["No strong signals"]
    
    return {
        "competition_score": round(advantage, 3),
        "competition_label": _label_from_score(advantage),
        "competition_reasons": final_reasons
    }
