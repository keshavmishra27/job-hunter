import asyncio, sys
sys.path.insert(0, '.')
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.database import engine
from backend.modules.ranker import _detect_duration_months

async def check():
    async with AsyncSession(engine) as db:
        r = await db.execute(text("SELECT title, company, SUBSTR(description, 1, 300) FROM job_posts WHERE company LIKE '%Spearmint%'"))
        for row in r.fetchall():
            months = _detect_duration_months(row[2] or '')
            print(f"{row[0]} | {row[1]} | dur={months}mo | desc={str(row[2])[:120]}...")

asyncio.run(check())
