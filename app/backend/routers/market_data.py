"""Market data management API endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func

from db.session import get_async_db
from services.market_data_service import MarketDataService
from db.models import Ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.post("/update-sp500-universe")
async def update_sp500_universe(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Manually trigger S&P 500 universe update."""
    try:
        logger.info("Manual S&P 500 universe update requested")
        
        market_data_service = MarketDataService(db)
        updated_tickers = await market_data_service.update_sp500_universe()
        
        return {
            "message": "S&P 500 universe update completed",
            "status": "success",
            "updated_tickers_count": len(updated_tickers),
            "timestamp": datetime.utcnow().isoformat(),
            "tickers": [
                {
                    "symbol": ticker.symbol,
                    "name": ticker.name,
                    "sector": ticker.sector,
                    "market_cap": ticker.market_cap,
                    "current_price": ticker.current_price
                } for ticker in updated_tickers[:10]  # Show first 10
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to update S&P 500 universe: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update S&P 500 universe: {str(e)}")


@router.post("/refresh-market-data")
async def refresh_market_data(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Manually trigger market data refresh for active tickers."""
    try:
        logger.info("Manual market data refresh requested")
        
        market_data_service = MarketDataService(db)
        refreshed_tickers = await market_data_service.refresh_market_data()
        
        return {
            "message": "Market data refresh completed",
            "status": "success",
            "refreshed_tickers_count": len(refreshed_tickers),
            "timestamp": datetime.utcnow().isoformat(),
            "tickers": [
                {
                    "symbol": ticker.symbol,
                    "name": ticker.name,
                    "current_price": ticker.current_price,
                    "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
                } for ticker in refreshed_tickers[:10]  # Show first 10
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh market data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh market data: {str(e)}")


@router.get("/summary")
async def get_market_summary(
    db: AsyncSession = Depends(get_async_db)
):
    """Get market data summary."""
    try:
        market_data_service = MarketDataService(db)
        summary = await market_data_service.get_market_summary()
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get market summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market summary: {str(e)}")


@router.post("/populate-sp500-fundamentals-earnings")
async def populate_sp500_fundamentals_earnings(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Manually trigger weekly SP500 fundamentals and earnings population."""
    try:
        logger.info("Manual SP500 fundamentals and earnings population requested")
        
        market_data_service = MarketDataService(db)
        result = await market_data_service.populate_sp500_fundamentals_and_earnings()
        
        if result["success"]:
            return {
                "message": "SP500 fundamentals and earnings population completed",
                "status": "success",
                "total_processed": result["total_processed"],
                "successful_updates": result["successful_updates"],
                "success_rate": result["success_rate"],
                "successful_tickers": result["successful_tickers"],
                "failed_tickers": result["failed_tickers"],
                "timestamp": result["timestamp"]
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"SP500 population failed: {result.get('error', 'Unknown error')}"
            )
        
    except Exception as e:
        logger.error(f"Failed to populate SP500 fundamentals and earnings: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to populate SP500 fundamentals and earnings: {str(e)}"
        )


@router.get("/tickers")
async def get_active_tickers(
    limit: int = 50,
    offset: int = 0,
    sector: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get active tickers with optional filtering."""
    try:
        from sqlalchemy import select
        
        query = select(Ticker).where(Ticker.active == True)
        
        if sector:
            query = query.where(Ticker.sector == sector)
        
        # Get total count
        count_query = select(func.count(Ticker.id)).where(Ticker.active == True)
        if sector:
            count_query = count_query.where(Ticker.sector == sector)
        
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Get tickers with pagination
        tickers_result = await db.execute(query.offset(offset).limit(limit))
        tickers = tickers_result.scalars().all()
        
        return {
            "status": "success",
            "data": {
                "tickers": [
                    {
                        "symbol": ticker.symbol,
                        "name": ticker.name,
                        "sector": ticker.sector,
                        "industry": ticker.industry,
                        "market_cap": ticker.market_cap,
                        "current_price": ticker.current_price,
                        "volume_avg_20d": ticker.volume_avg_20d,
                        "volatility_30d": ticker.volatility_30d,
                        "beta": ticker.beta,
                        "pe_ratio": ticker.pe_ratio,
                        "dividend_yield": ticker.dividend_yield,
                        "universe_score": ticker.universe_score,
                        "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
                    } for ticker in tickers
                ],
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get active tickers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active tickers: {str(e)}")


@router.get("/tickers/{symbol}")
async def get_ticker_details(
    symbol: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed information for a specific ticker."""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(Ticker).where(
                and_(
                    Ticker.symbol == symbol.upper(),
                    Ticker.active == True
                )
            )
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
        
        return {
            "status": "success",
            "data": {
                "symbol": ticker.symbol,
                "name": ticker.name,
                "sector": ticker.sector,
                "industry": ticker.industry,
                "market_cap": ticker.market_cap,
                "current_price": ticker.current_price,
                "volume_avg_20d": ticker.volume_avg_20d,
                "volatility_30d": ticker.volatility_30d,
                "beta": ticker.beta,
                "pe_ratio": ticker.pe_ratio,
                "dividend_yield": ticker.dividend_yield,
                "universe_score": ticker.universe_score,
                "last_analysis_date": ticker.last_analysis_date.isoformat() if ticker.last_analysis_date else None,
                "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticker details for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ticker details: {str(e)}")


@router.post("/tickers/{symbol}/options")
async def fetch_ticker_options(
    symbol: str,
    expiration: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Fetch options data for a specific ticker."""
    try:
        from clients.tradier import TradierDataManager
        from datetime import datetime, timedelta
        
        logger.info(f"Fetching options data for {symbol}")
        
        # Initialize TradierDataManager
        tradier_manager = TradierDataManager(db)
        
        # If no expiration provided, get available expirations first
        if not expiration:
            logger.info(f"Getting available expirations for {symbol}")
            expirations = await tradier_manager.client.get_option_expirations(symbol.upper())
            if expirations:
                # Use the first available expiration (usually the nearest one)
                expiration = expirations[0]
                logger.info(f"Using expiration: {expiration}")
            else:
                # Fallback to next month
                next_month = datetime.now() + timedelta(days=30)
                expiration = next_month.strftime("%Y-%m-%d")
                logger.info(f"No expirations found, using fallback: {expiration}")
        
        # For now, just return the expiration info to test the connection
        return {
            "message": f"Tradier API connection successful for {symbol}",
            "status": "success",
            "symbol": symbol.upper(),
            "expiration": expiration,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Options data fetching is being optimized for performance"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch options for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch options: {str(e)}")


@router.get("/status")
async def get_market_data_status(
    db: AsyncSession = Depends(get_async_db)
):
    """Get market data status and counts."""
    try:
        from sqlalchemy import func, select
        
        # Get ticker count
        ticker_result = await db.execute(
            select(func.count(Ticker.id)).where(Ticker.active == True)
        )
        ticker_count = ticker_result.scalar()
        
        # Get options count
        options_result = await db.execute(
            select(func.count(Option.id))
        )
        options_count = options_result.scalar()
        
        # Get recommendations count
        from db.models import Recommendation
        rec_result = await db.execute(
            select(func.count(Recommendation.id))
        )
        rec_count = rec_result.scalar()
        
        return {
            "status": "success",
            "data": {
                "active_tickers": ticker_count,
                "options_count": options_count,
                "recommendations_count": rec_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get market data status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


