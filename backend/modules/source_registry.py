"""
Source Registry — master switchboard for all data sources.

Provides:
  - SEED_SOURCES: canonical list with full capability metadata
  - seed_sources_to_db(): upsert seed data into the `sources` table at startup
  - DB query helpers: get_enabled_sources(), get_source_by_name(), etc.
  - Backward-compat helpers: get_all_sources(), get_sources_by_category()
"""
from __future__ import annotations

from datetime import datetime
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.source import Source


                                                                                  
                                                                  
                                                          

SEED_SOURCES: list[dict] = [
                                                                          
    {"name": "Internshala",      "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://internshala.com",          "parser_type": "internshala",       "fetch_mode": "apify",    "auth_requirement": "none",    "reliability": "high",         "fallback_modes": ["browser", "manual"]},
    {"name": "Indeed",           "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://indeed.com",               "parser_type": "indeed",            "fetch_mode": "apify",    "auth_requirement": "none",    "reliability": "high",         "fallback_modes": ["browser", "manual"]},
    {"name": "LinkedIn",         "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://linkedin.com",             "parser_type": "linkedin",          "fetch_mode": "apify",    "auth_requirement": "session", "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Naukri",           "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://naukri.com",               "parser_type": "naukri",            "fetch_mode": "apify",    "auth_requirement": "none",    "reliability": "high",         "fallback_modes": ["browser", "manual"]},
    {"name": "Foundit",          "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://foundit.in",               "parser_type": "foundit",           "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Freshersworld",    "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://freshersworld.com",        "parser_type": "freshersworld",     "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Cutshort",         "source_type": "internship_board",  "source_group": "internship", "category": "internship",  "base_url": "https://cutshort.io",              "parser_type": "cutshort",          "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},

                                                                          
    {"name": "Wellfound",        "source_type": "startup_board",     "source_group": "startup",    "category": "internship",  "base_url": "https://wellfound.com",            "parser_type": "wellfound",         "fetch_mode": "apify",    "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "WorkAtAStartup",   "source_type": "startup_board",     "source_group": "startup",    "category": "internship",  "base_url": "https://workatastartup.com",       "parser_type": "workatastartup",    "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "TrueUp",           "source_type": "startup_board",     "source_group": "startup",    "category": "internship",  "base_url": "https://www.trueup.io",            "parser_type": "trueup",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},

                                                                          
    {"name": "Arc.dev",          "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://arc.dev",                  "parser_type": "arcdev",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "Himalayas",        "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://himalayas.app",            "parser_type": "himalayas",         "fetch_mode": "api",      "auth_requirement": "none",    "reliability": "high",         "fallback_modes": ["html", "manual"], "enabled": False},
    {"name": "Otta",             "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://app.otta.com",             "parser_type": "otta",              "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "Turing",           "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://www.turing.com",           "parser_type": "turing_jobs",       "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "LandingJobs",      "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://landing.jobs",             "parser_type": "landingjobs",       "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "Pangian",          "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://pangian.com",              "parser_type": "pangian",           "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "PowerToFly",       "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://powertofly.com",           "parser_type": "powertofly",        "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "Andela",           "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://andela.com",               "parser_type": "andela",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    {"name": "Deel",             "source_type": "remote_board",      "source_group": "remote",     "category": "internship",  "base_url": "https://www.deel.com",             "parser_type": "deel",              "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"], "enabled": False},
    
                                                                          
    {"name": "DuckDuckGo ATS",   "source_type": "discovery_engine",  "source_group": "discovery",  "category": "internship",  "base_url": "https://html.duckduckgo.com",      "parser_type": "duckduckgo",        "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": []},

                                                                          
    {"name": "CompanyCareers",   "source_type": "notice_channel",    "source_group": "notice",     "category": "notice",      "base_url": None,                               "parser_type": "company_career",    "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["manual"]},
    {"name": "GovtPortal",       "source_type": "notice_channel",    "source_group": "notice",     "category": "notice",      "base_url": None,                               "parser_type": "govt_portal",       "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["manual"]},
    {"name": "Telegram",         "source_type": "notice_channel",    "source_group": "notice",     "category": "notice",      "base_url": None,                               "parser_type": "telegram",          "fetch_mode": "telegram", "auth_requirement": "api_key", "reliability": "high",         "fallback_modes": ["manual"]},
    {"name": "Gmail",            "source_type": "notice_channel",    "source_group": "notice",     "category": "notice",      "base_url": None,                               "parser_type": "gmail",             "fetch_mode": "imap",     "auth_requirement": "oauth",   "reliability": "high",         "fallback_modes": ["manual"]},

                                                                          
    {"name": "Upwork",           "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.upwork.com",           "parser_type": "upwork",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "high",         "fallback_modes": ["browser", "manual"]},
    {"name": "Fiverr",           "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.fiverr.com",           "parser_type": "fiverr",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Freelancer",       "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.freelancer.com",       "parser_type": "freelancer_com",    "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Guru",             "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.guru.com",             "parser_type": "guru",              "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Toptal",           "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.toptal.com",           "parser_type": "toptal",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "Contra",           "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://contra.com",               "parser_type": "contra",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "PeoplePerHour",    "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.peopleperhour.com",    "parser_type": "peopleperhour",     "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Arc",              "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://arc.dev",                  "parser_type": "arc",               "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "medium",       "fallback_modes": ["browser", "manual"]},
    {"name": "Turing",           "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.turing.com",           "parser_type": "turing",            "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "Lemon.io",         "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://lemon.io",                 "parser_type": "lemonio",           "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "Gun.io",           "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://gun.io",                   "parser_type": "gunio",             "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "99Designs",        "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://99designs.com",            "parser_type": "ninetynine_designs","fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "Dribbble",         "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://dribbble.com/jobs",        "parser_type": "dribbble",          "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
    {"name": "Behance",          "source_type": "freelance_board",   "source_group": "freelance",  "category": "freelance",   "base_url": "https://www.behance.net/joblist",  "parser_type": "behance",           "fetch_mode": "html",     "auth_requirement": "none",    "reliability": "low",          "fallback_modes": ["browser", "manual"]},
]


                                                                                  

async def seed_sources_to_db(db: AsyncSession) -> int:
    """Upsert seed sources into the DB.  Existing rows are updated (not replaced)
    so that user-toggled 'enabled' flags are preserved."""
    upserted = 0
    for seed in SEED_SOURCES:
        result = await db.execute(select(Source).where(Source.name == seed["name"]))
        existing = result.scalar_one_or_none()
        if existing:
                                                                  
            existing.source_type = seed["source_type"]
            existing.source_group = seed["source_group"]
            existing.category = seed["category"]
            existing.base_url = seed.get("base_url")
            existing.parser_type = seed.get("parser_type")
            existing.fetch_mode = seed.get("fetch_mode", "html")
            existing.auth_requirement = seed.get("auth_requirement", "none")
            existing.reliability = seed.get("reliability", "medium")
            existing.fallback_modes = seed.get("fallback_modes")
                                                                                           
        else:
            source = Source(
                name=seed["name"],
                source_type=seed["source_type"],
                source_group=seed["source_group"],
                category=seed["category"],
                base_url=seed.get("base_url"),
                parser_type=seed.get("parser_type"),
                fetch_mode=seed.get("fetch_mode", "html"),
                auth_requirement=seed.get("auth_requirement", "none"),
                reliability=seed.get("reliability", "medium"),
                fallback_modes=seed.get("fallback_modes"),
                enabled=seed.get("enabled", True),
            )
            db.add(source)
        upserted += 1

    await db.commit()
    logger.info(f"[SourceRegistry] Seeded/updated {upserted} sources")
    return upserted


                                                                                  

async def get_enabled_sources(db: AsyncSession, group: str | None = None) -> list[Source]:
    """Get all enabled sources, optionally filtered by source_group."""
    q = select(Source).where(Source.enabled == True)
    if group:
        q = q.where(Source.source_group == group)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_enabled_sources_multi(db: AsyncSession, groups: list[str]) -> list[Source]:
    """Get all enabled sources for multiple source_groups."""
    q = select(Source).where(Source.enabled == True, Source.source_group.in_(groups))
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_source_by_name(db: AsyncSession, name: str) -> Source | None:
    """Lookup a single source by name."""
    result = await db.execute(select(Source).where(Source.name == name))
    return result.scalar_one_or_none()


async def get_source_by_parser(db: AsyncSession, parser_type: str) -> Source | None:
    """Lookup a single source by parser_type."""
    result = await db.execute(select(Source).where(Source.parser_type == parser_type))
    return result.scalar_one_or_none()


async def get_all_sources_db(db: AsyncSession) -> list[Source]:
    """Get every source from DB (enabled and disabled)."""
    result = await db.execute(select(Source))
    return list(result.scalars().all())


async def get_sources_grouped(db: AsyncSession) -> dict[str, list[dict]]:
    """Return sources grouped by source_group for the UI."""
    result = await db.execute(select(Source).order_by(Source.source_group, Source.name))
    sources = result.scalars().all()

    groups: dict[str, list[dict]] = {}
    for s in sources:
        group = s.source_group or "other"
        if group not in groups:
            groups[group] = []
        groups[group].append({
            "id": s.id,
            "name": s.name,
            "source_type": s.source_type,
            "source_group": s.source_group,
            "fetch_mode": s.fetch_mode,
            "auth_requirement": s.auth_requirement,
            "reliability": s.reliability,
            "enabled": s.enabled,
            "base_url": s.base_url,
            "parser_type": s.parser_type,
            "last_fetch_at": s.last_fetch_at.isoformat() if s.last_fetch_at else None,
            "last_fetch_status": s.last_fetch_status,
            "last_fetch_count": s.last_fetch_count,
        })
    return groups


async def update_fetch_status(
    db: AsyncSession,
    source_name: str,
    status: str,
    count: int | None = None,
) -> None:
    """Update a source's last_fetch_* fields after a fetch attempt."""
    values = {
        "last_fetch_at": datetime.utcnow(),
        "last_fetch_status": status,
    }
    if count is not None:
        values["last_fetch_count"] = count

    await db.execute(
        update(Source)
        .where(Source.name == source_name)
        .values(**values)
    )
    await db.commit()


                                                                                  
                                                           
                                                               

def get_all_sources() -> list[dict]:
    """Return all seed sources as dicts (backward compat)."""
    return list(SEED_SOURCES)


def get_sources_by_category(category: str) -> list[dict]:
    """Return seed sources for a given category (backward compat)."""
    return [s for s in SEED_SOURCES if s["category"] == category]


def get_source_categories() -> list[str]:
    """Return distinct categories (backward compat)."""
    return sorted({s["category"] for s in SEED_SOURCES})


def get_source_groups() -> list[str]:
    """Return distinct source groups."""
    return sorted({s["source_group"] for s in SEED_SOURCES})


                                                                                  
                                                                  

SOURCE_KEY_TO_NAME: dict[str, str] = {}
for _src in SEED_SOURCES:
    _key = _src["name"].lower().replace(".", "").replace(" ", "")
    SOURCE_KEY_TO_NAME[_key] = _src["name"]
                                                       
    if _src.get("parser_type"):
        SOURCE_KEY_TO_NAME[_src["parser_type"]] = _src["name"]


def resolve_source_name(key: str) -> str:
    """Resolve a source key (e.g. 'upwork') to its display name ('Upwork')."""
    return SOURCE_KEY_TO_NAME.get(key.lower().replace(".", "").replace(" ", ""), key)
