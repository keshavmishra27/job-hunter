import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pathlib import Path

from backend.database import init_db
from backend.config import get_settings
from backend.routers import (
    profile_router,
    jobs_router,
    drafts_router,
    send_router,
    dashboard_router,
    applications_router,
    github_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.storage_dir + "/resumes").mkdir(parents=True, exist_ok=True)
    logger.info("Initialising database tables...")
    await init_db()
    logger.success("Job Hunter API ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Job Hunter API",
    description="Internship discovery + ranking + outreach assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(drafts_router)
app.include_router(send_router)
app.include_router(dashboard_router)
app.include_router(applications_router)
app.include_router(github_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
