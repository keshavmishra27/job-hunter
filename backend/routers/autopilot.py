from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db, AsyncSessionLocal
from backend.modules.pipeline import run_pipeline
from backend.modules.autopilot_queue import AutopilotQueue
from loguru import logger

router = APIRouter(prefix="/autopilot", tags=["Autopilot"])

class AutopilotRequest(BaseModel):
    user_id: str
    opportunity_type: str = "internship"
    max_queue: int = 25
    max_per_company: int = 2

                                                                                 
_autopilot_status = {}

async def _run_autopilot_task(user_id: str, opportunity_type: str, max_queue: int, max_per_company: int):
    _autopilot_status[user_id] = {"status": "running", "queue": []}
    try:
        async with AsyncSessionLocal() as db:
                                                             
            result = await run_pipeline(user_id, [opportunity_type], db)
            
                                   
            ranked_items = result.ranked_items
            
                            
            queue = AutopilotQueue.build_queue(ranked_items, max_queue=max_queue, max_per_company=max_per_company)
            
            _autopilot_status[user_id] = {
                "status": "completed",
                "queue": queue,
                "stats": {
                    "fetched": result.fetched,
                    "ranked": len(ranked_items),
                    "queue_size": len(queue)
                }
            }
            logger.info(f"[Autopilot] Completed for {user_id}. Queue size: {len(queue)}")
    except Exception as e:
        logger.error(f"[Autopilot] Failed for {user_id}: {e}")
        _autopilot_status[user_id] = {"status": "failed", "error": str(e), "queue": []}


@router.post("/build-queue")
async def build_queue(req: AutopilotRequest, background_tasks: BackgroundTasks):
    if req.user_id in _autopilot_status and _autopilot_status[req.user_id].get("status") == "running":
        return {"message": "Autopilot already running", "status": "running"}
        
    background_tasks.add_task(
        _run_autopilot_task, 
        req.user_id, 
        req.opportunity_type,
        req.max_queue,
        req.max_per_company
    )
    
    return {"message": "Autopilot started", "status": "running"}


@router.get("/status/{user_id}")
async def get_status(user_id: str):
    status = _autopilot_status.get(user_id, {"status": "idle", "queue": []})
    return {"status": status.get("status"), "stats": status.get("stats")}

@router.get("/queue/{user_id}")
async def get_queue(user_id: str):
    status = _autopilot_status.get(user_id, {})
    if status.get("status") != "completed":
        raise HTTPException(400, "Queue not ready or no run found")
    return {"queue": status.get("queue", []), "stats": status.get("stats")}
