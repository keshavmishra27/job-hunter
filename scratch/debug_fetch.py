import asyncio
import os
import sys

                                               
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.modules.fetchers.indeed_fetcher import IndeedFetcher
from backend.database import get_db, AsyncSessionLocal
from sqlalchemy import select
from backend.models import Application, UserProfile

async def main():
    async with AsyncSessionLocal() as db:
                             
        user_id = "demo-user-1"
        applied_history = await db.execute(
            select(Application.job_fingerprint, Application.canonical_url).where(Application.user_id == user_id)
        )
        rows = applied_history.fetchall()
        applied_fingerprints = {r[0] for r in rows if r[0]}
        applied_urls = {r[1] for r in rows if r[1]}
        
        print(f"Loaded {len(applied_fingerprints)} fingerprints and {len(applied_urls)} URLs.")
        
                                   
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        keywords = ["AI intern", "ML intern", "Machine Learning intern"]
        print(f"Keywords: {keywords}")
        
        fetcher = IndeedFetcher()
        results = await fetcher.fetch(
            keywords, 
            location="Remote", 
            applied_fingerprints=applied_fingerprints, 
            applied_urls=applied_urls
        )
        print(f"Found {len(results)} jobs.")
        for r in results:
            print(f"- {r.title} at {r.company} (Link: {r.apply_link})")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
