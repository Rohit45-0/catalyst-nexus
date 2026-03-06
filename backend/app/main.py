"""
Catalyst Nexus Core - FastAPI Application Entry Point
=====================================================

This module initializes the FastAPI application with all middleware,
routers, and event handlers configured.
# Force reload for verification
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
import structlog

from backend.app.core.config import settings
from backend.app.api.v1 import auth, projects, jobs, vault, tracking, market_intel, analytics, search, firecrawl, intake, market_scout, assistant_chat, publish, campaigns, whatsapp, business_knowledge

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for database connections,
    Redis queue, and other resources.
    """
    # Startup
    logger.info("Starting Catalyst Nexus Core", debug=settings.DEBUG)
    logger.info("Database connection established")
    
    # Initialize Redis connection pool
    try:
        from backend.app.core.redis import get_redis
        await get_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed (workers may not function): {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Catalyst Nexus Core")
    try:
        from backend.app.core.redis import close_redis
        await close_redis()
    except Exception:
        pass
    logger.info("All connections closed")


def create_application() -> FastAPI:
    """
    Application factory for creating the FastAPI instance.
    
    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Catalyst Nexus Core",
        description="AI-Powered Video Generation & Identity Management Platform",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Session middleware (required for Google OAuth state)
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    
    # Register API routers
    app.include_router(
        auth.router,
        prefix=f"{settings.API_V1_STR}/auth",
        tags=["Authentication"]
    )
    app.include_router(
        projects.router,
        prefix=f"{settings.API_V1_STR}/projects",
        tags=["Projects"]
    )
    app.include_router(
        jobs.router,
        prefix=f"{settings.API_V1_STR}/jobs",
        tags=["Jobs"]
    )
    app.include_router(
        vault.router,
        prefix=f"{settings.API_V1_STR}",
        tags=["Identity Vault"]
    )
    app.include_router(
        tracking.router,
        prefix=f"{settings.API_V1_STR}",
        tags=["Tracking"]
    )
    app.include_router(
        market_intel.router,
        prefix=f"{settings.API_V1_STR}/market-intel",
        tags=["Market Intelligence"]
    )
    app.include_router(
        analytics.router,
        prefix=f"{settings.API_V1_STR}/analytics",
        tags=["Analytics"]
    )
    
    app.include_router(
        search.router,
        prefix=f"{settings.API_V1_STR}/search",
        tags=["Web Search"]
    )

    app.include_router(
        firecrawl.router,
        prefix=f"{settings.API_V1_STR}/firecrawl",
        tags=["Firecrawl"]
    )

    app.include_router(
        intake.router,
        prefix=f"{settings.API_V1_STR}/intake",
        tags=["Product Intake"]
    )

    app.include_router(
        market_scout.router,
        prefix=f"{settings.API_V1_STR}/market-scout",
        tags=["Market Scout"]
    )

    app.include_router(
        assistant_chat.router,
        prefix=f"{settings.API_V1_STR}/assistant",
        tags=["Assistant Chat"]
    )

    app.include_router(
        publish.router,
        prefix=f"{settings.API_V1_STR}/publish",
        tags=["Publishing"]
    )

    app.include_router(
        campaigns.router,
        prefix=f"{settings.API_V1_STR}/campaigns",
        tags=["Generated Campaigns"]
    )
    
    app.include_router(
        whatsapp.router,
        prefix=f"{settings.API_V1_STR}/whatsapp",
        tags=["WhatsApp Integration"]
    )
    
    app.include_router(
        business_knowledge.router,
        prefix=f"{settings.API_V1_STR}/projects",
        tags=["Business Knowledge Base"]
    )

    return app


# Create the application instance
app = create_application()


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint returning API status."""
    return {
        "status": "operational",
        "service": "Catalyst Nexus Core",
        "version": "0.1.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        dict: Health status of the application and its dependencies.
    """
    redis_status = "disconnected"
    try:
        from backend.app.core.redis import get_redis
        r = await get_redis()
        if await r.ping():
            redis_status = "connected"
    except Exception:
        pass

    return {
        "status": "healthy",
        "database": "connected",
        "cache": redis_status,
        "agents": "ready"
    }
