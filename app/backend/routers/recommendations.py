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
    
    # Expanded rationale fields
    annualized_yield: Optional[float] = None
    proximity_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    risk_adjustment: Optional[float] = None
    qualitative_score: Optional[float] = None
    dte: Optional[int] = None
    spread_pct: Optional[float] = None
    mid_price: Optional[float] = None
    delta: Optional[float] = None
    iv_rank: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    
    class Config:
        from_attributes = True


def build_rationale_dict(recommendation: Recommendation) -> dict:
    """Build rationale dict with backward compatibility."""
    rationale = recommendation.rationale_json or {}
    
    # Add expanded fields to rationale if they exist
    if recommendation.annualized_yield is not None:
        rationale["annualized_yield"] = recommendation.annualized_yield
    if recommendation.proximity_score is not None:
        rationale["proximity_score"] = recommendation.proximity_score
    if recommendation.liquidity_score is not None:
        rationale["liquidity_score"] = recommendation.liquidity_score
    if recommendation.risk_adjustment is not None:
        rationale["risk_adjustment"] = recommendation.risk_adjustment
    if recommendation.qualitative_score is not None:
        rationale["qualitative_score"] = recommendation.qualitative_score
    if recommendation.dte is not None:
        rationale["dte"] = recommendation.dte
    if recommendation.spread_pct is not None:
        rationale["spread_pct"] = recommendation.spread_pct
    if recommendation.mid_price is not None:
        rationale["mid_price"] = recommendation.mid_price
    if recommendation.delta is not None:
        rationale["delta"] = recommendation.delta
    if recommendation.iv_rank is not None:
        rationale["iv_rank"] = recommendation.iv_rank
    if recommendation.open_interest is not None:
        rationale["open_interest"] = recommendation.open_interest
    if recommendation.volume is not None:
        rationale["volume"] = recommendation.volume
    
    return rationale


async def get_option_for_recommendation(db: AsyncSession, rec: Recommendation) -> Optional[Option]:
    """Get option for recommendation using option_symbol field."""
    option = None
    if rec.option_symbol:
        option_stmt = select(Option).where(Option.symbol == rec.option_symbol)
        option_result = await db.execute(option_stmt)
        option = option_result.scalar_one_or_none()
    return option


def build_recommendation_response(recommendation: Recommendation, option: Optional[Option] = None) -> RecommendationResponse:
    """Build recommendation response with expanded fields."""
    rationale = build_rationale_dict(recommendation)
    
    return RecommendationResponse(
        id=recommendation.id,
        symbol=recommendation.symbol,
        strike=option.strike if option else None,
        expiry=option.expiry.isoformat() if option else None,
        score=recommendation.score,
        rationale=rationale,
        status=recommendation.status,
        created_at=recommendation.created_at.isoformat(),
        # Include expanded fields
        annualized_yield=recommendation.annualized_yield,
        proximity_score=recommendation.proximity_score,
        liquidity_score=recommendation.liquidity_score,
        risk_adjustment=recommendation.risk_adjustment,
        qualitative_score=recommendation.qualitative_score,
        dte=recommendation.dte,
        spread_pct=recommendation.spread_pct,
        mid_price=recommendation.mid_price,
        delta=recommendation.delta,
        iv_rank=recommendation.iv_rank,
        open_interest=recommendation.open_interest,
        volume=recommendation.volume
    )


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
            option = await get_option_for_recommendation(db, rec)
            response_list.append(build_recommendation_response(rec, option))
        
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
            option = await get_option_for_recommendation(db, rec)
            response_list.append(build_recommendation_response(rec, option))
        
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
        
        option = await get_option_for_recommendation(db, recommendation)
        
        return build_recommendation_response(recommendation, option)
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
            option = await get_option_for_recommendation(db, rec)
            response_list.append(build_recommendation_response(rec, option))
        
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
