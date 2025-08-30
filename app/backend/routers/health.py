from utils.timezone import pacific_now
"""Health check router."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from db.session import get_async_db
from db.models import Recommendation, InterestingTicker, Option
from services.recommender_service import RecommenderService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": pacific_now().isoformat(),
        "service": "wheel-strategy-api"
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_async_db)):
    """Readiness check with database connectivity and core services."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        # Check core tables exist and are accessible
        try:
            # Check recommendations table
            rec_stmt = select(Recommendation)
            rec_result = await db.execute(rec_stmt)
            rec_count = len(rec_result.scalars().all())
            
            ticker_stmt = select(InterestingTicker)
            ticker_result = await db.execute(ticker_stmt)
            ticker_count = len(ticker_result.scalars().all())
            
            option_stmt = select(Option)
            option_result = await db.execute(option_stmt)
            option_count = len(option_result.scalars().all())
            
            db_status = {
                "status": "connected",
                "tables": {
                    "recommendations": {"count": rec_count, "status": "accessible"},
                    "tickers": {"count": ticker_count, "status": "accessible"},
                    "options": {"count": option_count, "status": "accessible"}
                }
            }
        except Exception as db_error:
            logger.warning(f"Database table check failed: {db_error}")
            db_status = {
                "status": "connected",
                "tables": "inaccessible",
                "warning": "Tables may not be initialized"
            }
        
        return {
            "status": "ready",
            "database": db_status,
            "timestamp": pacific_now().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "database": {
                "status": "disconnected",
                "error": str(e)
            },
            "timestamp": pacific_now().isoformat()
        }


@router.get("/live")
async def liveness_check():
    """Liveness check."""
    return {
        "status": "alive",
        "timestamp": pacific_now().isoformat()
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_async_db)):
    """Detailed health check including all services and components."""
    health_status = {
        "status": "healthy",
        "timestamp": pacific_now().isoformat(),
        "services": {}
    }
    
    # Database health
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["services"]["database"] = {"status": "healthy", "connection": "established"}
    except Exception as e:
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Recommendations service health
    try:
        recommender = RecommenderService()
        # Test basic functionality
        try:
            current_recs_stmt = select(Recommendation).where(Recommendation.status == "proposed")
            current_recs_result = await db.execute(current_recs_stmt)
            current_recs = len(current_recs_result.scalars().all())
            
            health_status["services"]["recommendations"] = {
                "status": "healthy",
                "current_recommendations": current_recs,
                "service": "initialized"
            }
        except Exception as db_error:
            # Database tables might not exist yet
            health_status["services"]["recommendations"] = {
                "status": "initializing",
                "current_recommendations": 0,
                "service": "initialized",
                "warning": "Database tables not ready yet"
            }
    except Exception as e:
        health_status["services"]["recommendations"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Data counts
    try:
        ticker_stmt = select(InterestingTicker)
        ticker_result = await db.execute(ticker_stmt)
        ticker_count = len(ticker_result.scalars().all())
        
        option_stmt = select(Option)
        option_result = await db.execute(option_stmt)
        option_count = len(option_result.scalars().all())
        
        rec_stmt = select(Recommendation)
        rec_result = await db.execute(rec_stmt)
        rec_count = len(rec_result.scalars().all())
        
        proposed_rec_stmt = select(Recommendation).where(Recommendation.status == "proposed")
        proposed_rec_result = await db.execute(proposed_rec_stmt)
        proposed_rec_count = len(proposed_rec_result.scalars().all())
        
        health_status["data_counts"] = {
            "tickers": ticker_count,
            "options": option_count,
            "recommendations": rec_count,
            "proposed_recommendations": proposed_rec_count
        }
    except Exception as e:
        health_status["data_counts"] = {"error": str(e)}
    
    return health_status


@router.get("/recommendations")
async def recommendations_health_check(db: AsyncSession = Depends(get_async_db)):
    """Specific health check for recommendations service."""
    try:
        # Test recommender service initialization
        recommender = RecommenderService()
        
        try:
            # Check recommendations table
            total_recs_stmt = select(Recommendation)
            total_recs_result = await db.execute(total_recs_stmt)
            total_recs = len(total_recs_result.scalars().all())
            
            proposed_recs_stmt = select(Recommendation).where(Recommendation.status == "proposed")
            proposed_recs_result = await db.execute(proposed_recs_stmt)
            proposed_recs = len(proposed_recs_result.scalars().all())
            
            dismissed_recs_stmt = select(Recommendation).where(Recommendation.status == "dismissed")
            dismissed_recs_result = await db.execute(dismissed_recs_stmt)
            dismissed_recs = len(dismissed_recs_result.scalars().all())
            
            return {
                "status": "healthy",
                "recommendations": {
                    "total": total_recs,
                    "proposed": proposed_recs,
                    "dismissed": dismissed_recs
                },
                "service": "operational",
                "timestamp": pacific_now().isoformat()
            }
        except Exception as db_error:
            # Database tables might not exist yet
            return {
                "status": "initializing",
                "recommendations": {
                    "total": 0,
                    "proposed": 0,
                    "dismissed": 0
                },
                "service": "operational",
                "warning": "Database tables not ready yet",
                "timestamp": pacific_now().isoformat()
            }
    except Exception as e:
        logger.error(f"Recommendations health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": pacific_now().isoformat()
        }
