"""
Opportunity Classifier — determines which lane (internship / notice / freelance)
an opportunity belongs to, based on source and keyword analysis.
"""

                                                                               

FREELANCE_SOURCE_KEYS = {
    "upwork", "fiverr", "freelancer", "guru", "toptal", "contra",
    "peopleperhour", "arc", "turing", "lemonio", "lemon.io",
    "gunio", "gun.io", "99designs", "ninetynine_designs",
    "dribbble", "behance", "braintrust", "xteam", "x-team",
    "workingnotworking",
}

NOTICE_SOURCE_KEYS = {
    "gmail", "telegram", "companycareers", "govtportal",
}

INTERNSHIP_SOURCE_KEYS = {
    "internshala", "indeed", "linkedin", "naukri",
    "foundit", "freshersworld", "cutshort", "wellfound",
    "workatastartup", "remoteok", "weworkremotely",
}

                                                                               

FREELANCE_SIGNALS = frozenset({
    "freelance", "freelancer", "gig", "contract work", "project-based",
    "hourly rate", "fixed price", "per project", "remote contract",
    "client", "deliverables", "milestone", "escrow", "proposal",
    "bid", "budget", "freelancing",
})

INTERNSHIP_SIGNALS = frozenset({
    "intern", "internship", "stipend", "training program", "semester",
    "co-op", "apprentice", "apprenticeship", "trainee", "fresh graduate",
    "fresher", "campus", "placement",
})


def classify(normalized: dict, source_key: str) -> str:
    """
    Classify a normalized opportunity into a lane.
    
    Returns:
        'internship' | 'notice' | 'freelance'
    """
    key = source_key.lower().replace(".", "").replace(" ", "").replace("-", "")

                                                                         
    if key in FREELANCE_SOURCE_KEYS or any(key.startswith(f) for f in FREELANCE_SOURCE_KEYS):
        return "freelance"
    if key in NOTICE_SOURCE_KEYS or source_key.startswith("Telegram/"):
        return "notice"
    if key in INTERNSHIP_SOURCE_KEYS:
        return "internship"

                                                                 
    opp_type = normalized.get("opportunity_type", "")
    if opp_type in ("internship", "freelance", "notice"):
        return opp_type

                                                         
    text = " ".join(filter(None, [
        normalized.get("title", ""),
        normalized.get("description", ""),
    ])).lower()

    freelance_hits = sum(1 for s in FREELANCE_SIGNALS if s in text)
    internship_hits = sum(1 for s in INTERNSHIP_SIGNALS if s in text)

    if freelance_hits > internship_hits and freelance_hits >= 2:
        return "freelance"

                           
    return "internship"
