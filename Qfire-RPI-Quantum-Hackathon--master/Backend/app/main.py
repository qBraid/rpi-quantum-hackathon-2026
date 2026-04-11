from __future__ import annotations

import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db import Base, SessionLocal, engine
from app.routes.benchmarks import router as benchmarks_router
from app.routes.forecast import router as forecast_router
from app.routes.integrations import router as integrations_router
from app.routes.optimize import router as optimize_router
from app.routes.overview import router as overview_router
from app.routes.reports import router as reports_router
from app.routes.risk import router as risk_router
from app.routes.scenarios import router as scenarios_router
from app.services.bootstrap import seed_sample_data
from app.services.integrations import sync_integration_statuses

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("quantumproj")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Wildfire resilience planning backend with ignition risk classification, spread forecasting, intervention optimization, and qBraid-centered benchmark validation.",
        version="0.2.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Database init
    Base.metadata.create_all(bind=engine)

    # Startup seeding and integration sync
    try:
        with SessionLocal() as db:
            seed_sample_data(db)
            logger.info("Sample data seeding complete")
    except Exception as exc:
        logger.warning("Data seeding failed (non-fatal): %s", exc)

    try:
        with SessionLocal() as db:
            statuses = sync_integration_statuses(db)
            for s in statuses:
                logger.info("Integration %s: mode=%s, available=%s", s.provider, s.mode, s.available)
    except Exception as exc:
        logger.warning("Integration sync failed (non-fatal): %s", exc)

    # Log configuration summary
    logger.info("=" * 60)
    logger.info("QuantumProj API starting")
    logger.info("  Database: %s", settings.sqlite_path)
    logger.info("  IBM token configured: %s", settings.ibm_configured)
    logger.info("  qBraid API key configured: %s", settings.qbraid_configured)
    logger.info("=" * 60)

    # Routes
    prefix = settings.api_prefix
    app.include_router(overview_router, prefix=prefix)
    app.include_router(scenarios_router, prefix=prefix)
    app.include_router(risk_router, prefix=prefix)
    app.include_router(forecast_router, prefix=prefix)
    app.include_router(optimize_router, prefix=prefix)
    app.include_router(benchmarks_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(integrations_router, prefix=prefix)

    return app


app = create_app()
