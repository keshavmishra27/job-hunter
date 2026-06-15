"""Source management API — list, toggle, query sources by group, and view grouped dashboard."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.source import Source
from backend.modules.source_registry import (
    get_all_sources,
    get_sources_by_category,
    get_source_categories,
    get_source_groups,
    get_sources_grouped,
    get_enabled_sources,
)

router = APIRouter(prefix="/sources", tags=["Sources"])


class ToggleSourceRequest(BaseModel):
    source_name: str
    enabled: bool


class PatchSourceRequest(BaseModel):
    enabled: bool | None = None
    reliability: str | None = None
    fetch_mode: str | None = None


# ─── Grouped View (new primary endpoint) ────────────────────────────────────

@router.get("/groups")
async def list_source_groups(db: AsyncSession = Depends(get_db)):
    """Return all sources grouped by source_group for the UI dashboard."""
    groups = await get_sources_grouped(db)
    return {"groups": groups}


@router.get("/groups/{group}")
async def list_sources_in_group(group: str, db: AsyncSession = Depends(get_db)):
    """Return sources for a specific source_group."""
    sources = await get_enabled_sources(db, group=None)
    # Return all (enabled + disabled) for the given group
    result = await db.execute(
        select(Source).where(Source.source_group == group).order_by(Source.name)
    )
    all_in_group = result.scalars().all()
    if not all_in_group:
        raise HTTPException(404, f"No sources found for group: {group}")
    return [
        {
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
        }
        for s in all_in_group
    ]


@router.get("/groups/{group}/enabled")
async def list_enabled_in_group(group: str, db: AsyncSession = Depends(get_db)):
    """Return only enabled sources for a group."""
    sources = await get_enabled_sources(db, group=group)
    if not sources:
        return []
    return [
        {"name": s.name, "parser_type": s.parser_type, "fetch_mode": s.fetch_mode}
        for s in sources
    ]


# ─── Individual Source CRUD ──────────────────────────────────────────────────

@router.patch("/{source_id}")
async def patch_source(source_id: str, req: PatchSourceRequest, db: AsyncSession = Depends(get_db)):
    """Update source fields (enabled, reliability, fetch_mode)."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(404, f"Source not found: {source_id}")

    if req.enabled is not None:
        source.enabled = req.enabled
    if req.reliability is not None:
        if req.reliability not in ("high", "medium", "low", "experimental"):
            raise HTTPException(400, "Invalid reliability level")
        source.reliability = req.reliability
    if req.fetch_mode is not None:
        if req.fetch_mode not in ("html", "browser", "api", "imap", "telegram", "manual"):
            raise HTTPException(400, "Invalid fetch_mode")
        source.fetch_mode = req.fetch_mode

    await db.commit()
    return {"id": source.id, "name": source.name, "enabled": source.enabled}


# ─── Backward-compatible endpoints ──────────────────────────────────────────

@router.get("/")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all sources from the registry, merged with DB state."""
    seed = get_all_sources()
    # Fetch DB overrides (enabled/disabled state)
    result = await db.execute(select(Source))
    db_sources = {s.name: s for s in result.scalars().all()}

    out = []
    for s in seed:
        db_row = db_sources.get(s["name"])
        out.append({
            "name": s["name"],
            "source_type": s["source_type"],
            "source_group": s.get("source_group", "internship"),
            "category": s["category"],
            "base_url": s["base_url"],
            "parser_type": s["parser_type"],
            "fetch_mode": s.get("fetch_mode", "html"),
            "reliability": s.get("reliability", "medium"),
            "enabled": db_row.enabled if db_row else True,
            "last_fetch_status": db_row.last_fetch_status if db_row else None,
        })
    return out


@router.get("/categories")
async def list_categories():
    """List distinct source categories."""
    return {"categories": get_source_categories(), "groups": get_source_groups()}


@router.get("/{category}")
async def list_sources_by_category(category: str, db: AsyncSession = Depends(get_db)):
    """List sources for a specific lane category."""
    seed = get_sources_by_category(category)
    if not seed:
        raise HTTPException(404, f"No sources found for category: {category}")

    result = await db.execute(select(Source).where(Source.category == category))
    db_sources = {s.name: s for s in result.scalars().all()}

    out = []
    for s in seed:
        db_row = db_sources.get(s["name"])
        out.append({
            "name": s["name"],
            "source_type": s["source_type"],
            "category": s["category"],
            "base_url": s["base_url"],
            "parser_type": s["parser_type"],
            "enabled": db_row.enabled if db_row else True,
        })
    return out


@router.post("/toggle")
async def toggle_source(req: ToggleSourceRequest, db: AsyncSession = Depends(get_db)):
    """Enable or disable a source."""
    result = await db.execute(select(Source).where(Source.name == req.source_name))
    source = result.scalar_one_or_none()

    if source:
        source.enabled = req.enabled
    else:
        # Create a DB row from seed data
        seed = get_all_sources()
        seed_match = next((s for s in seed if s["name"] == req.source_name), None)
        if not seed_match:
            raise HTTPException(404, f"Unknown source: {req.source_name}")
        source = Source(
            name=seed_match["name"],
            source_type=seed_match["source_type"],
            source_group=seed_match.get("source_group", "internship"),
            category=seed_match["category"],
            base_url=seed_match.get("base_url"),
            parser_type=seed_match.get("parser_type"),
            fetch_mode=seed_match.get("fetch_mode", "html"),
            auth_requirement=seed_match.get("auth_requirement", "none"),
            reliability=seed_match.get("reliability", "medium"),
            fallback_modes=seed_match.get("fallback_modes"),
            enabled=req.enabled,
        )
        db.add(source)

    await db.commit()
    return {"name": req.source_name, "enabled": req.enabled}
