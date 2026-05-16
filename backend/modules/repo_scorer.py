from loguru import logger
from backend.modules.role_profiles import get_role_weights


def score_uniqueness(analysis: dict, all_analyses: list[dict] | None = None) -> float:
    score = 5.0

    topics = analysis.get("topics") or []
    description = (analysis.get("description") or "").lower()

    common_patterns = [
        "todo", "calculator", "weather", "portfolio", "blog",
        "chat", "e-commerce", "ecommerce", "crud", "landing page",
    ]
    is_common = any(p in description for p in common_patterns) or any(p in " ".join(topics).lower() for p in common_patterns)

    if is_common:
        score -= 2.0
    else:
        score += 2.0

    if len(topics) >= 3:
        score += 1.0
    if analysis.get("has_problem_statement"):
        score += 1.0

    file_count = analysis.get("file_count", 0)
    if file_count > 20:
        score += 0.5
    if file_count > 50:
        score += 0.5

    return max(0.0, min(10.0, score))


def score_code_quality(analysis: dict) -> float:
    score = 3.0

    dir_count = analysis.get("directory_count", 0)
    file_count = analysis.get("file_count", 0)

    if dir_count >= 3:
        score += 1.0
    if dir_count >= 6:
        score += 1.0

    if file_count >= 10:
        score += 0.5
    if file_count >= 30:
        score += 0.5

    if analysis.get("has_tests"):
        score += 1.5
    if analysis.get("has_ci_cd"):
        score += 1.0
    if analysis.get("has_docker"):
        score += 0.5
    if analysis.get("has_gitignore"):
        score += 0.5
    if analysis.get("has_env_example"):
        score += 0.5
    if analysis.get("has_requirements") or analysis.get("has_package_json"):
        score += 0.5

    return max(0.0, min(10.0, score))


def score_documentation(analysis: dict) -> float:
    score = 0.0

    if analysis.get("has_readme"):
        score += 2.0

    readme_len = analysis.get("readme_length", 0)
    if readme_len > 500:
        score += 1.0
    if readme_len > 1500:
        score += 1.0
    if readme_len > 3000:
        score += 0.5

    if analysis.get("has_problem_statement"):
        score += 1.0
    if analysis.get("has_features_section"):
        score += 1.0
    if analysis.get("has_setup_instructions"):
        score += 1.0
    if analysis.get("has_architecture_info"):
        score += 1.0
    if analysis.get("has_screenshots"):
        score += 0.5
    if analysis.get("has_api_docs"):
        score += 0.5
    if analysis.get("has_future_scope"):
        score += 0.5

    return max(0.0, min(10.0, score))


def score_uiux(analysis: dict) -> float:
    score = 2.0

    if analysis.get("has_ui"):
        score += 3.0
    if analysis.get("has_screenshots"):
        score += 1.5
    if analysis.get("has_demo_link"):
        score += 2.0
    if analysis.get("has_deployment"):
        score += 1.5

    return max(0.0, min(10.0, score))


def compute_repo_score(analysis: dict, role: str, all_analyses: list[dict] | None = None) -> dict:
    weights = get_role_weights(role)

    u = score_uniqueness(analysis, all_analyses)
    c = score_code_quality(analysis)
    d = score_documentation(analysis)
    x = score_uiux(analysis)

    final = (
        u * weights["uniqueness"]
        + c * weights["code_quality"]
        + d * weights["documentation"]
        + x * weights["uiux"]
    )

    breakdown = {
        "uniqueness": {"score": round(u, 2), "weight": weights["uniqueness"]},
        "code_quality": {"score": round(c, 2), "weight": weights["code_quality"]},
        "documentation": {"score": round(d, 2), "weight": weights["documentation"]},
        "uiux": {"score": round(x, 2), "weight": weights["uiux"]},
    }

    return {
        "uniqueness_score": round(u, 2),
        "code_quality_score": round(c, 2),
        "documentation_score": round(d, 2),
        "uiux_score": round(x, 2),
        "final_score": round(final, 2),
        "breakdown": breakdown,
    }


def generate_selection_reason(scores: dict, role: str) -> str:
    parts = []
    best_metric = max(
        ["uniqueness", "code_quality", "documentation", "uiux"],
        key=lambda m: scores.get(f"{m}_score", 0),
    )
    metric_labels = {
        "uniqueness": "project uniqueness",
        "code_quality": "code quality & structure",
        "documentation": "documentation completeness",
        "uiux": "UI/UX & deployment presence",
    }
    parts.append(f"Strongest in {metric_labels[best_metric]} ({scores[f'{best_metric}_score']}/10).")

    if scores["final_score"] >= 7:
        parts.append("Overall excellent project for this role.")
    elif scores["final_score"] >= 5:
        parts.append("Solid project with room for improvement.")
    else:
        parts.append("Needs improvement in several areas.")

    return " ".join(parts)


def rank_and_select_top5(
    repos_with_scores: list[dict],
    role: str,
) -> list[dict]:
    sorted_repos = sorted(repos_with_scores, key=lambda r: r["final_score"], reverse=True)

    for i, repo in enumerate(sorted_repos):
        repo["rank"] = i + 1
        repo["is_top5"] = i < 5
        if i < 5:
            repo["selection_reason"] = generate_selection_reason(repo, role)

    logger.info(f"[Scorer] Ranked {len(sorted_repos)} repos for role '{role}', top 5 selected")
    return sorted_repos
