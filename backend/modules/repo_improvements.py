SIGNAL_REASONS = {
    "has_readme": {
        "why": "README.md is the first thing recruiters and engineers look at. It's essential for understanding the project at a glance.",
        "fix": "✓ Great! Your README is well-documented. | ✗ Create a README.md at the root with a title, description, and 'how to run' section.",
    },
    "has_problem_statement": {
        "why": "Explaining the problem your project solves shows critical thinking and real-world relevance—key for senior roles.",
        "fix": "✓ Excellent motivation statement found! | ✗ Add a 'Motivation' or 'Problem Statement' section explaining the pain point you solved.",
    },
    "has_features_section": {
        "why": "A clear feature list helps readers quickly understand what your project does and its value proposition.",
        "fix": "✓ Features are well-documented! | ✗ Add a '## Features' section with 3-5 bullet points describing key capabilities.",
    },
    "has_setup_instructions": {
        "why": "Clear setup/installation steps show professionalism and make your project reproducible—critical for production-ready code.",
        "fix": "✓ Good setup documentation! | ✗ Add a '## Getting Started' section with exact commands: clone, install deps, configure env, run.",
    },
    "has_architecture_info": {
        "why": "System architecture description demonstrates your design thinking and helps others understand the codebase structure.",
        "fix": "✓ Architecture is well-explained! | ✗ Add a '## Architecture' section with tech stack list and a brief explanation of data flow.",
    },
    "has_screenshots": {
        "why": "Visual previews dramatically increase engagement and show the project works—especially important for frontend/full-stack roles.",
        "fix": "✓ Great visual documentation! | ✗ Take a screenshot of the running app and embed it in the README.",
    },
    "has_api_docs": {
        "why": "API documentation is a hallmark of professional backend development and makes integration straightforward.",
        "fix": "✓ API is well-documented! | ✗ Add a '## API Reference' section with endpoints, methods, and example payloads or link to /docs.",
    },
    "has_future_scope": {
        "why": "A roadmap signals that you're thinking long-term and actively developing—projects with clear vision are more impressive.",
        "fix": "✓ Nice roadmap included! | ✗ Add a '## Roadmap' or '## Future Scope' section with 2-3 planned improvements.",
    },
    "has_tests": {
        "why": "Test files are a critical signal of code quality and professionalism. Companies expect to see testing practices.",
        "fix": "✓ Good test coverage! | ✗ Add at least 3-5 unit tests using pytest (Python) or Jest (JS/TS) for your core logic.",
    },
    "has_ci_cd": {
        "why": "CI/CD pipelines are expected in modern development—they show you understand DevOps and automated testing.",
        "fix": "✓ Automated testing pipeline is set up! | ✗ Create .github/workflows/test.yml with a workflow that runs tests on every push.",
    },
    "has_docker": {
        "why": "Containerization shows DevOps awareness and guarantees your project runs reliably in any environment.",
        "fix": "✓ Project is containerized! | ✗ Add a Dockerfile and optionally docker-compose.yml for multi-service projects.",
    },
    "has_ui": {
        "why": "A frontend component makes your project tangible and interactive—crucial for full-stack and frontend roles.",
        "fix": "✓ Great UI/UX demonstrated! | ✗ Add a basic UI using React, Vue, or HTML. For backend-only, consider a Swagger UI or dashboard.",
    },
    "has_deployment": {
        "why": "A deployed, live project is infinitely more impressive than one that only runs locally—it proves it works in production.",
        "fix": "✓ Project is deployed and live! | ✗ Deploy to a free tier (Vercel, Netlify, Railway, Fly.io) and set the repo 'Website' field.",
    },
    "has_demo_link": {
        "why": "A live demo is the single biggest differentiator in project-based hiring—recruiters want to try it, not just read about it.",
        "fix": "✓ Live demo is available! | ✗ Deploy the project and set the GitHub repository's 'Website' field to the live URL.",
    },
    "has_license": {
        "why": "A LICENSE file is essential for open source projects and shows you understand intellectual property and legal standards.",
        "fix": "✓ Proper licensing in place! | ✗ Add a LICENSE file (MIT License is a good default for open source projects).",
    },
    "has_contributing": {
        "why": "A CONTRIBUTING guide signals professional project hygiene and makes it clear how others can contribute.",
        "fix": "✓ Contributing guide provided! | ✗ Add a brief CONTRIBUTING.md with fork, branch, and PR submission instructions.",
    },
}

ROLE_TIPS = {
    "backend": [
        {
            "title": "Structure your codebase",
            "tip": "Organise code into clear layers: routers/controllers, services/business logic, and data/models. Avoid putting everything in a single file.",
        },
        {
            "title": "Document your API",
            "tip": "Use FastAPI's built-in /docs or add an API reference in the README with real request/response examples.",
        },
        {
            "title": "Write integration tests",
            "tip": "For backend roles, test your API endpoints using pytest + httpx (FastAPI) or supertest (Express). Cover the happy path and at least one error case per endpoint.",
        },
        {
            "title": "Containerise the app",
            "tip": "Add a Dockerfile so the app can be run without a local setup. Include a docker-compose.yml if you have a database.",
        },
        {
            
            "title": "Show environment config hygiene",
            "tip": "Add a `.env.example` file listing all required environment variables (without real secrets). This is a standard professional practice.",
        },
    ],
    "frontend": [
        {
            
            "title": "Add screenshots and a live demo",
            "tip": "Frontend recruiters skim visually. Embed screenshots in the README and deploy to Vercel/Netlify so they can interact with it.",
        },
        {
            
            "title": "Make it responsive",
            "tip": "Ensure the UI works on mobile viewports. Add a note in the README about responsive design support.",
        },
        {
            
            "title": "Mention accessibility",
            "tip": "Even a short note about keyboard navigation, ARIA labels, or colour contrast shows senior-level awareness.",
        },
        {
            
            "title": "Highlight performance choices",
            "tip": "Mention code splitting, lazy loading, or bundle optimisation decisions. This differentiates you from basic CRUD projects.",
        },
        {
            
            "title": "Add component tests",
            "tip": "Use Vitest + Testing Library or Jest to write at least a few component-level tests. This is increasingly expected even for junior roles.",
        },
    ],
    "fullstack": [
        {
            
            "title": "Show the full data flow",
            "tip": "In the README, describe how data flows from the database through the API to the UI. A simple diagram (even ASCII) helps recruiters understand the system.",
        },
        {
            
            "title": "Deploy the entire stack",
            "tip": "Deploy both frontend and backend. Use Railway or Render for the backend and Vercel for the frontend. Mention the URLs prominently.",
        },
        {
            
            "title": "Document your database schema",
            "tip": "Add a database schema diagram or at least list your main models and their relationships in the README.",
        },
        {
            
            "title": "Implement auth (if missing)",
            "tip": "Projects with authentication (JWT, OAuth) demonstrate real-world readiness. If auth isn't appropriate, explain why in the README.",
        },
        {
            
            "title": "Separate concerns clearly",
            "tip": "Make sure the frontend and backend are clearly separated (different folders or repos). Show you understand the distinction between client and server code.",
        },
    ],
    "mlops": [
        {
            
            "title": "Show your pipeline as code",
            "tip": "Use tools like Prefect, Airflow, or even a Makefile to define the ML pipeline (data → train → evaluate → serve) as reproducible code.",
        },
        {
            
            "title": "Log experiments",
            "tip": "Integrate MLflow, Weights & Biases, or DVC to track experiment results. Even a CSV of results with a comparison table in the README counts.",
        },
        {
           
            "title": "Containerise model serving",
            "tip": "Wrap your model in a FastAPI/Flask app and containerise it with Docker. This shows you understand how models go from notebooks to production.",
        },
        {
            
            "title": "Pin your dependencies",
            "tip": "Use `requirements.txt` with pinned versions or a `pyproject.toml`. Reproducible environments are critical in ML contexts.",
        },
        {
            
            "title": "Document model performance",
            "tip": "Add a '## Results' section with key metrics (accuracy, F1, latency) and compare to a baseline. This is the most important thing for an ML project.",
        },
    ],
    "data_science": [
        {
            
            "title": "Structure your notebooks",
            "tip": "Notebooks should be named clearly (e.g., `01_eda.ipynb`, `02_feature_eng.ipynb`) and have markdown cells explaining each step.",
        },
        {
            
            "title": "Show your results clearly",
            "tip": "Add a '## Key Findings' section with the most important insights. Include charts as images in the README.",
        },
        {
            
            "title": "Document your methodology",
            "tip": "Explain your approach: what models you tried, why you chose the final one, and what the limitations are.",
        },
        {
            
            "title": "Describe your dataset",
            "tip": "Add a '## Data' section explaining the source, size, and key features. Link to the dataset if it's public.",
        },
        {
            
            "title": "Add a reproducibility script",
            "tip": "Add a `run_all.sh` or Makefile that runs all notebooks/scripts in order. This shows the project isn't just a collection of random files.",
        },
    ],
    "agentic_ai": [
        {
            
            "title": "Clearly describe the agent's capabilities",
            "tip": "Explain what tools the agent has access to, how it decides which to use, and what it can and cannot do. This is the core value proposition.",
        },
        {
            
            "title": "Show tool integrations",
            "tip": "List the external APIs, tools, or services the agent integrates with. A table of tools with their purposes reads very well.",
        },
        {
            
            "title": "Include example runs",
            "tip": "Add a '## Example' section with a real prompt and the agent's full response/action trace. This is the most powerful thing you can show.",
        },
        {
           
            "title": "Document limitations and safety",
            "tip": "Mention what the agent can't do and any safety guardrails you've built. This shows maturity and real-world awareness.",
        },
        {
            
            "title": "Make it runnable in one command",
            "tip": "Agents are judged by whether they work. Provide a simple demo script with a hardcoded prompt so anyone can verify it works immediately.",
        },
    ],
    "devops": [
        {
            
            "title": "Infrastructure as Code",
            "tip": "If the project provisions infrastructure, use Terraform, Pulumi, or CDK. Show the IaC files and document what they create.",
        },
        {
           
            "title": "Build a full CI/CD pipeline",
            "tip": "Create a GitHub Actions workflow that: lints → tests → builds → deploys. Each stage should be a separate job.",
        },
        {
            
            "title": "Add observability",
            "tip": "Mention logging, metrics, or alerting setup. Even a Prometheus + Grafana setup documented in the README is impressive.",
        },
        {
            
            "title": "Document security practices",
            "tip": "Mention secrets management (Vault, env vars), network policies, or image scanning. Security awareness is highly valued in DevOps.",
        },
        {
           
            "title": "Multi-stage Dockerfiles",
            "tip": "Use multi-stage builds to minimise image size. Document the image size before and after in your README.",
        },
    ],
    "mobile": [
        {
            
            "title": "Add device screenshots",
            "tip": "Include screenshots from iOS and Android simulators in your README. Show multiple screen sizes if possible.",
        },
        {
            
            "title": "Link to the app store or TestFlight",
            "tip": "If the app is published (even on TestFlight/Google Play beta), link to it. A working install is worth 10 screenshots.",
        },
        {
            
            "title": "Mention accessibility support",
            "tip": "Document VoiceOver/TalkBack support. This differentiates you from developers who only think about happy-path users.",
        },
        {
           
            "title": "Show your state management approach",
            "tip": "Mention how you handle state (Redux, Zustand, Provider, etc.) in the README. Architectural decisions matter in mobile.",
        },
        {
            
            "title": "Add at least unit tests",
            "tip": "Use XCTest (iOS) or JUnit/Espresso (Android) for unit tests. Widget tests (Flutter) are also strongly valued.",
        },
    ],
}

GENERAL_TIPS = [
    {
        
        "title": "Write a compelling project description",
        "tip": "Set the GitHub repo's 'About' description (under Settings). It appears in search results and on your profile. Keep it under 20 words and make it punchy.",
    },
    {
        
        "title": "Add GitHub topics",
        "tip": "Add 5-10 relevant topics to your repo (e.g., 'fastapi', 'machine-learning', 'react'). They improve discoverability and help the scoring system categorise your project correctly.",
    },
    {
       
        "title": "Keep the repo active",
        "tip": "Even small commits (fixing a typo, adding a test) show ongoing engagement. Repos with no commits in 6+ months look abandoned to recruiters.",
    },
    {
        
        "title": "Pin this repo on your GitHub profile",
        "tip": "Pin your best projects on your GitHub profile page. You can pin up to 6 repos — make sure this one is there if it's strong.",
    },
    {
        
        "title": "Link your projects from your resume",
        "tip": "Your resume and GitHub should reference each other. If this project is on your resume, the README should match the description you use there.",
    },
]


def generate_signal_reasons(analysis: dict) -> dict:
    reasons = {}
    for signal_key, info in SIGNAL_REASONS.items():
        # Return reasons for ALL signals (both present and missing)
        reasons[signal_key] = info
    return reasons


def generate_improvement_tips(role: str, analysis: dict) -> list[dict]:
    role_specific = ROLE_TIPS.get(role, ROLE_TIPS.get("fullstack", []))

    missing_count = sum(
        1 for k in SIGNAL_REASONS if not analysis.get(k, False)
    )

    tips = list(role_specific)

    if missing_count >= 5:
        tips = tips + GENERAL_TIPS[:3]
    elif missing_count >= 2:
        tips = tips + GENERAL_TIPS[:2]
    else:
        tips = tips + GENERAL_TIPS[:1]

    return tips


def generate_repo_intelligence(analysis: dict, role: str) -> dict:
    return {
        "signal_reasons": generate_signal_reasons(analysis),
        "improvement_tips": generate_improvement_tips(role, analysis),
    }
