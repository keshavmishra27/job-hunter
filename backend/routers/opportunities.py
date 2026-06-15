"""
Unified Opportunities Router — single API surface for all opportunity types.

Replaces the separate /jobs, /internships, /freelance routers with one
unified interface that speaks "source groups" instead of hardcoded platforms.

Endpoints:
    POST /opportunities/fetch              → run the unified pipeline
    GET  /opportunities/ranked/{user_id}   → get ranked opportunities
    GET  /opportunities/{id}               → get opportunity detail
    POST /opportunities/{id}/status        → update tracking status
    POST /opportunities/{id}/enrich        → trigger async enrichment
    GET  /opportunities/stats/{user_id}    → unified stats
"""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from backend.database import get_db
from backend.models.opportunity import Opportunity, FreelanceDetails, ApplicationTracker
from backend.models.user import UserProfile
from backend.modules.pipeline import run_pipeline, _load_profile, _load_github_repos
from backend.modules.ranker import rank_jobs
from backend.modules.eligibility_filter import _is_remote
from backend.modules.deduper import job_signature

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


# ─── Request Models ──────────────────────────────────────────────────────────

class StatusUpdateRequest(BaseModel):
    status: str  # new | saved | drafted | applied | rejected | expired
    notes: str | None = None


# ─── Fetch ───────────────────────────────────────────────────────────────────

@router.post("/fetch")
async def fetch_opportunities(
    user_id: str,
    source_groups: list[str] = Query(
        default=["internship", "startup", "remote"],
        description="Source groups to fetch from: internship, startup, remote, notice, freelance"
    ),
    force_refresh: bool = False,
    enrich: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the unified discovery pipeline:
    Source Registry → Capability Router → Adapters → Normalize
    → Dedup → Eligibility Filter → Rank → Store → (Enrich)
    """
    result = await run_pipeline(
        user_id=user_id,
        source_groups=source_groups,
        db=db,
        force_refresh=force_refresh,
        enrich=enrich,
        limit=limit,
    )

    return {
        "fetched": result.fetched,
        "normalized": result.normalized,
        "deduplicated": result.deduplicated,
        "eligible": result.eligible,
        "filtered_out": result.filtered_out,
        "ranked": result.ranked,
        "saved": result.saved,
        "top_5": result.top_items,
        "fetch_results": result.fetch_results,
        "errors": result.errors,
    }


# ─── Ranked View ─────────────────────────────────────────────────────────────

@router.get("/ranked/{user_id}")
async def get_ranked_opportunities(
    user_id: str,
    limit: int = 30,
    offset: int = 0,
    source_groups: list[str] = Query(default=[]),
    sources: list[str] = Query(default=[]),
    opportunity_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get ranked opportunities for a user, optionally filtered by
    source group, specific sources, opportunity type, or status.
    """
    # Load profile for re-scoring and location filtering
    profile_dict = await _load_profile(user_id, db)
    github_repos = await _load_github_repos(user_id, db)

    # Build query
    query = select(Opportunity)

    if source_groups:
        query = query.where(Opportunity.source_group.in_(source_groups))
    if sources:
        query = query.where(Opportunity.source.in_(sources))
    if opportunity_type:
        query = query.where(Opportunity.opportunity_type == opportunity_type)
    if status:
        query = query.where(Opportunity.status == status)

    # Fetch more than needed for re-ranking and filtering
    query = query.order_by(Opportunity.score.desc().nullslast()).limit(limit * 3 + offset)
    result = await db.execute(query)
    opportunities = result.scalars().all()

    # Convert to dicts for re-scoring
    opp_dicts = []
    for opp in opportunities:
        opp_dicts.append({
            "id": opp.id,
            "title": opp.title,
            "company": opp.organization,
            "organization": opp.organization,
            "location": opp.location,
            "mode": opp.mode,
            "description": opp.description,
            "apply_link": opp.apply_link,
            "posted_date": opp.posted_at,
            "source": opp.source,
            "source_group": opp.source_group,
            "opportunity_type": opp.opportunity_type,
            "status": opp.status,
            "eligibility_text": opp.eligibility_text,
            "eligibility_status": opp.eligibility_status,
            "deadline": opp.deadline,
            "stipend": opp.stipend,
            "competition_score": opp.competition_score,
            "competition_label": opp.competition_label,
            "competition_reasons": opp.competition_reasons,
            "opportunity_score": opp.opportunity_score,
        })

    # Re-rank with current profile
    ranked = rank_jobs(opp_dicts, profile_dict, github_repos)

    # Apply location filter at read-time
    location_rule = profile_dict.get("location_rule") or {}
    allowed_cities = [loc.lower() for loc in (location_rule.get("offline_allowed") or [])]

    # Check tracking status
    tracking_result = await db.execute(
        select(ApplicationTracker).where(ApplicationTracker.user_id == user_id)
    )
    tracked = {t.opportunity_id: t.status for t in tracking_result.scalars().all()}

    seen_signatures: set[str] = set()
    out: list[dict] = []

    for item in ranked:
        # Dedup by signature in output
        sig = job_signature(item)
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        # Location filter
        if allowed_cities and not _is_remote(item):
            loc = (item.get("location") or "").lower()
            if not any(a in loc or loc in a for a in allowed_cities):
                continue

        tracking_status = tracked.get(item["id"], item.get("status", "new"))

        out.append({
            "id": item["id"],
            "title": item["title"],
            "organization": item.get("organization") or item.get("company"),
            "location": item.get("location"),
            "mode": item.get("mode"),
            "source": item.get("source"),
            "source_group": item.get("source_group"),
            "opportunity_type": item.get("opportunity_type"),
            "apply_link": item.get("apply_link"),
            "score": item.get("score"),
            "score_breakdown": item.get("score_breakdown"),
            "matched_skills": item.get("matched_skills", []),
            "matched_projects": item.get("matched_projects", []),
            "status": tracking_status,
            "eligibility_status": item.get("eligibility_status"),
            "deadline": item["deadline"].isoformat() if isinstance(item.get("deadline"), datetime) else item.get("deadline"),
            "stipend": item.get("stipend"),
            "competition_score": item.get("competition_score"),
            "competition_label": item.get("competition_label"),
            "competition_reasons": item.get("competition_reasons"),
            "opportunity_score": item.get("opportunity_score"),
        })

        if len(out) >= limit:
            break

    return out[offset:]


# ─── Detail View ─────────────────────────────────────────────────────────────

@router.get("/{opportunity_id}")
async def get_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    """Get full detail for an opportunity including freelance details if applicable."""
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    response = {
        "id": opp.id,
        "title": opp.title,
        "organization": opp.organization,
        "location": opp.location,
        "mode": opp.mode,
        "description": opp.description,
        "raw_text": opp.raw_text,
        "apply_link": opp.apply_link,
        "canonical_url": opp.canonical_url,
        "source": opp.source,
        "source_group": opp.source_group,
        "opportunity_type": opp.opportunity_type,
        "score": opp.score,
        "score_breakdown": opp.score_breakdown,
        "matched_skills": opp.matched_skills,
        "matched_projects": opp.matched_projects,
        "status": opp.status,
        "eligibility_text": opp.eligibility_text,
        "eligibility_status": opp.eligibility_status,
        "deadline": opp.deadline,
        "stipend": opp.stipend,
        "posted_at": opp.posted_at,
        "fetched_at": opp.fetched_at,
        "enriched_at": opp.enriched_at,
        "competition_score": opp.competition_score,
        "competition_label": opp.competition_label,
        "competition_reasons": opp.competition_reasons,
        "opportunity_score": opp.opportunity_score,
    }

    # Include freelance details if present
    if opp.opportunity_type == "freelance":
        fd_result = await db.execute(
            select(FreelanceDetails).where(
                FreelanceDetails.opportunity_id == opportunity_id
            )
        )
        fd = fd_result.scalar_one_or_none()
        if fd:
            response["freelance_details"] = {
                "budget_min": fd.budget_min,
                "budget_max": fd.budget_max,
                "budget_type": fd.budget_type,
                "currency": fd.currency,
                "deliverables": fd.deliverables,
                "deadline": fd.deadline,
                "client_type": fd.client_type,
                "client_rating": fd.client_rating,
                "client_reviews_count": fd.client_reviews_count,
                "required_skills": fd.required_skills,
                "project_length": fd.project_length,
                "payment_verified": fd.payment_verified,
                "delivery_time_days": fd.delivery_time_days,
                "remote_only": fd.remote_only,
            }

    return response


# ─── Status Tracking ─────────────────────────────────────────────────────────

@router.post("/{opportunity_id}/status")
async def update_status(
    opportunity_id: str,
    user_id: str,
    req: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update tracking status for an opportunity."""
    VALID = {"new", "saved", "drafted", "applied", "rejected", "expired", "dismissed"}
    if req.status not in VALID:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID}")

    # Check opportunity exists
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    # Upsert tracker
    existing = await db.execute(
        select(ApplicationTracker).where(
            ApplicationTracker.opportunity_id == opportunity_id,
            ApplicationTracker.user_id == user_id,
        )
    )
    tracker = existing.scalar_one_or_none()

    now = datetime.utcnow()
    if tracker:
        tracker.status = req.status
        tracker.notes = req.notes or tracker.notes
        if req.status == "saved":
            tracker.saved_at = now
        elif req.status in ("applied", "drafted"):
            tracker.applied_at = now
        elif req.status == "in_progress":
            tracker.in_progress_at = now
        elif req.status in ("completed", "rejected", "expired"):
            tracker.completed_at = now
    else:
        tracker = ApplicationTracker(
            opportunity_id=opportunity_id,
            user_id=user_id,
            lane_type=opp.opportunity_type or "internship",
            status=req.status,
            notes=req.notes,
            saved_at=now if req.status == "saved" else None,
            applied_at=now if req.status in ("applied", "drafted") else None,
        )
        db.add(tracker)

    # Also update the opportunity's status field
    opp.status = req.status
    await db.commit()

    return {"id": tracker.id, "status": tracker.status, "opportunity_id": opportunity_id}


# ─── Enrichment Trigger ─────────────────────────────────────────────────────

@router.post("/{opportunity_id}/enrich")
async def enrich_single(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger enrichment for a single opportunity."""
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    from backend.modules.enrichment import enrich_opportunity

    opp_dict = {
        "apply_link": opp.apply_link,
        "source": opp.source,
        "description": opp.description,
        "location": opp.location,
        "eligibility_text": opp.eligibility_text,
        "deadline": opp.deadline,
        "stipend": opp.stipend,
    }

    enriched = await enrich_opportunity(opp_dict)

    # Apply enriched fields back to the DB row
    if enriched.get("description") and not opp.description:
        opp.description = enriched["description"]
    if enriched.get("location") and not opp.location:
        opp.location = enriched["location"]
    if enriched.get("eligibility_text") and not opp.eligibility_text:
        opp.eligibility_text = enriched["eligibility_text"]
    if enriched.get("deadline") and not opp.deadline:
        opp.deadline = enriched["deadline"]
    if enriched.get("stipend") and not opp.stipend:
        opp.stipend = enriched["stipend"]
    opp.enriched_at = datetime.utcnow()

    await db.commit()

    return {"id": opp.id, "enriched_at": opp.enriched_at.isoformat(), "status": "enriched"}


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats/{user_id}")
async def get_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get unified opportunity statistics."""
    total = await db.execute(select(func.count(Opportunity.id)))

    by_group = await db.execute(
        select(Opportunity.source_group, func.count(Opportunity.id))
        .group_by(Opportunity.source_group)
    )

    by_type = await db.execute(
        select(Opportunity.opportunity_type, func.count(Opportunity.id))
        .group_by(Opportunity.opportunity_type)
    )

    saved = await db.execute(
        select(func.count(ApplicationTracker.id)).where(
            ApplicationTracker.user_id == user_id,
            ApplicationTracker.status == "saved",
        )
    )
    applied = await db.execute(
        select(func.count(ApplicationTracker.id)).where(
            ApplicationTracker.user_id == user_id,
            ApplicationTracker.status.in_(["applied", "drafted"]),
        )
    )

    return {
        "total": total.scalar() or 0,
        "by_group": {row[0] or "unknown": row[1] for row in by_group.fetchall()},
        "by_type": {row[0] or "unknown": row[1] for row in by_type.fetchall()},
        "saved": saved.scalar() or 0,
        "applied": applied.scalar() or 0,
    }
