import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

async def main():
    e = create_async_engine("sqlite+aiosqlite:///./data/job_hunter.db")
    async with AsyncSession(e) as s:
        r = await s.execute(text("SELECT user_id, projects, skills FROM user_profiles LIMIT 3"))
        for row in r.fetchall():
            print(f"--- user_id: {row[0]} ---")
            print(f"projects: {row[1]}")
            print(f"skills:   {row[2]}")
            print()

        # Also check a sample job description
        r2 = await s.execute(text("SELECT id, title, company, description FROM job_posts LIMIT 2"))
        for row in r2.fetchall():
            print(f"--- job: {row[1]} @ {row[2]} ---")
            desc = row[3] or ""
            print(f"description length: {len(desc)} chars")
            print(f"description preview: {desc[:200]}")
            print()

asyncio.run(main())
