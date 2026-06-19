from backend.routers.profile import router as profile_router
from backend.routers.drafts import router as drafts_router
from backend.routers.send import router as send_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.applications import router as applications_router
from backend.routers.github import router as github_router
from backend.routers.internships import router as internships_router
from backend.routers.applied_notices import router as applied_notices_router
from backend.routers.gmail import router as gmail_router
from backend.routers.freelancing import router as freelancing_router
from backend.routers.sources import router as sources_router
from backend.routers.autopilot import router as autopilot_router
from backend.routers.tracker import router as tracker_router

__all__ = [
    "profile_router",
    "drafts_router",
    "send_router",
    "dashboard_router",
    "applications_router",
    "github_router",
    "internships_router",
    "applied_notices_router",
    "gmail_router",
    "freelancing_router",
    "sources_router",
    "autopilot_router",
    "tracker_router",
]
