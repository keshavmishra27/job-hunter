import re
from difflib import SequenceMatcher
from collections import defaultdict
from backend.modules.ranker import get_semantic_model

class AutopilotQueue:
    @staticmethod
    def _normalize_company(name: str) -> str:
        if not name:
            return "unknown"
        # lowercase and remove common suffixes
        name = name.lower()
        name = re.sub(r'\b(inc|ltd|llc|pvt|private|limited|corp|corporation)\b', '', name)
        name = re.sub(r'[^a-z0-9]', ' ', name)
        # remove extra spaces
        name = ' '.join(name.split())
        return name

    @staticmethod
    def _is_same_company(name1: str, name2: str) -> bool:
        n1 = AutopilotQueue._normalize_company(name1)
        n2 = AutopilotQueue._normalize_company(name2)
        if not n1 or not n2:
            return False
        if n1 == n2:
            return True
        if n1 in n2 or n2 in n1:
            return True
        return SequenceMatcher(None, n1, n2).ratio() > 0.85

    @staticmethod
    def _normalize_role(title: str) -> str:
        if not title:
            return ""
        title = title.lower()
        title = re.sub(r'\b(intern|internship|fresher|junior|jr|sr|senior)\b', '', title)
        title = re.sub(r'[^a-z0-9]', ' ', title)
        return ' '.join(title.split())

    @staticmethod
    def _is_same_role(title1: str, title2: str) -> bool:
        t1 = AutopilotQueue._normalize_role(title1)
        t2 = AutopilotQueue._normalize_role(title2)
        
        # If very similar strings
        if SequenceMatcher(None, t1, t2).ratio() > 0.7:
            return True
            
        # Semantic similarity fallback
        if t1 and t2:
            try:
                model = get_semantic_model()
                from sentence_transformers import util
                emb1 = model.encode(t1, convert_to_tensor=True)
                emb2 = model.encode(t2, convert_to_tensor=True)
                score = util.cos_sim(emb1, emb2)[0][0].item()
                if score > 0.8:
                    return True
            except:
                pass
                
        return False

    @staticmethod
    def build_queue(ranked_opportunities: list[dict], max_queue: int = 25, max_per_company: int = 2) -> list[dict]:
        queue = []
        company_groups = defaultdict(list)
        
        for job in ranked_opportunities:
            # find if company exists
            company_name = job.get("company")
            found_company_key = None
            for key in company_groups.keys():
                if AutopilotQueue._is_same_company(key, company_name):
                    found_company_key = key
                    break
            
            if not found_company_key:
                found_company_key = company_name or "Unknown"
                
            jobs_in_company = company_groups[found_company_key]
            
            # check if we already have max per company
            if len(jobs_in_company) >= max_per_company:
                continue
                
            # check if same role already exists in this company
            is_dup_role = False
            for existing_job in jobs_in_company:
                if AutopilotQueue._is_same_role(existing_job.get("title"), job.get("title")):
                    is_dup_role = True
                    break
            
            if is_dup_role:
                continue
                
            company_groups[found_company_key].append(job)
            queue.append(job)
            
            if len(queue) >= max_queue:
                break
                
        return queue
