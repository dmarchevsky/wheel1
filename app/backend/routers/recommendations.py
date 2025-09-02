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
    name: Optional[str] = None  # Company name
    option_symbol: Optional[str] = None
    option_type: str = "put"  # Side put or call
    underlying_ticker: str  # Underlying ticker
    current_price: Optional[float] = None
    strike: Optional[float] = None
    expiry: Optional[str] = None
    dte: Optional[int] = None
    contract_price: Optional[float] = None  # Calculated contract price
    total_credit: Optional[float] = None
    collateral: Optional[float] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    next_earnings_date: Optional[str] = None
    annualized_roi: Optional[float] = None  # Annualized ROI
    pe_ratio: Optional[float] = None
    put_call_ratio: Optional[float] = None
    volume: Optional[int] = None
    score: float
    # Score components in human readable format
    score_breakdown: Optional[dict] = None
    rationale: dict
    status: str
    created_at: str
    
    # Expanded rationale fields (keeping for backward compatibility)
    annualized_yield: Optional[float] = None
    proximity_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    risk_adjustment: Optional[float] = None
    qualitative_score: Optional[float] = None
    spread_pct: Optional[float] = None
    mid_price: Optional[float] = None
    delta: Optional[float] = None
    iv_rank: Optional[float] = None
    open_interest: Optional[int] = None
    probability_of_profit_black_scholes: Optional[float] = None
    probability_of_profit_monte_carlo: Optional[float] = None
    option_side: Optional[str] = None  # 'put' or 'call'
    
    class Config:
        from_attributes = True


def _sanitize_float_value(value: float) -> float:
    """Sanitize a single float value to ensure JSON compliance."""
    if value is None:
        return 0.0
    if value == float('inf'):
        return 999999.0
    if value == float('-inf'):
        return -999999.0
    if value != value:  # NaN check
        return 0.0
    if abs(value) > 1e10:  # Very large numbers
        return 999999.0 if value > 0 else -999999.0
    return float(value)


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
    if recommendation.probability_of_profit_black_scholes is not None:
        rationale["probability_of_profit_black_scholes"] = recommendation.probability_of_profit_black_scholes
    if recommendation.probability_of_profit_monte_carlo is not None:
        rationale["probability_of_profit_monte_carlo"] = recommendation.probability_of_profit_monte_carlo
    if recommendation.option_side is not None:
        rationale["option_side"] = recommendation.option_side
    
    return rationale


async def get_option_for_recommendation(db: AsyncSession, rec: Recommendation) -> Optional[Option]:
    """Get option for recommendation using option_symbol field."""
    option = None
    if rec.option_symbol:
        option_stmt = select(Option).where(Option.symbol == rec.option_symbol)
        option_result = await db.execute(option_stmt)
        option = option_result.scalar_one_or_none()
    return option


async def build_recommendation_response(db: AsyncSession, recommendation: Recommendation, option: Optional[Option] = None, ticker: Optional[InterestingTicker] = None, quote: Optional[object] = None) -> RecommendationResponse:
    """Build recommendation response with expanded fields."""
    from core.scoring import ScoringEngine
    from db.models import TickerQuote
    
    # Get option if not provided
    if not option:
        option = await get_option_for_recommendation(db, recommendation)
    
    # Get ticker information if not provided
    if not ticker:
        ticker_stmt = select(InterestingTicker).where(InterestingTicker.symbol == recommendation.symbol)
        ticker_result = await db.execute(ticker_stmt)
        ticker = ticker_result.scalar_one_or_none()
    
    # Get current quote if not provided
    if not quote:
        quote_stmt = select(TickerQuote).where(TickerQuote.symbol == recommendation.symbol)
        quote_result = await db.execute(quote_stmt)
        quote = quote_result.scalar_one_or_none()
    
    # Initialize ScoringEngine for calculations
    scoring_engine = ScoringEngine(db)
    
    # Calculate financial metrics
    contract_price = None
    total_credit = None
    collateral = None
    annualized_roi = None
    
    if option:
        contract_price = scoring_engine.calculate_contract_price(
            option.bid or 0, option.ask or 0, option.last
        )
        total_credit = scoring_engine.calculate_total_credit(contract_price)
        collateral = scoring_engine.calculate_collateral_required(option.strike)
        annualized_roi = scoring_engine.calculate_annualized_roi(
            total_credit, collateral, recommendation.dte or 0
        )
    
    # Build score breakdown in human readable format
    score_breakdown = {
        "Annualized Yield": f"{recommendation.annualized_yield:.1f}%" if recommendation.annualized_yield else "N/A",
        "Proximity Score": f"{recommendation.proximity_score:.2f}" if recommendation.proximity_score else "N/A",
        "Liquidity Score": f"{recommendation.liquidity_score:.2f}" if recommendation.liquidity_score else "N/A", 
        "Risk Adjustment": f"{recommendation.risk_adjustment:.2f}" if recommendation.risk_adjustment else "N/A",
        "Qualitative Score": f"{recommendation.qualitative_score:.2f}" if recommendation.qualitative_score else "N/A",
        "Probability of Profit (Black-Scholes)": f"{recommendation.probability_of_profit_black_scholes:.1%}" if recommendation.probability_of_profit_black_scholes else "N/A",
        "Probability of Profit (Monte Carlo)": f"{recommendation.probability_of_profit_monte_carlo:.1%}" if recommendation.probability_of_profit_monte_carlo else "N/A",
        "Overall Score": f"{recommendation.score:.2f}"
    }
    
    rationale = build_rationale_dict(recommendation)
    
    return RecommendationResponse(
        id=recommendation.id,
        symbol=recommendation.symbol,
        name=ticker.name if ticker else None,
        option_symbol=option.symbol if option else None,
        option_type=option.option_type if option else "put",
        underlying_ticker=recommendation.symbol,
        current_price=_sanitize_float_value(quote.current_price) if quote and quote.current_price else None,
        strike=_sanitize_float_value(option.strike) if option and option.strike else None,
        expiry=option.expiry.isoformat() if option else None,
        dte=recommendation.dte,
        contract_price=_sanitize_float_value(contract_price) if contract_price else None,
        total_credit=_sanitize_float_value(total_credit) if total_credit else None,
        collateral=_sanitize_float_value(collateral) if collateral else None,
        industry=ticker.industry if ticker else None,
        sector=ticker.sector if ticker else None,
        next_earnings_date=ticker.next_earnings_date.isoformat() if ticker and ticker.next_earnings_date else None,
        annualized_roi=_sanitize_float_value(annualized_roi) if annualized_roi else None,
        pe_ratio=_sanitize_float_value(ticker.pe_ratio) if ticker and ticker.pe_ratio else None,
        put_call_ratio=_sanitize_float_value(quote.put_call_ratio) if quote and quote.put_call_ratio else None,
        volume=recommendation.volume,
        score=_sanitize_float_value(recommendation.score),
        score_breakdown=score_breakdown,
        rationale=rationale,
        status=recommendation.status,
        created_at=recommendation.created_at.isoformat(),
        # Include expanded fields (backward compatibility) - sanitize all float values
        annualized_yield=_sanitize_float_value(recommendation.annualized_yield) if recommendation.annualized_yield else None,
        proximity_score=_sanitize_float_value(recommendation.proximity_score) if recommendation.proximity_score else None,
        liquidity_score=_sanitize_float_value(recommendation.liquidity_score) if recommendation.liquidity_score else None,
        risk_adjustment=_sanitize_float_value(recommendation.risk_adjustment) if recommendation.risk_adjustment else None,
        qualitative_score=_sanitize_float_value(recommendation.qualitative_score) if recommendation.qualitative_score else None,
        spread_pct=_sanitize_float_value(recommendation.spread_pct) if recommendation.spread_pct else None,
        mid_price=_sanitize_float_value(recommendation.mid_price) if recommendation.mid_price else None,
        delta=_sanitize_float_value(recommendation.delta) if recommendation.delta else None,
        iv_rank=_sanitize_float_value(recommendation.iv_rank) if recommendation.iv_rank else None,
        open_interest=recommendation.open_interest,
        probability_of_profit_black_scholes=_sanitize_float_value(recommendation.probability_of_profit_black_scholes) if recommendation.probability_of_profit_black_scholes else None,
        probability_of_profit_monte_carlo=_sanitize_float_value(recommendation.probability_of_profit_monte_carlo) if recommendation.probability_of_profit_monte_carlo else None,
        option_side=recommendation.option_side
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
    limit: int = Query(default=50, le=100)
):
    """Get current recommendations - all recommendations from today."""
    try:
        from sqlalchemy import func, and_, distinct
        from utils.timezone import pacific_now
        from datetime import timedelta
        
        # Get today's date in Pacific timezone
        today_start = pacific_now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        logger.info(f"🔍 Fetching recommendations from {today_start} to {today_end}")
        
        # Get all proposed recommendations from today, ordered by score
        stmt = select(Recommendation).where(
            and_(
                Recommendation.status == "proposed",
                Recommendation.created_at >= today_start,
                Recommendation.created_at < today_end
            )
        ).order_by(desc(Recommendation.score))
        
        result = await db.execute(stmt)
        recommendations = result.scalars().all()
        
        logger.info(f"📊 Found {len(recommendations)} recommendations for today")
        
        # If no recommendations today, check if there are any recommendations at all
        if not recommendations:
            logger.info("🔍 No recommendations found for today, checking all recommendations...")
            all_stmt = select(func.count(Recommendation.id)).where(Recommendation.status == "proposed")
            all_result = await db.execute(all_stmt)
            total_count = all_result.scalar()
            logger.info(f"📊 Total proposed recommendations in database: {total_count}")
            
            # Check most recent recommendation
            recent_stmt = select(Recommendation).where(Recommendation.status == "proposed").order_by(desc(Recommendation.created_at)).limit(1)
            recent_result = await db.execute(recent_stmt)
            most_recent = recent_result.scalar_one_or_none()
            if most_recent:
                logger.info(f"📊 Most recent recommendation: {most_recent.symbol} created at {most_recent.created_at}")
            else:
                logger.warning("❌ No recommendations found in database at all")
        
        # Apply limit only if there are too many results
        if len(recommendations) > limit:
            recommendations = recommendations[:limit]
        
        response_list = []
        for rec in recommendations:
            option = await get_option_for_recommendation(db, rec)
            response = await build_recommendation_response(db, rec, option)
            response_list.append(response)
        
        return response_list
    except Exception as e:
        # Handle case where tables don't exist yet
        logger.warning(f"Database tables not ready: {e}")
        return []


@router.get("/debug")
async def debug_recommendations(
    db: AsyncSession = Depends(get_async_db)
):
    """Debug endpoint to check recommendation system status."""
    try:
        from sqlalchemy import func, and_
        from utils.timezone import pacific_now
        from datetime import timedelta
        from db.models import InterestingTicker, TickerQuote, Option, Position
        
        debug_info = {}
        
        # Check tickers
        ticker_count = await db.execute(select(func.count(InterestingTicker.id)))
        debug_info["total_tickers"] = ticker_count.scalar()
        
        active_ticker_count = await db.execute(
            select(func.count(InterestingTicker.id)).where(InterestingTicker.active == True)
        )
        debug_info["active_tickers"] = active_ticker_count.scalar()
        
        # Check quotes
        quote_count = await db.execute(select(func.count(TickerQuote.id)))
        debug_info["total_quotes"] = quote_count.scalar()
        
        # Check options
        option_count = await db.execute(select(func.count(Option.id)))
        debug_info["total_options"] = option_count.scalar()
        
        # Check recent options (last 24 hours)
        recent_options = await db.execute(
            select(func.count(Option.id)).where(
                Option.updated_at >= pacific_now() - timedelta(hours=24)
            )
        )
        debug_info["recent_options"] = recent_options.scalar()
        
        # Check positions
        position_count = await db.execute(select(func.count(Position.id)))
        debug_info["total_positions"] = position_count.scalar()
        
        # Check recommendations
        rec_count = await db.execute(select(func.count(Recommendation.id)))
        debug_info["total_recommendations"] = rec_count.scalar()
        
        proposed_rec_count = await db.execute(
            select(func.count(Recommendation.id)).where(Recommendation.status == "proposed")
        )
        debug_info["proposed_recommendations"] = proposed_rec_count.scalar()
        
        # Check today's recommendations
        today_start = pacific_now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        today_rec_count = await db.execute(
            select(func.count(Recommendation.id)).where(
                and_(
                    Recommendation.status == "proposed",
                    Recommendation.created_at >= today_start,
                    Recommendation.created_at < today_end
                )
            )
        )
        debug_info["todays_recommendations"] = today_rec_count.scalar()
        
        # Get most recent recommendation
        recent_rec = await db.execute(
            select(Recommendation).order_by(desc(Recommendation.created_at)).limit(1)
        )
        most_recent = recent_rec.scalar_one_or_none()
        if most_recent:
            debug_info["most_recent_recommendation"] = {
                "symbol": most_recent.symbol,
                "created_at": most_recent.created_at.isoformat(),
                "status": most_recent.status,
                "score": most_recent.score
            }
        
        # Check market data service status
        from services.market_data_service import MarketDataService
        market_service = MarketDataService(db)
        summary = await market_service.get_market_summary()
        debug_info["market_summary"] = summary
        
        debug_info["timestamp"] = pacific_now().isoformat()
        debug_info["today_start"] = today_start.isoformat()
        debug_info["today_end"] = today_end.isoformat()
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return {"error": str(e)}


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
            response = await build_recommendation_response(db, rec, option)
            response_list.append(response)
        
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
        
        return await build_recommendation_response(db, recommendation, option)
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
            response = await build_recommendation_response(db, rec, option)
            response_list.append(response)
        
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
