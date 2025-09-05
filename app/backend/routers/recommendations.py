from utils.timezone import pacific_now
"""Recommendations router."""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, and_

from db.session import get_async_db
from db.models import Recommendation, InterestingTicker, Option
from pydantic import BaseModel
from services.recommender_service import RecommenderService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory job store (in production, use Redis or database)
job_store = {}


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
    
    # Build simplified score breakdown with ROI and Monte-Carlo probability only
    score_breakdown = {
        "Annualized ROI": f"{annualized_roi:.1f}%" if annualized_roi else "N/A",
        "Monte-Carlo Win Probability": f"{recommendation.probability_of_profit_monte_carlo:.1%}" if recommendation.probability_of_profit_monte_carlo else "N/A",
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
        expiry=option.expiry.strftime("%Y-%m-%d") if option else None,
        dte=recommendation.dte,
        contract_price=_sanitize_float_value(contract_price) if contract_price else None,
        total_credit=_sanitize_float_value(total_credit) if total_credit else None,
        collateral=_sanitize_float_value(collateral) if collateral else None,
        industry=ticker.industry if ticker else None,
        sector=ticker.sector if ticker else None,
        next_earnings_date=ticker.next_earnings_date.strftime("%Y-%m-%d") if ticker and ticker.next_earnings_date else None,
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
    """Start async recommendation generation and return job ID."""
    try:
        logger.info("🚀 Manual recommendation generation requested")
        
        # Generate a unique job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Store job in memory
        job_store[job_id] = {
            "id": job_id,
            "status": "pending",
            "message": "Starting recommendation generation...",
            "created_at": pacific_now().isoformat(),
            "total_tickers": 0,
            "processed_tickers": 0,
            "recommendations_generated": 0,
            "current_ticker": None
        }
        
        # Start background generation (simplified - in production you'd use Celery/RQ)
        import asyncio
        asyncio.create_task(generate_recommendations_background(job_id, db))
        
        return {
            "message": "Recommendation generation started",
            "status": "pending",
            "job_id": job_id,
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start recommendation generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start recommendation generation: {str(e)}")

async def generate_recommendations_background(job_id: str, db: AsyncSession):
    """Background task for generating recommendations."""
    try:
        logger.info(f"🔄 Starting background generation for job {job_id}")
        
        # Update job status
        if job_id in job_store:
            job_store[job_id].update({
                "status": "running",
                "message": "Initializing recommendation generation...",
                "total_tickers": 0,
                "processed_tickers": 0,
                "recommendations_generated": 0
            })
        
        # Create a new database session for background task
        from db.session import get_async_db
        async for fresh_db in get_async_db():
            try:
                # Use the real RecommenderService with progress tracking
                from services.recommender_service import RecommenderService
                
                def progress_callback(status_update):
                    """Callback function to update job progress"""
                    if job_id in job_store:
                        job_store[job_id].update(status_update)
                
                recommender_service = RecommenderService()
                recommendations = await recommender_service.generate_recommendations(fresh_db, progress_callback=progress_callback)
                
                # Update job completion
                if job_id in job_store:
                    job_store[job_id].update({
                        "status": "completed",
                        "message": f"Successfully generated {len(recommendations)} recommendations",
                        "recommendations_generated": len(recommendations),
                        "completed_at": pacific_now().isoformat()
                    })
                
                logger.info(f"✅ Background generation completed for job {job_id}: {len(recommendations)} recommendations created")
                break
                
            except Exception as e:
                logger.error(f"❌ Background generation failed for job {job_id}: {e}")
                
                # Update job failure
                if job_id in job_store:
                    job_store[job_id].update({
                        "status": "failed",
                        "message": f"Generation failed: {str(e)}",
                        "failed_at": pacific_now().isoformat()
                    })
                break
        
    except Exception as e:
        logger.error(f"❌ Critical error in background generation for job {job_id}: {e}")
        
        # Update job failure
        if job_id in job_store:
            job_store[job_id].update({
                "status": "failed",
                "message": f"Critical error: {str(e)}",
                "failed_at": pacific_now().isoformat()
            })

@router.get("/generate/status/{job_id}")
async def get_generation_status(job_id: str):
    """Get the status of a generation job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_store[job_id]

@router.get("/generate/jobs")
async def list_generation_jobs():
    """List all generation jobs."""
    return {"jobs": list(job_store.values())}

@router.get("/metadata")
async def get_recommendations_metadata(
    db: AsyncSession = Depends(get_async_db)
):
    """Get recommendations metadata including latest update timestamp."""
    try:
        from sqlalchemy import func, and_
        from utils.timezone import pacific_now
        from datetime import timedelta
        
        # Get today's date in Pacific timezone
        today_start = pacific_now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Get latest recommendation timestamp
        latest_stmt = select(func.max(Recommendation.created_at)).where(
            and_(
                Recommendation.status == "proposed",
                Recommendation.created_at >= today_start,
                Recommendation.created_at < today_end
            )
        )
        latest_result = await db.execute(latest_stmt)
        latest_timestamp = latest_result.scalar()
        
        # Count unique tickers with recommendations for today (to match the deduplication logic)
        count_stmt = select(func.count(func.distinct(Recommendation.symbol))).where(
            and_(
                Recommendation.status == "proposed",
                Recommendation.created_at >= today_start,
                Recommendation.created_at < today_end
            )
        )
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        return {
            "latest_update": latest_timestamp.isoformat() if latest_timestamp else None,
            "total_recommendations_today": total_count or 0,  # Count of unique tickers with recommendations
            "today_start": today_start.isoformat(),
            "current_time": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.warning(f"Error getting recommendations metadata: {e}")
        return {
            "latest_update": None,
            "total_recommendations_today": 0,
            "today_start": pacific_now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
            "current_time": pacific_now().isoformat()
        }

@router.get("/current", response_model=List[RecommendationResponse])
async def get_current_recommendations(
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(default=50, le=100)
):
    """Get current recommendations - latest recommendation per ticker from today."""
    try:
        from sqlalchemy import func, and_, distinct
        from utils.timezone import pacific_now
        from datetime import timedelta
        
        # Get today's date in Pacific timezone
        today_start = pacific_now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        logger.info(f"🔍 Fetching recommendations from {today_start} to {today_end}")
        
        # Get only the latest recommendation per ticker from today
        # Use a window function to rank recommendations by created_at DESC for each symbol
        from sqlalchemy import func, desc, text
        
        # Subquery to get the latest recommendation ID for each symbol
        latest_rec_subquery = select(
            Recommendation.symbol,
            func.max(Recommendation.created_at).label('latest_created_at')
        ).where(
            and_(
                Recommendation.status == "proposed",
                Recommendation.created_at >= today_start,
                Recommendation.created_at < today_end
            )
        ).group_by(Recommendation.symbol).subquery()
        
        # Main query to get the full recommendation data for latest recommendations only
        stmt = select(Recommendation).join(
            latest_rec_subquery,
            and_(
                Recommendation.symbol == latest_rec_subquery.c.symbol,
                Recommendation.created_at == latest_rec_subquery.c.latest_created_at,
                Recommendation.status == "proposed"
            )
        ).order_by(desc(Recommendation.score))
        
        result = await db.execute(stmt)
        recommendations = result.scalars().all()
        
        logger.info(f"📊 Found {len(recommendations)} unique recommendations for today (latest per ticker)")
        
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


@router.post("/generate/ticker/{symbol}")
async def generate_recommendations_for_ticker(
    symbol: str,
    force_refresh: bool = Query(default=False, description="Force refresh of options data"),
    db: AsyncSession = Depends(get_async_db)
):
    """Generate recommendations for a specific ticker."""
    try:
        logger.info(f"🎯 Manual recommendation generation requested for ticker: {symbol}")
        
        # Validate symbol format
        if not symbol or len(symbol.strip()) == 0:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        symbol = symbol.upper().strip()
        
        # Check if ticker exists in universe
        from db.models import InterestingTicker
        ticker_result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol)
        )
        ticker = ticker_result.scalar_one_or_none()
        
        if not ticker:
            raise HTTPException(
                status_code=404, 
                detail=f"Ticker {symbol} not found in universe. Add it to your watchlist first."
            )
        
        # Check if ticker already has active recommendations
        existing_recommendations = await db.execute(
            select(Recommendation).where(
                and_(
                    Recommendation.symbol == symbol,
                    Recommendation.status == "proposed"
                )
            )
        )
        existing = existing_recommendations.scalars().all()
        
        if existing and not force_refresh:
            logger.info(f"📊 Ticker {symbol} already has {len(existing)} active recommendations")
            # Return existing recommendations instead of creating new ones
            response_list = []
            for rec in existing:
                option = await get_option_for_recommendation(db, rec)
                response = await build_recommendation_response(db, rec, option)
                response_list.append(response)
            
            return {
                "message": f"Ticker {symbol} already has active recommendations",
                "status": "existing",
                "recommendations_count": len(existing),
                "recommendations": response_list,
                "timestamp": pacific_now().isoformat()
            }
        
        # If force_refresh is True, clear existing recommendations first
        if force_refresh and existing:
            logger.info(f"🔄 Force refresh requested for {symbol}, clearing {len(existing)} existing recommendations")
            for rec in existing:
                rec.status = "dismissed"
                rec.updated_at = pacific_now()
            await db.commit()
            logger.info(f"✅ Cleared existing recommendations for {symbol}")
        
        # Generate new recommendations
        from services.recommender_service import RecommenderService
        recommender_service = RecommenderService()
        
        logger.info(f"🔄 Starting recommendation generation for {symbol}...")
        recommendations = await recommender_service.generate_recommendations_for_ticker(db, symbol)
        logger.info(f"✅ Recommendation generation completed for {symbol}")
        
        if not recommendations:
            return {
                "message": f"No recommendations generated for {symbol}",
                "status": "no_recommendations",
                "recommendations_count": 0,
                "recommendations": [],
                "timestamp": pacific_now().isoformat()
            }
        
        # Build response for new recommendations
        response_list = []
        for rec in recommendations:
            option = await get_option_for_recommendation(db, rec)
            response = await build_recommendation_response(db, rec, option)
            response_list.append(response)
        
        return {
            "message": f"Successfully generated {len(recommendations)} recommendations for {symbol}",
            "status": "generated",
            "recommendations_count": len(recommendations),
            "recommendations": response_list,
            "timestamp": pacific_now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to generate recommendations for ticker {symbol}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate recommendations for {symbol}: {str(e)}"
        )



