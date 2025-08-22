"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.session import get_async_db

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_async_db)):
    """Readiness check with database connectivity."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/live")
async def liveness_check():
    """Liveness check."""
    return {"status": "alive"}
