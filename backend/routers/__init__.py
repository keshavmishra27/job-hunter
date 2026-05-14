from backend.routers.profile import router as profile_router
from backend.routers.jobs import router as jobs_router
from backend.routers.drafts import router as drafts_router
from backend.routers.send import router as send_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.applications import router as applications_router

__all__ = [
    "profile_router",
    "jobs_router",
    "drafts_router",
    "send_router",
    "dashboard_router",
    "applications_router",
]
