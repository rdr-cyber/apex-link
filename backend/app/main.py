"""APEX LINK — Main FastAPI application."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown events."""
    # Startup diagnostics — safe for production logs (no secrets)
    db_configured = bool(settings.DATABASE_URL and not settings.DATABASE_URL.startswith("postgresql://apex_user"))
    logger.info(
        "APEX LINK %s starting | env=%s | db=%s | email=%s",
        settings.APP_VERSION,
        "production" if not settings.DEBUG else "development",
        "configured" if db_configured else "NOT CONFIGURED (using defaults)",
        settings.EMAIL_PROVIDER,
    )
    yield
    logger.info("APEX LINK shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Explainable Criminal Network & Investigation Intelligence Platform",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Lightweight health check — no sensitive data, no auth required."""
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/api/ready", tags=["Health"])
async def readiness_check():
    """Readiness check — verifies database connectivity."""
    try:
        from app.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception:
        logger.warning("Readiness check failed — database unavailable")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler — never expose stack traces in production."""
    if settings.DEBUG:
        logger.exception("Unhandled exception: %s", exc)
    else:
        logger.error("Unhandled exception (trace suppressed)")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )
