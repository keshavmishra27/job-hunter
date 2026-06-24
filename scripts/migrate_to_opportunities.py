"""
Migration script — copies existing JobPost and Notice rows into the
unified Opportunity table.

Run once after deploying the new architecture:
    python -m scripts.migrate_to_opportunities

This preserves historical data while transitioning to the new model.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from loguru import logger
from sqlalchemy import select, text

from backend.database import engine, AsyncSessionLocal, init_db


async def migrate():
    """Migrate JobPost and Notice rows into the Opportunity table."""
    await init_db()

    async with AsyncSessionLocal() as db:
                                      
        async with engine.begin() as conn:
                                       
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM job_posts"))
                job_count = result.scalar()
                logger.info(f"Found {job_count} rows in job_posts")
            except Exception:
                job_count = 0
                logger.warning("job_posts table not found or empty")

                                     
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM notices"))
                notice_count = result.scalar()
                logger.info(f"Found {notice_count} rows in notices")
            except Exception:
                notice_count = 0
                logger.warning("notices table not found or empty")

        if job_count == 0 and notice_count == 0:
            logger.info("No data to migrate. Done.")
            return

        migrated = 0

                                           
        if job_count > 0:
            async with engine.begin() as conn:
                rows = await conn.execute(text("""
                    SELECT id, source, title, company, location, mode,
                           description, apply_link, posted_date, content_hash
                    FROM job_posts
                """))
                jobs = rows.fetchall()

            for job in jobs:
                                                             
                existing = await db.execute(text(
                    "SELECT id FROM opportunities WHERE content_hash = :hash"
                ), {"hash": job[9]})
                if existing.scalar_one_or_none():
                    continue

                await db.execute(text("""
                    INSERT OR IGNORE INTO opportunities
                    (id, opportunity_type, source, title, organization,
                     location, mode, description, apply_link,
                     posted_at, content_hash, status, fetched_at)
                    VALUES
                    (:id, 'internship', :source, :title, :org,
                     :loc, :mode, :desc, :link,
                     :posted, :hash, 'new', :fetched)
                """), {
                    "id": job[0],
                    "source": job[1],
                    "title": job[2],
                    "org": job[3],
                    "loc": job[4],
                    "mode": job[5],
                    "desc": job[6],
                    "link": job[7],
                    "posted": job[8],
                    "hash": job[9],
                    "fetched": datetime.utcnow(),
                })
                migrated += 1

            await db.commit()
            logger.info(f"Migrated {migrated} job_posts → opportunities")

                                         
        notice_migrated = 0
        if notice_count > 0:
            async with engine.begin() as conn:
                rows = await conn.execute(text("""
                    SELECT id, source, title, company, location,
                           raw_text, portal_link, source_link,
                           eligibility_text, eligibility_status,
                           deadline, stipend, content_hash, fetched_at
                    FROM notices
                """))
                notices = rows.fetchall()

            for notice in notices:
                                           
                if notice[12]:                
                    existing = await db.execute(text(
                        "SELECT id FROM opportunities WHERE content_hash = :hash"
                    ), {"hash": notice[12]})
                    if existing.scalar_one_or_none():
                        continue

                await db.execute(text("""
                    INSERT OR IGNORE INTO opportunities
                    (id, opportunity_type, source, source_group, title, organization,
                     description, apply_link, raw_text,
                     eligibility_text, eligibility_status,
                     deadline, stipend, content_hash, status, fetched_at)
                    VALUES
                    (:id, 'notice', :source, 'notice', :title, :org,
                     :desc, :link, :raw,
                     :elig_text, :elig_status,
                     :deadline, :stipend, :hash, 'new', :fetched)
                """), {
                    "id": notice[0],
                    "source": notice[1],
                    "title": notice[2],
                    "org": notice[3],
                    "desc": notice[5],
                    "link": notice[6] or notice[7],
                    "raw": notice[5],
                    "elig_text": notice[8],
                    "elig_status": notice[9],
                    "deadline": notice[10],
                    "stipend": notice[11],
                    "hash": notice[12],
                    "fetched": notice[13] or datetime.utcnow(),
                })
                notice_migrated += 1

            await db.commit()
            logger.info(f"Migrated {notice_migrated} notices → opportunities")

        logger.success(f"Migration complete: {migrated + notice_migrated} total rows migrated")


if __name__ == "__main__":
    asyncio.run(migrate())
