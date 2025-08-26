"""Recommendations router."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.session import get_async_db
from db.models import Recommendation, Ticker, Option
from pydantic import BaseModel
from services.recommender_service import RecommenderService

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


@router.get("/current", response_model=List[RecommendationResponse])
async def get_current_recommendations(
    db: Session = Depends(get_async_db),
    limit: int = Query(default=10, le=50)
):
    """Get current recommendations."""
    recommendations = db.query(Recommendation).filter(
        Recommendation.status == "proposed"
    ).order_by(desc(Recommendation.score)).limit(limit).all()
    
    result = []
    for rec in recommendations:
        option = None
        if rec.option_id:
            option = db.query(Option).filter(Option.id == rec.option_id).first()
        
        result.append(RecommendationResponse(
            id=rec.id,
            symbol=rec.symbol,
            strike=option.strike if option else None,
            expiry=option.expiry.isoformat() if option else None,
            score=rec.score,
            rationale=rec.rationale_json or {},
            status=rec.status,
            created_at=rec.created_at.isoformat()
        ))
    
    return result


@router.get("/history", response_model=List[RecommendationResponse])
async def get_recommendation_history(
    db: Session = Depends(get_async_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    symbol: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None)
):
    """Get recommendation history."""
    query = db.query(Recommendation)
    
    if symbol:
        query = query.filter(Recommendation.symbol == symbol.upper())
    
    if status:
        query = query.filter(Recommendation.status == status)
    
    recommendations = query.order_by(desc(Recommendation.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for rec in recommendations:
        option = None
        if rec.option_id:
            option = db.query(Option).filter(Option.id == rec.option_id).first()
        
        result.append(RecommendationResponse(
            id=rec.id,
            symbol=rec.symbol,
            strike=option.strike if option else None,
            expiry=option.expiry.isoformat() if option else None,
            score=rec.score,
            rationale=rec.rationale_json or {},
            status=rec.status,
            created_at=rec.created_at.isoformat()
        ))
    
    return result


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_async_db)
):
    """Get a specific recommendation by ID."""
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    option = None
    if recommendation.option_id:
        option = db.query(Option).filter(Option.id == recommendation.option_id).first()
    
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


@router.post("/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_async_db)
):
    """Dismiss a recommendation."""
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if recommendation.status != "proposed":
        raise HTTPException(status_code=400, detail="Can only dismiss proposed recommendations")
    
    recommendation.status = "dismissed"
    db.commit()
    
    return {"message": "Recommendation dismissed successfully"}


@router.get("/symbols/{symbol}", response_model=List[RecommendationResponse])
async def get_recommendations_by_symbol(
    symbol: str,
    db: Session = Depends(get_async_db),
    limit: int = Query(default=20, le=50)
):
    """Get recommendations for a specific symbol."""
    recommendations = db.query(Recommendation).filter(
        Recommendation.symbol == symbol.upper()
    ).order_by(desc(Recommendation.created_at)).limit(limit).all()
    
    result = []
    for rec in recommendations:
        option = None
        if rec.option_id:
            option = db.query(Option).filter(Option.id == rec.option_id).first()
        
        result.append(RecommendationResponse(
            id=rec.id,
            symbol=rec.symbol,
            strike=option.strike if option else None,
            expiry=option.expiry.isoformat() if option else None,
            score=rec.score,
            rationale=rec.rationale_json or {},
            status=rec.status,
            created_at=rec.created_at.isoformat()
        ))
    
    return result


@router.post("/refresh")
async def refresh_recommendations(
    db: Session = Depends(get_async_db)
):
    """Refresh recommendations by generating new ones."""
    try:
        # For now, return a success message since database tables need to be set up
        # TODO: Implement full recommendation generation once database is properly configured
        
        return {
            "message": "Recommendations refresh endpoint is working! Database setup required for full functionality.",
            "new_recommendations_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Database tables need to be created for full recommendation generation"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh recommendations: {str(e)}")
