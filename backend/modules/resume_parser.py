import re
import fitz
from pathlib import Path
from loguru import logger


class ResumeParser:
    SKILL_KEYWORDS = {
        "Python", "Java", "C++", "C", "JavaScript", "TypeScript", "SQL", "R",
        "FastAPI", "Django", "Flask", "React", "Node.js", "Next.js",
        "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy",
        "FAISS", "LangChain", "CrewAI", "OpenAI", "Hugging Face",
        "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Git", "GitHub",
        "Linux", "Bash", "REST", "GraphQL", "PostgreSQL", "MongoDB", "Redis",
        "AI", "ML", "NLP", "CV", "LLM", "RAG", "Agentic AI", "Automation",
        "Data Science", "Machine Learning", "Deep Learning", "Computer Vision",
    }

    ROLE_KEYWORDS = [
        "AI intern", "ML intern", "Machine Learning intern", "Data Science intern",
        "Software intern", "Backend intern", "Research intern", "NLP intern",
        "Computer Vision intern", "Full Stack intern",
    ]

    RESEARCH_KEYWORDS = [
        "agentic AI", "multi-agent", "RAG", "retrieval augmented generation",
        "NLP", "computer vision", "large language models", "LLM",
        "reinforcement learning", "federated learning", "diffusion models",
        "knowledge graphs", "automation", "robotics",
    ]

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)

    def _extract_text(self) -> str:
        doc = fitz.open(str(self.pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def _extract_skills(self, text: str) -> list[str]:
        found = []
        text_lower = text.lower()
        for skill in self.SKILL_KEYWORDS:
            if skill.lower() in text_lower:
                found.append(skill)
        return sorted(set(found))

    def _extract_projects(self, text: str) -> list[str]:
        projects = []
        patterns = [
            r"(?i)project[s]?\s*[:\-]\s*([^\n]{5,80})",
            r"(?i)•\s*([A-Z][^\n]{10,80})",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            projects.extend(m.strip() for m in matches[:8])
        return list(dict.fromkeys(projects))

    def _extract_research_areas(self, text: str) -> list[str]:
        found = []
        text_lower = text.lower()
        for area in self.RESEARCH_KEYWORDS:
            if area.lower() in text_lower:
                found.append(area)
        return sorted(set(found))

    def _extract_name(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            candidate = lines[0]
            if len(candidate.split()) <= 4 and candidate.replace(" ", "").isalpha():
                return candidate
        return "Unknown"

    def _extract_email(self, text: str) -> str | None:
        match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        return match.group(0) if match else None

    def _build_summary(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 40]
        return " ".join(lines[:5])

    def parse(self) -> dict:
        logger.info(f"Parsing resume: {self.pdf_path}")
        text = self._extract_text()

        profile = {
            "name": self._extract_name(text),
            "email": self._extract_email(text),
            "skills": self._extract_skills(text),
            "projects": self._extract_projects(text),
            "research_areas": self._extract_research_areas(text),
            "preferred_roles": self.ROLE_KEYWORDS[:3],
            "location_rule": {
                "offline_allowed": ["Delhi NCR", "Gurgaon", "Noida","Delhi","ghaziabad(hybrid)","ghaziabad","delhi(hybrid)","faridabad","agra, uttar pradesh","uttar pradesh","delhi, delhi","okhla, delhi","paschim vihar, delhi","saket, delhi","naraina, delhi, delhi","hauz khas, delhi, delhi","dilshad garden, delhi, delhi","tilak nagar, delhi, delhi","kirti nagar, delhi, delhi","connaught place, delhi, delhi","badarpur, delhi, delhi","india","India"],
                "remote_allowed": True,
                "strict": True,
            },
            "resume_summary": self._build_summary(text),
            "raw_text": text,
        }

        logger.success(f"Parsed: {len(profile['skills'])} skills, {len(profile['projects'])} projects")
        return profile
