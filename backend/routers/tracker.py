from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models.opportunity import ApplicationTracker, Opportunity

router = APIRouter(prefix="/tracker", tags=["Tracker"])

class TrackerUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    portal_type: Optional[str] = None
    resume_used_id: Optional[str] = None

@router.get("/{user_id}")
async def get_user_tracker(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all tracked applications for a user, joined with opportunity details.
    """
    query = (
        select(ApplicationTracker, Opportunity)
        .join(Opportunity, ApplicationTracker.opportunity_id == Opportunity.id)
        .where(ApplicationTracker.user_id == user_id)
        .order_by(ApplicationTracker.saved_at.desc().nulls_last())
    )
    result = await db.execute(query)
    
    response = []
    for tracker, opp in result.all():
        response.append({
            "id": tracker.id,
            "opportunity_id": opp.id,
            "title": opp.title,
            "company": opp.company,
            "location": opp.location,
            "lane_type": tracker.lane_type,
            "status": tracker.status,
            "portal_type": tracker.portal_type,
            "resume_used_id": tracker.resume_used_id,
            "saved_at": tracker.saved_at,
            "applied_at": tracker.applied_at,
            "notes": tracker.notes,
        })
    return response

@router.patch("/{tracker_id}")
async def update_tracker(tracker_id: str, payload: TrackerUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update the status or notes of a tracked application.
    """
    query = select(ApplicationTracker).where(ApplicationTracker.id == tracker_id)
    result = await db.execute(query)
    tracker = result.scalar_one_or_none()
    
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker entry not found")
        
    if payload.status:
        tracker.status = payload.status
        if payload.status == "applied" and not tracker.applied_at:
            tracker.applied_at = datetime.utcnow()
            
    if payload.notes is not None:
        tracker.notes = payload.notes
        
    if payload.portal_type:
        tracker.portal_type = payload.portal_type
        
    if payload.resume_used_id:
        tracker.resume_used_id = payload.resume_used_id
        
    await db.commit()
    return {"message": "Tracker updated successfully", "status": tracker.status}
