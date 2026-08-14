"""FastAPI application entry point.

The application is intentionally minimal at Step 1. It wires the health route
and nothing else. New routers are added in later steps.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.runs import router as runs_router


from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    """Application factory used by Uvicorn and tests."""
    app = FastAPI(
        title="FlowDocs",
        version="0.1.0",
        description="FlowDocs Backend.",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(health_router)
    app.include_router(runs_router, prefix="/api/v1")
    return app


app = create_app()
