from utils.timezone import pacific_now
"""Recommendations router."""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from db.session import get_async_db
from db.models import Recommendation, InterestingTicker, Option
from pydantic import BaseModel
from services.recommender_service import RecommenderService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()


class RecommendationResponse(BaseModel):
    """Recommendation response model."""
    id: int
    symbol: str
    strike: Optional[float] = None
    expiry: Optional[str] = None
    score: float
    rationale: dict
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/generate")
async def generate_recommendations(
    db: AsyncSession = Depends(get_async_db)
):
    """Generate new recommendations."""
    try:
        logger.info("🚀 Manual recommendation generation requested")
        
        recommender_service = RecommenderService()
        recommendations = await recommender_service.generate_recommendations(db)
        
        return {
            "message": "Recommendation generation completed",
            "status": "success",
            "recommendations_created": len(recommendations),
            "timestamp": pacific_now().isoformat(),
            "recommendations": [
                {
                    "id": rec.id,
                    "symbol": rec.symbol,
                    "score": rec.score,
                    "status": rec.status,
                    "created_at": rec.created_at.isoformat()
                } for rec in recommendations
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")

@router.get("/current", response_model=List[RecommendationResponse])
async def get_current_recommendations(
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(default=10, le=50)
):
    """Get current recommendations."""
    try:
        # Use async SQLAlchemy 2.0 style queries
        stmt = select(Recommendation).where(
            Recommendation.status == "proposed"
        ).order_by(desc(Recommendation.score)).limit(limit)
        
        result = await db.execute(stmt)
        recommendations = result.scalars().all()
        
        response_list = []
        for rec in recommendations:
            option = None
            if rec.option_id:
                option_stmt = select(Option).where(Option.id == rec.option_id)
                option_result = await db.execute(option_stmt)
                option = option_result.scalar_one_or_none()
            
            response_list.append(RecommendationResponse(
                id=rec.id,
                symbol=rec.symbol,
                strike=option.strike if option else None,
                expiry=option.expiry.isoformat() if option else None,
                score=rec.score,
                rationale=rec.rationale_json or {},
                status=rec.status,
                created_at=rec.created_at.isoformat()
            ))
        
        return response_list
    except Exception as e:
        # Handle case where tables don't exist yet
        logger.warning(f"Database tables not ready: {e}")
        return []


@router.get("/history", response_model=List[RecommendationResponse])
async def get_recommendation_history(
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    symbol: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None)
):
    """Get recommendation history."""
    try:
        stmt = select(Recommendation)
        
        if symbol:
            stmt = stmt.where(Recommendation.symbol == symbol.upper())
        
        if status:
            stmt = stmt.where(Recommendation.status == status)
        
        stmt = stmt.order_by(desc(Recommendation.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(stmt)
        recommendations = result.scalars().all()
        
        response_list = []
        for rec in recommendations:
            option = None
            if rec.option_id:
                option_stmt = select(Option).where(Option.id == rec.option_id)
                option_result = await db.execute(option_stmt)
                option = option_result.scalar_one_or_none()
            
            response_list.append(RecommendationResponse(
                id=rec.id,
                symbol=rec.symbol,
                strike=option.strike if option else None,
                expiry=option.expiry.isoformat() if option else None,
                score=rec.score,
                rationale=rec.rationale_json or {},
                status=rec.status,
                created_at=rec.created_at.isoformat()
            ))
        
        return response_list
    except Exception as e:
        # Handle case where tables don't exist yet
        logger.warning(f"Database tables not ready: {e}")
        return []


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific recommendation by ID."""
    try:
        stmt = select(Recommendation).where(Recommendation.id == recommendation_id)
        result = await db.execute(stmt)
        recommendation = result.scalar_one_or_none()
        
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        option = None
        if recommendation.option_id:
            option_stmt = select(Option).where(Option.id == recommendation.option_id)
            option_result = await db.execute(option_stmt)
            option = option_result.scalar_one_or_none()
        
        return RecommendationResponse(
            id=recommendation.id,
            symbol=recommendation.symbol,
            strike=option.strike if option else None,
            expiry=option.expiry.isoformat() if option else None,
            score=recommendation.score,
            rationale=recommendation.rationale_json or {},
            status=recommendation.status,
            created_at=recommendation.created_at.isoformat()
        )
    except Exception as e:
        # Handle case where tables don't exist yet
        logger.warning(f"Database tables not ready: {e}")
        raise HTTPException(status_code=404, detail="Recommendation not found")


@router.post("/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Dismiss a recommendation."""
    try:
        stmt = select(Recommendation).where(Recommendation.id == recommendation_id)
        result = await db.execute(stmt)
        recommendation = result.scalar_one_or_none()
        
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        if recommendation.status != "proposed":
            raise HTTPException(status_code=400, detail="Can only dismiss proposed recommendations")
        
        recommendation.status = "dismissed"
        await db.commit()
        
        return {"message": "Recommendation dismissed successfully"}
    except Exception as e:
        # Handle case where tables don't exist yet
        logger.warning(f"Database tables not ready: {e}")
        raise HTTPException(status_code=404, detail="Recommendation not found")


@router.get("/symbols/{symbol}", response_model=List[RecommendationResponse])
async def get_recommendations_by_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(default=20, le=50)
):
    """Get recommendations for a specific symbol."""
    try:
        stmt = select(Recommendation).where(
            Recommendation.symbol == symbol.upper()
        ).order_by(desc(Recommendation.created_at)).limit(limit)
        
        result = await db.execute(stmt)
        recommendations = result.scalars().all()
        
        response_list = []
        for rec in recommendations:
            option = None
            if rec.option_id:
                option_stmt = select(Option).where(Option.id == rec.option_id)
                option_result = await db.execute(option_stmt)
                option = option_result.scalar_one_or_none()
            
            response_list.append(RecommendationResponse(
                id=rec.id,
                symbol=rec.symbol,
                strike=option.strike if option else None,
                expiry=option.expiry.isoformat() if option else None,
                score=rec.score,
                rationale=rec.rationale_json or {},
                status=rec.status,
                created_at=rec.created_at.isoformat()
            ))
        
        return response_list
    except Exception as e:
        # Handle case where tables don't exist yet
        logger.warning(f"Database tables not ready: {e}")
        return []


@router.post("/refresh")
async def refresh_recommendations(
    db: AsyncSession = Depends(get_async_db)
):
    """Refresh recommendations by generating new ones."""
    try:
        logger.info("Manual recommendation refresh requested")
        
        # Initialize recommender service and generate recommendations directly
        recommender_service = RecommenderService()
        new_recommendations = await recommender_service.generate_recommendations(db)
        
        return {
            "message": "Recommendations refreshed successfully",
            "status": "success",
            "new_recommendations_count": len(new_recommendations),
            "timestamp": pacific_now().isoformat(),
            "recommendations": [
                {
                    "symbol": rec.symbol,
                    "score": rec.score,
                    "status": rec.status
                } for rec in new_recommendations
            ]
        }
            
    except Exception as e:
        logger.error(f"Failed to refresh recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh recommendations: {str(e)}")
