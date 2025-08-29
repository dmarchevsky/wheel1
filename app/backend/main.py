"""Main FastAPI application for the Wheel Strategy API."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn

from config import settings, validate_required_settings
from db.session import get_async_db, create_tables
from routers import recommendations, positions, trades, export, health, market_data, settings as settings_router
from services.telegram_service import TelegramService


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Wheel Strategy API...")
    
    try:
        # Validate required settings
        validate_required_settings()
        logger.info("Configuration validated successfully")
        
        # Create database tables if they don't exist
        create_tables()
        logger.info("Database tables ready")
        
        # Initialize Telegram service
        telegram_service = TelegramService()
        await telegram_service.initialize()
        logger.info("Telegram service initialized")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Wheel Strategy API...")


# Create FastAPI app
app = FastAPI(
    title="Wheel Strategy API",
    description="API for automated Wheel Strategy options trading",
    version="1.0.0",
    lifespan=lifespan
)

# CORS is handled by Nginx reverse proxy
# No CORS middleware needed here


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(recommendations.router, prefix="/v1/recommendations", tags=["recommendations"])
app.include_router(positions.router, prefix="/v1/positions", tags=["positions"])
app.include_router(trades.router, prefix="/v1/trades", tags=["trades"])
app.include_router(export.router, prefix="/v1/export", tags=["export"])
app.include_router(market_data.router, prefix="/v1", tags=["market-data"])
app.include_router(settings_router.router, prefix="/v1", tags=["settings"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Wheel Strategy API",
        "version": "1.0.0",
        "status": "running"
    }


# FastAPI automatically serves Swagger UI at /docs and ReDoc at /redoc
# OpenAPI schema is available at /openapi.json


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Always enable reload in development
        log_level=settings.log_level.lower()
    )
