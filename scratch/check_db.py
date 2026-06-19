import asyncio
import sys
import os
os.chdir("D:\\kfiles\\job-hunter")
sys.path.append(".")

from backend.database import AsyncSessionLocal
from backend.models.notice import Notice
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Notice.title, Notice.company, Notice.score, Notice.sender_email).where(Notice.source == "Gmail").order_by(Notice.score.desc()).limit(150))
        notices = res.all()
        for title, company, score, sender in notices:
            if "indeed" not in (sender or "").lower():
                print(f"[{score}] {title} | {company} | {sender}")

asyncio.run(run())
