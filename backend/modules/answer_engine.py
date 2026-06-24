class AnswerEngine:
    """
    Template-based Answer Engine that combines context (JD, Resume, Company Info)
    with structured templates to answer standard application questions.
    """
    
    TEMPLATES = {
        "why_us": "Given the company context '{company_info}' and my resume summary '{resume_summary}', explain why I am interested in joining them. Keep it professional, enthusiastic, and under 150 words.",
        "technical_skills": "Given the job description '{job_desc}' and my skills '{skills}', write a concise response explaining my technical fit for the role. Focus on matching skills. Keep it under 100 words.",
        "experience": "Given the job description '{job_desc}', summarize my most relevant experience from my resume '{resume_summary}'. Keep it under 150 words.",
        "general": "Given my resume '{resume_summary}' and the job description '{job_desc}', answer the following application question: '{question}'."
    }
    
    def __init__(self):
                                    
        pass
        
    def classify_question(self, question: str) -> str:
        question = question.lower()
        if "why" in question and ("company" in question or "us" in question or "join" in question):
            return "why_us"
        if "skill" in question or "technical" in question or "stack" in question or "technologies" in question:
            return "technical_skills"
        if "experience" in question or "background" in question or "past" in question:
            return "experience"
        return "general"
        
    def build_prompt(self, question: str, template_type: str, context: dict) -> str:
        template = self.TEMPLATES.get(template_type, self.TEMPLATES["general"])
        
        return template.format(
            question=question,
            company_info=context.get("company_info", "A great company"),
            resume_summary=context.get("resume_summary", ""),
            skills=context.get("skills", ""),
            job_desc=context.get("job_desc", "")
        )
        
    async def generate_answer(self, question: str, context: dict) -> str:
        """
        Generate a contextual application answer using the appropriate template.
        """
        q_type = self.classify_question(question)
        prompt = self.build_prompt(question, q_type, context)
        
                                                        
                                                                    
        return f"[Answer generated via '{q_type}' template using LLM]\nPrompt used: {prompt}"
