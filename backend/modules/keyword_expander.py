"""
keyword_expander.py
───────────────────
Expands a candidate's resume skills into ranked OR-query keyword groups
suitable for job-portal searches (Indeed, Internshala, etc.).

Domain-tree rules
─────────────────
If a candidate knows a high-level skill, they implicitly know all sub-skills
beneath it in the domain tree.  We also expand laterally to sibling domains
because job portals use inconsistent terminology.

Usage
─────
    from backend.modules.keyword_expander import expand_keywords

    groups = expand_keywords(
        skills=["GenAI", "LangChain", "FastAPI"],
        preferred_roles=["AI intern", "ML intern"],
    )
    # → [
    #     {"keywords": "generative AI OR LLM intern",         "relevance": "primary"},
    #     {"keywords": "machine learning OR deep learning intern", "relevance": "high"},
    #     ...
    # ]
"""

from __future__ import annotations

import re
from loguru import logger


                                                                               
                      
                                                
                                                 
                                                                               

DOMAIN_EXPANSION_MAP: dict[str, list[str]] = {
                                                                            
    "genai": [
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "Data Science", "Data Analytics", "Python", "TensorFlow", "PyTorch",
        "Transformers", "Neural Networks", "LLM", "AI",
    ],
    "agentic ai": [
        "Machine Learning", "LLM", "NLP", "Automation", "Python",
        "Deep Learning", "AI", "Data Science",
    ],
    "llm": [
        "NLP", "Machine Learning", "Deep Learning", "Transformers",
        "Python", "AI", "Data Science", "Neural Networks",
    ],
    "large language model": [
        "NLP", "Machine Learning", "Deep Learning", "Transformers",
        "Python", "AI", "Data Science",
    ],
    "langchain": [
        "LLM", "NLP", "Machine Learning", "Python", "AI", "Generative AI",
    ],
    "crewai": [
        "LLM", "Agentic AI", "Machine Learning", "Python", "AI", "Automation",
    ],
    "rag": [
        "LLM", "NLP", "Machine Learning", "Python", "AI", "Vector Database",
    ],
    "openai": [
        "LLM", "Generative AI", "NLP", "Machine Learning", "Python", "AI",
    ],
    "hugging face": [
        "NLP", "Transformers", "Machine Learning", "Deep Learning", "Python", "LLM",
    ],
    "transformers": [
        "NLP", "LLM", "Machine Learning", "Deep Learning", "Python", "BERT",
    ],
    "stable diffusion": [
        "Generative AI", "Computer Vision", "Deep Learning", "PyTorch", "Python",
    ],

                                                                            
    "machine learning": [
        "Deep Learning", "Data Science", "Python", "Statistics",
        "Scikit-learn", "Data Analytics", "AI", "TensorFlow", "PyTorch",
    ],
    "ml": [
        "Deep Learning", "Data Science", "Python", "Statistics",
        "Scikit-learn", "Data Analytics", "AI",
    ],
    "deep learning": [
        "Machine Learning", "Neural Networks", "TensorFlow", "PyTorch",
        "Python", "AI", "Computer Vision", "NLP",
    ],
    "tensorflow": [
        "Machine Learning", "Deep Learning", "Python", "AI", "Neural Networks",
    ],
    "pytorch": [
        "Machine Learning", "Deep Learning", "Python", "AI", "Neural Networks",
    ],
    "scikit-learn": [
        "Machine Learning", "Data Science", "Python", "Statistics",
    ],
    "keras": [
        "Deep Learning", "Machine Learning", "TensorFlow", "Python", "AI",
    ],

                                                                            
    "nlp": [
        "Machine Learning", "Deep Learning", "Transformers", "Python",
        "Text Mining", "Data Science", "LLM", "AI",
    ],
    "natural language processing": [
        "Machine Learning", "Deep Learning", "Transformers", "Python",
        "Text Mining", "Data Science", "LLM",
    ],

                                                                            
    "computer vision": [
        "Machine Learning", "Deep Learning", "Image Processing", "OpenCV",
        "Python", "CNN", "AI", "PyTorch", "TensorFlow",
    ],
    "cv": [
        "Computer Vision", "Machine Learning", "Deep Learning",
        "Image Processing", "Python", "AI",
    ],
    "opencv": [
        "Computer Vision", "Image Processing", "Python", "Deep Learning",
    ],

                                                                            
    "data science": [
        "Data Analytics", "SQL", "Python", "Statistics", "Power BI",
        "Tableau", "Excel", "Machine Learning", "Pandas", "NumPy",
    ],
    "data analytics": [
        "Data Science", "SQL", "Python", "Statistics", "Power BI",
        "Tableau", "Excel",
    ],
    "data analysis": [
        "Data Science", "SQL", "Python", "Statistics", "Power BI",
        "Excel", "Tableau",
    ],
    "pandas": [
        "Data Science", "Data Analytics", "Python", "NumPy", "Machine Learning",
    ],
    "numpy": [
        "Data Science", "Python", "Machine Learning", "Pandas",
    ],

                                                                            
    "web development": [
        "Frontend", "Backend", "React", "Node.js", "REST API",
        "Django", "Flask", "FastAPI", "Full Stack",
    ],
    "full stack": [
        "Frontend", "Backend", "React", "Node.js", "REST API",
        "Django", "Flask", "FastAPI", "JavaScript", "TypeScript",
    ],
    "react": [
        "Frontend", "JavaScript", "TypeScript", "Next.js", "Web Development",
    ],
    "fastapi": [
        "Backend", "Python", "REST API", "Web Development", "Django", "Flask",
    ],
    "django": [
        "Backend", "Python", "REST API", "Web Development", "FastAPI", "Flask",
    ],
    "flask": [
        "Backend", "Python", "REST API", "Web Development", "Django", "FastAPI",
    ],
    "node.js": [
        "Backend", "JavaScript", "REST API", "Web Development", "Express",
    ],
    "frontend": [
        "React", "JavaScript", "TypeScript", "HTML", "CSS", "Web Development",
    ],
    "backend": [
        "FastAPI", "Django", "Flask", "Node.js", "REST API", "Python", "Web Development",
    ],

                                                                            
    "aws": [
        "Cloud Computing", "DevOps", "GCP", "Azure", "Docker", "Kubernetes",
    ],
    "gcp": [
        "Cloud Computing", "DevOps", "AWS", "Azure", "Docker",
    ],
    "azure": [
        "Cloud Computing", "DevOps", "AWS", "GCP", "Docker",
    ],
    "docker": [
        "DevOps", "Cloud Computing", "Kubernetes", "CI/CD",
    ],
    "kubernetes": [
        "DevOps", "Docker", "Cloud Computing", "CI/CD",
    ],
    "devops": [
        "Docker", "Kubernetes", "CI/CD", "AWS", "GCP", "Azure",
        "Infrastructure", "Automation",
    ],

                                                                            
    "automation": [
        "RPA", "Selenium", "Python", "Scripting", "DevOps", "AI",
    ],
    "selenium": [
        "Automation", "QA", "Testing", "Python", "Web Scraping",
    ],

                                                                            
    "sql": [
        "Data Science", "Data Analytics", "Database", "PostgreSQL", "MySQL",
    ],
    "postgresql": [
        "SQL", "Database", "Backend", "Data Science",
    ],
    "mongodb": [
        "Database", "Backend", "NoSQL",
    ],

                                                                            
    "python": [
        "Machine Learning", "Data Science", "Automation", "Backend",
        "Scripting", "AI",
    ],
    "java": [
        "Backend", "Android", "Spring Boot", "Software Development",
    ],
    "javascript": [
        "Frontend", "React", "Node.js", "Web Development", "TypeScript",
    ],
    "typescript": [
        "Frontend", "React", "Node.js", "Web Development", "JavaScript",
    ],
    "c++": [
        "Systems Programming", "Competitive Programming", "Embedded", "Robotics",
    ],
}


                                                                               
                         
 
                          
                                                                 
                                                      
                                                             
                                                                               

                                            
                                                                             
_DOMAIN_GROUPS: dict[str, list[dict]] = {
    "ai_genai": [
        {
            "terms": ["generative AI", "LLM intern", "GenAI intern"],
            "relevance": "primary",
        },
        {
            "terms": ["machine learning", "ML intern", "deep learning intern"],
            "relevance": "high",
        },
        {
            "terms": ["NLP intern", "natural language processing intern"],
            "relevance": "related",
        },
        {
            "terms": ["computer vision intern", "CV intern", "image processing intern"],
            "relevance": "related",
        },
        {
            "terms": ["data science intern", "data analytics intern"],
            "relevance": "related",
        },
        {
            "terms": ["AI research intern", "AI engineer intern", "AI developer intern"],
            "relevance": "broad",
        },
    ],
    "ml": [
        {
            "terms": ["machine learning intern", "ML intern"],
            "relevance": "primary",
        },
        {
            "terms": ["deep learning intern", "neural network intern"],
            "relevance": "high",
        },
        {
            "terms": ["data science intern", "data analytics intern"],
            "relevance": "related",
        },
        {
            "terms": ["NLP intern", "computer vision intern"],
            "relevance": "related",
        },
        {
            "terms": ["AI intern", "AI engineer intern"],
            "relevance": "broad",
        },
    ],
    "nlp": [
        {
            "terms": ["NLP intern", "natural language processing intern"],
            "relevance": "primary",
        },
        {
            "terms": ["machine learning intern", "deep learning intern"],
            "relevance": "high",
        },
        {
            "terms": ["LLM intern", "generative AI intern"],
            "relevance": "related",
        },
        {
            "terms": ["data science intern", "text analytics intern"],
            "relevance": "related",
        },
        {
            "terms": ["AI research intern", "AI engineer intern"],
            "relevance": "broad",
        },
    ],
    "computer_vision": [
        {
            "terms": ["computer vision intern", "CV intern", "image processing intern"],
            "relevance": "primary",
        },
        {
            "terms": ["machine learning intern", "deep learning intern"],
            "relevance": "high",
        },
        {
            "terms": ["generative AI intern", "diffusion models intern"],
            "relevance": "related",
        },
        {
            "terms": ["AI intern", "AI engineer intern"],
            "relevance": "broad",
        },
    ],
    "data_science": [
        {
            "terms": ["data science intern", "data scientist intern"],
            "relevance": "primary",
        },
        {
            "terms": ["data analytics intern", "data analyst intern"],
            "relevance": "high",
        },
        {
            "terms": ["machine learning intern", "ML intern"],
            "relevance": "related",
        },
        {
            "terms": ["business intelligence intern", "BI intern", "Power BI intern"],
            "relevance": "related",
        },
        {
            "terms": ["Python developer intern", "SQL intern"],
            "relevance": "broad",
        },
    ],
    "web_fullstack": [
        {
            "terms": ["full stack intern", "fullstack developer intern"],
            "relevance": "primary",
        },
        {
            "terms": ["frontend intern", "React intern", "UI developer intern"],
            "relevance": "high",
        },
        {
            "terms": ["backend intern", "Python backend intern", "Node.js intern"],
            "relevance": "high",
        },
        {
            "terms": ["web development intern", "software developer intern"],
            "relevance": "related",
        },
        {
            "terms": ["software engineer intern", "SWE intern"],
            "relevance": "broad",
        },
    ],
    "backend": [
        {
            "terms": ["backend intern", "backend developer intern"],
            "relevance": "primary",
        },
        {
            "terms": ["Python developer intern", "Django intern", "FastAPI intern"],
            "relevance": "high",
        },
        {
            "terms": ["full stack intern", "web development intern"],
            "relevance": "related",
        },
        {
            "terms": ["software developer intern", "software engineer intern"],
            "relevance": "broad",
        },
    ],
    "frontend": [
        {
            "terms": ["frontend intern", "UI developer intern", "React intern"],
            "relevance": "primary",
        },
        {
            "terms": ["JavaScript intern", "TypeScript intern", "Next.js intern"],
            "relevance": "high",
        },
        {
            "terms": ["full stack intern", "web development intern"],
            "relevance": "related",
        },
        {
            "terms": ["software developer intern", "software engineer intern"],
            "relevance": "broad",
        },
    ],
    "devops_cloud": [
        {
            "terms": ["DevOps intern", "cloud intern", "cloud engineering intern"],
            "relevance": "primary",
        },
        {
            "terms": ["AWS intern", "GCP intern", "Azure intern"],
            "relevance": "high",
        },
        {
            "terms": ["infrastructure intern", "SRE intern", "platform engineering intern"],
            "relevance": "related",
        },
        {
            "terms": ["software engineer intern", "backend intern"],
            "relevance": "broad",
        },
    ],
    "automation": [
        {
            "terms": ["automation intern", "RPA intern"],
            "relevance": "primary",
        },
        {
            "terms": ["QA intern", "testing intern", "Selenium intern"],
            "relevance": "high",
        },
        {
            "terms": ["Python developer intern", "scripting intern"],
            "relevance": "related",
        },
        {
            "terms": ["software developer intern", "software engineer intern"],
            "relevance": "broad",
        },
    ],
    "data_engineering": [
        {
            "terms": ["data engineering intern", "data engineer intern"],
            "relevance": "primary",
        },
        {
            "terms": ["ETL intern", "SQL intern", "database intern"],
            "relevance": "high",
        },
        {
            "terms": ["data science intern", "data analytics intern"],
            "relevance": "related",
        },
        {
            "terms": ["backend intern", "Python developer intern"],
            "relevance": "broad",
        },
    ],
}

                                                                               
                         
                                                     
                                                                               

_SKILL_DOMAIN_MAP: list[tuple[str, str]] = [
                
    ("genai", "ai_genai"),
    ("generative", "ai_genai"),
    ("agentic", "ai_genai"),
    ("llm", "ai_genai"),
    ("large language", "ai_genai"),
    ("langchain", "ai_genai"),
    ("crewai", "ai_genai"),
    ("autogen", "ai_genai"),
    ("openai", "ai_genai"),
    ("hugging face", "ai_genai"),
    ("huggingface", "ai_genai"),
    ("transformer", "ai_genai"),
    ("rag", "ai_genai"),
    ("stable diffusion", "ai_genai"),
    ("faiss", "ai_genai"),
    ("chromadb", "ai_genai"),
    ("pinecone", "ai_genai"),
        
    ("machine learning", "ml"),
    ("tensorflow", "ml"),
    ("pytorch", "ml"),
    ("keras", "ml"),
    ("scikit", "ml"),
    ("sklearn", "ml"),
    ("xgboost", "ml"),
    ("lightgbm", "ml"),
                                                       
    ("deep learning", "ml"),
    ("neural network", "ml"),
         
    ("nlp", "nlp"),
    ("natural language", "nlp"),
    ("spacy", "nlp"),
    ("nltk", "nlp"),
    ("bert", "nlp"),
                     
    ("computer vision", "computer_vision"),
    ("opencv", "computer_vision"),
    ("image processing", "computer_vision"),
    ("yolo", "computer_vision"),
    ("cnn", "computer_vision"),
                  
    ("data science", "data_science"),
    ("data analytics", "data_science"),
    ("data analysis", "data_science"),
    ("pandas", "data_science"),
    ("numpy", "data_science"),
    ("matplotlib", "data_science"),
    ("tableau", "data_science"),
    ("power bi", "data_science"),
                      
    ("full stack", "web_fullstack"),
    ("fullstack", "web_fullstack"),
    ("web development", "web_fullstack"),
    ("react", "frontend"),
    ("vue", "frontend"),
    ("angular", "frontend"),
    ("next.js", "frontend"),
    ("nextjs", "frontend"),
    ("html", "frontend"),
    ("css", "frontend"),
    ("frontend", "frontend"),
    ("fastapi", "backend"),
    ("django", "backend"),
    ("flask", "backend"),
    ("spring", "backend"),
    ("backend", "backend"),
    ("node.js", "backend"),
    ("nodejs", "backend"),
    ("express", "backend"),
                    
    ("docker", "devops_cloud"),
    ("kubernetes", "devops_cloud"),
    ("devops", "devops_cloud"),
    ("aws", "devops_cloud"),
    ("gcp", "devops_cloud"),
    ("azure", "devops_cloud"),
    ("terraform", "devops_cloud"),
    ("ci/cd", "devops_cloud"),
                
    ("selenium", "automation"),
    ("playwright", "automation"),
    ("automation", "automation"),
    ("rpa", "automation"),
                      
    ("spark", "data_engineering"),
    ("kafka", "data_engineering"),
    ("airflow", "data_engineering"),
    ("etl", "data_engineering"),
    ("data engineer", "data_engineering"),
    ("sql", "data_engineering"),
    ("postgresql", "data_engineering"),
]

                                                                              
                                                       
_AI_SIBLING_DOMAINS: set[str] = {"ai_genai", "ml", "nlp", "computer_vision"}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _detect_domains(skills: list[str], preferred_roles: list[str]) -> set[str]:
    """Map skills and preferred roles to domain keys."""
    detected: set[str] = set()
    all_text = " ".join(_normalise(s) for s in skills + preferred_roles)

    for fragment, domain in _SKILL_DOMAIN_MAP:
        if fragment in all_text:
            detected.add(domain)

                                     
    role_text = " ".join(_normalise(r) for r in preferred_roles)
    if "ai" in role_text or "ml" in role_text:
        detected.add("ai_genai")
    if "data" in role_text:
        detected.add("data_science")
    if "web" in role_text or "software" in role_text or "developer" in role_text:
        if not detected & {"web_fullstack", "frontend", "backend"}:
            detected.add("web_fullstack")

    return detected


def _merge_ai_siblings(domains: set[str]) -> set[str]:
    """
    If ANY AI-related domain is detected, automatically include ALL
    AI sibling domains so the candidate sees the full AI landscape.
    """
    if domains & _AI_SIBLING_DOMAINS:
        domains = domains | _AI_SIBLING_DOMAINS
    return domains


def _build_groups(domains: set[str]) -> list[dict]:
    """
    Collect and merge keyword groups from all detected domains.
    Deduplicate by relevance tier, prefer higher-priority relevance.
    """
                        
    relevance_rank = {"primary": 0, "high": 1, "related": 2, "broad": 3}

                                                                             
    ordered_domains: list[str] = []
    priority_order = ["ai_genai", "ml", "nlp", "computer_vision",
                      "data_science", "web_fullstack", "frontend", "backend",
                      "devops_cloud", "automation", "data_engineering"]
    for d in priority_order:
        if d in domains:
            ordered_domains.append(d)
                                                 
    for d in domains:
        if d not in ordered_domains:
            ordered_domains.append(d)

    seen_keywords: dict[str, str] = {}                                     
    all_groups: list[dict] = []

    for domain in ordered_domains:
        for group in _DOMAIN_GROUPS.get(domain, []):
                                       
            kw_str = " OR ".join(group["terms"])
            key = _normalise(kw_str)
            new_rel = group["relevance"]

            if key in seen_keywords:
                                                             
                existing_rel = seen_keywords[key]
                if relevance_rank[new_rel] < relevance_rank[existing_rel]:
                    seen_keywords[key] = new_rel
                                                             
                    for g in all_groups:
                        if _normalise(g["keywords"]) == key:
                            g["relevance"] = new_rel
                            break
            else:
                seen_keywords[key] = new_rel
                all_groups.append({"keywords": kw_str, "relevance": new_rel})

    return all_groups


def expand_keywords(
    skills: list[str],
    preferred_roles: list[str] | None = None,
    max_groups: int = 6,
) -> list[dict]:
    """
    Expand resume skills into ranked OR-query keyword groups for job portals.

    Parameters
    ----------
    skills:          List of skills from the parsed resume.
    preferred_roles: List of preferred job roles (optional).
    max_groups:      Maximum number of keyword groups to return (default 6).

    Returns
    -------
    List of dicts: [{"keywords": "...", "relevance": "primary|high|related|broad"}, ...]
    Ordered by relevance (primary first).
    """
    preferred_roles = preferred_roles or []

    if not skills and not preferred_roles:
        logger.warning("[KeywordExpander] No skills or roles provided; returning empty list.")
        return []

                                        
    domains = _detect_domains(skills, preferred_roles)

                                                     
    domains = _merge_ai_siblings(domains)

    logger.info(f"[KeywordExpander] Detected domains: {domains}")

                                  
    groups = _build_groups(domains)

                               
    result = groups[:max_groups]

    logger.info(
        f"[KeywordExpander] Generated {len(result)} keyword groups from "
        f"{len(skills)} skills, {len(preferred_roles)} roles."
    )
    return result


def flatten_to_query_list(groups: list[dict]) -> list[str]:
    """
    Flatten keyword groups into a plain list of individual query terms.
    Useful for passing to fetchers that take `keywords: list[str]`.

    Example:
        "generative AI OR LLM intern" → ["generative AI", "LLM intern"]
    """
    terms: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for term in group["keywords"].split(" OR "):
            t = term.strip()
            if t and t not in seen:
                seen.add(t)
                terms.append(t)
    return terms
