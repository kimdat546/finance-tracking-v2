"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.config import settings
from app.database import DatabaseManager
from app.parsers.registry import registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Finance Tracker Backend")

    # Initialize database
    try:
        await DatabaseManager.init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Check database health
    health = await DatabaseManager.health_check()
    if health:
        logger.info("Database health check passed")
    else:
        logger.warning("Database health check failed")

    # Initialize parser registry
    if settings.ENABLE_PARSER_AUTO_DISCOVERY:
        try:
            count = registry.auto_discover_parsers()
            logger.info(f"Auto-discovered {count} transaction parsers")
        except Exception as e:
            logger.error(f"Failed to auto-discover parsers: {e}")

    # Log configuration
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Email sync enabled: {settings.ENABLE_EMAIL_SYNC}")
    logger.info(f"Scheduler enabled: {settings.ENABLE_SCHEDULER}")

    yield

    # Shutdown
    logger.info("Shutting down Finance Tracker Backend")
    await DatabaseManager.close()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Finance Tracker API",
        "version": settings.API_VERSION,
        "environment": settings.APP_ENV,
    }


# Logging configuration
logging.basicConfig(
    level=logging.INFO if settings.APP_ENV == "prod" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.APP_ENV == "prod" else "debug",
    )
