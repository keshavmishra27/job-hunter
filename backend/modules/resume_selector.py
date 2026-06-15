from backend.models.user import Resume
from backend.modules.ranker import get_semantic_model

class ResumeSelector:
    ROLE_TAGS = {
        "backend": ["backend", "server", "api", "django", "fastapi", "node"],
        "ai_engineer": ["ai", "ml", "machine learning", "deep learning", "llm", "nlp", "genai"],
        "mlops": ["mlops", "ml engineer", "model deployment", "kubeflow"],
        "data_science": ["data science", "data analyst", "analytics", "tableau", "power bi"],
        "frontend": ["frontend", "react", "vue", "angular", "ui/ux"],
        "fullstack": ["fullstack", "full stack", "full-stack"],
        "devops": ["devops", "cloud", "sre", "infrastructure"],
        "research": ["research", "phd", "publication", "paper"],
    }

    @staticmethod
    def classify_role(job_description: str) -> str | None:
        if not job_description:
            return None
        job_description = job_description.lower()
        
        best_tag = None
        best_count = 0
        
        for tag, keywords in ResumeSelector.ROLE_TAGS.items():
            count = sum(job_description.count(kw) for kw in keywords)
            if count > best_count:
                best_count = count
                best_tag = tag
                
        return best_tag

    @staticmethod
    def select(job_description: str, resumes: list[Resume]) -> Resume | None:
        if not resumes:
            return None
            
        # 1. Classify the JD into a role_tag
        classified_tag = ResumeSelector.classify_role(job_description)
        
        # 2. Find the resume with matching role_tag
        if classified_tag:
            for r in resumes:
                if r.role_tag == classified_tag:
                    return r
                    
        # 3. Fall back to highest cosine similarity
        best_resume = None
        best_score = -1.0
        
        try:
            model = get_semantic_model()
            from sentence_transformers import util
            desc_emb = model.encode(job_description[:1000], convert_to_tensor=True)
            
            for r in resumes:
                summary = r.parsed_summary or ""
                if not summary:
                    continue
                res_emb = model.encode(summary[:1000], convert_to_tensor=True)
                score = util.cos_sim(desc_emb, res_emb)[0][0].item()
                if score > best_score:
                    best_score = score
                    best_resume = r
        except Exception:
            pass
            
        return best_resume or resumes[0]
