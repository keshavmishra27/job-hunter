import re
from loguru import logger


UI_EXTENSIONS = {
    ".html", ".css", ".jsx", ".tsx", ".vue", ".svelte",
    ".scss", ".sass", ".less", ".styl",
}
UI_FRAMEWORKS = {
    "react", "vue", "angular", "svelte", "next", "nuxt",
    "gatsby", "tailwind", "bootstrap", "material-ui", "chakra",
}
CI_FILES = {
    ".github/workflows", "Jenkinsfile", ".travis.yml",
    ".circleci", "azure-pipelines.yml", ".gitlab-ci.yml",
}
DEPLOY_SIGNALS = {
    "vercel.json", "netlify.toml", "Procfile", "app.yaml",
    "fly.toml", "render.yaml", "railway.json", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml",
}
TEST_PATTERNS = {"test_", "_test.", ".test.", ".spec.", "tests/", "__tests__/"}


def analyze_readme(readme: str | None) -> dict:
    if not readme:
        return {
            "has_readme": False,
            "readme_length": 0,
            "has_problem_statement": False,
            "has_features_section": False,
            "has_setup_instructions": False,
            "has_architecture_info": False,
            "has_screenshots": False,
            "has_api_docs": False,
            "has_future_scope": False,
        }

    text = readme.lower()
    length = len(readme)

    return {
        "has_readme": True,
        "readme_length": length,
        "has_problem_statement": any(
            kw in text for kw in [
                "problem", "motivation", "why", "challenge", "objective",
                "goal", "purpose", "about this project",
            ]
        ),
        "has_features_section": any(
            kw in text for kw in ["features", "what it does", "capabilities", "highlights"]
        ),
        "has_setup_instructions": any(
            kw in text for kw in [
                "install", "setup", "getting started", "quick start",
                "how to run", "usage", "prerequisites",
            ]
        ),
        "has_architecture_info": any(
            kw in text for kw in [
                "architecture", "system design", "tech stack", "design",
                "structure", "overview", "diagram", "flow",
            ]
        ),
        "has_screenshots": bool(re.search(r"!\[.*?\]\(.*?\)", readme)) or "screenshot" in text,
        "has_api_docs": any(
            kw in text for kw in ["api", "endpoint", "route", "request", "response"]
        ),
        "has_future_scope": any(
            kw in text for kw in [
                "future", "roadmap", "todo", "planned", "upcoming",
                "next steps", "improvements", "enhancements",
            ]
        ),
    }


def analyze_tree(tree: list[dict]) -> dict:
    paths = [item["path"] for item in tree]
    types = {item["path"]: item["type"] for item in tree}

    files = [p for p in paths if types.get(p) == "blob"]
    dirs = [p for p in paths if types.get(p) == "tree"]

    extensions = set()
    for f in files:
        if "." in f:
            ext = "." + f.rsplit(".", 1)[-1].lower()
            extensions.add(ext)

    has_ui = bool(extensions & UI_EXTENSIONS)
    has_tests = any(any(tp in f.lower() for tp in TEST_PATTERNS) for f in files)
    has_ci_cd = any(any(ci in f for ci in CI_FILES) for f in paths)
    has_docker = any(f.lower() in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"} or f.lower().startswith("dockerfile") for f in files)
    has_deployment = any(f.lower() in DEPLOY_SIGNALS or any(ds in f.lower() for ds in DEPLOY_SIGNALS) for f in files)
    has_env_example = any(f.lower() in {".env.example", ".env.sample", "env.example"} for f in files)
    has_requirements = any(f.lower() in {"requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "pipfile"} for f in files)
    has_package_json = any(f.lower() == "package.json" for f in files)
    has_gitignore = any(f.lower() == ".gitignore" for f in files)
    has_license = any(f.lower().startswith("license") for f in files)
    has_contributing = any(f.lower().startswith("contributing") for f in files)

    top_dirs = set()
    for d in dirs:
        top = d.split("/")[0]
        top_dirs.add(top)

    return {
        "file_count": len(files),
        "directory_count": len(dirs),
        "top_level_dirs": sorted(top_dirs),
        "extensions": sorted(extensions),
        "has_ui": has_ui,
        "has_tests": has_tests,
        "has_ci_cd": has_ci_cd,
        "has_docker": has_docker,
        "has_deployment": has_deployment,
        "has_env_example": has_env_example,
        "has_requirements": has_requirements,
        "has_package_json": has_package_json,
        "has_gitignore": has_gitignore,
        "has_license": has_license,
        "has_contributing": has_contributing,
    }


def analyze_repo(readme: str | None, tree: list[dict], repo_meta: dict) -> dict:
    readme_signals = analyze_readme(readme)
    tree_signals = analyze_tree(tree)

    description = repo_meta.get("description") or ""
    topics = repo_meta.get("topics") or []
    has_demo_link = bool(repo_meta.get("homepage"))

    has_ui_from_topics = any(t in UI_FRAMEWORKS for t in topics)

    combined = {
        **readme_signals,
        **tree_signals,
        "has_ui": tree_signals["has_ui"] or has_ui_from_topics,
        "has_demo_link": has_demo_link,
        "description": description,
        "topics": topics,
    }

    logger.debug(f"[Analyzer] {repo_meta.get('name', '?')}: "
                 f"files={tree_signals['file_count']}, "
                 f"readme={readme_signals['readme_length']}chars, "
                 f"ui={combined['has_ui']}, tests={tree_signals['has_tests']}")

    return combined
