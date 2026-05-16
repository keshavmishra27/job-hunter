ROLE_PROFILES = {
    "backend": {
        "label": "Backend Developer",
        "weights": {
            "uniqueness": 0.20,
            "code_quality": 0.40,
            "documentation": 0.30,
            "uiux": 0.10,
        },
        "description": "Emphasises clean architecture, API design, and code structure over visual polish.",
    },
    "frontend": {
        "label": "Frontend Developer",
        "weights": {
            "uniqueness": 0.15,
            "code_quality": 0.25,
            "documentation": 0.20,
            "uiux": 0.40,
        },
        "description": "Prioritises UI/UX quality, responsive design, and visual polish.",
    },
    "fullstack": {
        "label": "Full-Stack Developer",
        "weights": {
            "uniqueness": 0.20,
            "code_quality": 0.30,
            "documentation": 0.25,
            "uiux": 0.25,
        },
        "description": "Balanced evaluation across all dimensions.",
    },
    "mlops": {
        "label": "MLOps Engineer",
        "weights": {
            "uniqueness": 0.25,
            "code_quality": 0.30,
            "documentation": 0.35,
            "uiux": 0.10,
        },
        "description": "Values pipeline architecture, reproducibility, and thorough documentation.",
    },
    "data_science": {
        "label": "Data Scientist",
        "weights": {
            "uniqueness": 0.30,
            "code_quality": 0.25,
            "documentation": 0.35,
            "uiux": 0.10,
        },
        "description": "Focuses on novel analysis, methodology documentation, and result presentation.",
    },
    "agentic_ai": {
        "label": "Agentic AI Developer",
        "weights": {
            "uniqueness": 0.40,
            "code_quality": 0.25,
            "documentation": 0.25,
            "uiux": 0.10,
        },
        "description": "Heavily weights originality and problem-solving innovation.",
    },
    "devops": {
        "label": "DevOps / SRE",
        "weights": {
            "uniqueness": 0.15,
            "code_quality": 0.35,
            "documentation": 0.35,
            "uiux": 0.15,
        },
        "description": "Values infrastructure-as-code, CI/CD, containerisation, and operational docs.",
    },
    "mobile": {
        "label": "Mobile Developer",
        "weights": {
            "uniqueness": 0.20,
            "code_quality": 0.25,
            "documentation": 0.20,
            "uiux": 0.35,
        },
        "description": "Prioritises UI polish, responsive design, and clean component architecture.",
    },
}


def get_role_weights(role: str) -> dict:
    profile = ROLE_PROFILES.get(role)
    if not profile:
        return ROLE_PROFILES["fullstack"]["weights"]
    return profile["weights"]


def list_roles() -> list[dict]:
    return [
        {"id": k, "label": v["label"], "description": v["description"]}
        for k, v in ROLE_PROFILES.items()
    ]
