from utils.timezone import pacific_now
"""Market data management API endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func

from db.session import get_async_db
from services.market_data_service import MarketDataService
from services.universe_service import UniverseService
from db.models import InterestingTicker, TickerQuote
from datetime import datetime, timezone

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
            "timestamp": pacific_now().isoformat(),
            "tickers": [
                {
                    "symbol": ticker.symbol,
                    "name": ticker.name,
                    "sector": ticker.sector,
                    "market_cap": ticker.market_cap,
                    "source": ticker.source,
                    "active": ticker.active
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
            "timestamp": pacific_now().isoformat(),
            "tickers": [
                {
                    "symbol": ticker.symbol,
                    "name": ticker.name,
                    "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
                } for ticker in refreshed_tickers[:10]  # Show first 10
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh market data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh market data: {str(e)}")


# =============================================================================
# NEW DATA FETCH LOGIC ENDPOINTS
# =============================================================================

@router.post("/update-all-fundamentals")
async def update_all_fundamentals(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Update fundamentals for all interesting_tickers using SEC API and API Ninjas."""
    try:
        logger.info("Manual fundamentals update requested")
        
        market_data_service = MarketDataService(db)
        result = await market_data_service.update_all_fundamentals()
        
        return {
            "message": "Fundamentals update completed",
            "status": "success" if result["success"] else "failed",
            "data": result,
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update fundamentals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update fundamentals: {str(e)}")


@router.post("/calculate-universe-scores")
async def calculate_universe_scores(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Calculate universe scores for all interesting_tickers."""
    try:
        logger.info("Manual universe scoring requested")
        
        market_data_service = MarketDataService(db)
        result = await market_data_service.calculate_universe_scores()
        
        return {
            "message": "Universe scoring completed",
            "status": "success" if result["success"] else "failed",
            "data": result,
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate universe scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate universe scores: {str(e)}")


@router.post("/update-recommendation-tickers")
async def update_recommendation_tickers(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Update ticker quotes and option chains for top 20 SP500 and manual tickers."""
    try:
        logger.info("Manual recommendation tickers update requested")
        
        market_data_service = MarketDataService(db)
        result = await market_data_service.update_recommendation_tickers()
        
        return {
            "message": "Recommendation tickers update completed",
            "status": "success" if result["success"] else "failed",
            "data": result,
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update recommendation tickers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update recommendation tickers: {str(e)}")


@router.post("/market-population")
async def run_market_population(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Run complete market population (SP500 update + fundamentals update)."""
    try:
        logger.info("Manual market population requested")
        
        market_data_service = MarketDataService(db)
        
        # Step 1: Update SP500 universe
        logger.info("Step 1: Updating SP500 universe...")
        sp500_result = await market_data_service.update_sp500_universe()
        
        # Step 2: Update all fundamentals
        logger.info("Step 2: Updating all fundamentals...")
        fundamentals_result = await market_data_service.update_all_fundamentals()
        
        return {
            "message": "Market population completed",
            "status": "success",
            "data": {
                "sp500_update": {
                    "updated_tickers_count": len(sp500_result),
                    "tickers": [t.symbol for t in sp500_result[:10]]
                },
                "fundamentals_update": fundamentals_result
            },
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to run market population: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run market population: {str(e)}")


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
            "timestamp": pacific_now().isoformat()
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
        
        query = select(InterestingTicker, TickerQuote).outerjoin(
            TickerQuote, InterestingTicker.symbol == TickerQuote.symbol
        ).where(InterestingTicker.active == True)
        
        if sector:
            query = query.where(InterestingTicker.sector == sector)
        
        # Get total count
        count_query = select(func.count(InterestingTicker.id)).where(InterestingTicker.active == True)
        if sector:
            count_query = count_query.where(InterestingTicker.sector == sector)
        
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Get tickers with pagination
        tickers_result = await db.execute(query.offset(offset).limit(limit))
        rows = tickers_result.all()
        
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
                        "current_price": quote.current_price if quote else None,
                        "volume_avg_20d": quote.volume_avg_20d if quote else None,
                        "volatility_30d": quote.volatility_30d if quote else None,
                        "beta": ticker.beta,
                        "pe_ratio": ticker.pe_ratio,
                        "dividend_yield": ticker.dividend_yield,
                        "universe_score": ticker.universe_score,
                        "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
                    } for ticker, quote in rows
                ],
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            },
            "timestamp": pacific_now().isoformat()
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
            select(InterestingTicker, TickerQuote).outerjoin(
                TickerQuote, InterestingTicker.symbol == TickerQuote.symbol
            ).where(
                and_(
                    InterestingTicker.symbol == symbol.upper(),
                    InterestingTicker.active == True
                )
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
        
        ticker, quote = row
        
        return {
            "status": "success",
            "data": {
                "symbol": ticker.symbol,
                "name": ticker.name,
                "sector": ticker.sector,
                "industry": ticker.industry,
                "market_cap": ticker.market_cap,
                "current_price": quote.current_price if quote else None,
                "volume_avg_20d": quote.volume_avg_20d if quote else None,
                "volatility_30d": quote.volatility_30d if quote else None,
                "beta": ticker.beta,
                "pe_ratio": ticker.pe_ratio,
                "dividend_yield": ticker.dividend_yield,
                "universe_score": ticker.universe_score,
                "last_analysis_date": ticker.last_analysis_date.isoformat() if ticker.last_analysis_date else None,
                "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
            },
            "timestamp": pacific_now().isoformat()
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
        
        # If no expiration provided, get optimal expiration (21-35 days)
        if not expiration:
            logger.info(f"Getting optimal expiration for {symbol}")
            expiration = await tradier_manager.get_optimal_expiration(symbol.upper())
            if not expiration:
                # Fallback to next month
                next_month = datetime.now() + timedelta(days=30)
                expiration = next_month.strftime("%Y-%m-%d")
                logger.info(f"No optimal expiration found, using fallback: {expiration}")
        
        # Actually fetch and sync options data
        logger.info(f"Fetching options data for {symbol} with expiration {expiration}")
        options = await tradier_manager.sync_options_data(symbol.upper(), expiration)
        
        # Convert options to dict for response
        options_data = []
        for option in options:
            options_data.append({
                "symbol": option.symbol,
                "strike": option.strike,
                "option_type": option.option_type,
                "expiry": option.expiry.isoformat(),
                "bid": option.bid,
                "ask": option.ask,
                "last": option.last,
                "delta": option.delta,
                "gamma": option.gamma,
                "theta": option.theta,
                "vega": option.vega,
                "implied_volatility": option.implied_volatility,
                "open_interest": option.open_interest,
                "volume": option.volume,
                "dte": option.dte
            })
        
        return {
            "message": f"Successfully fetched options data for {symbol}",
            "status": "success",
            "symbol": symbol.upper(),
            "expiration": expiration,
            "options_count": len(options_data),
            "options": options_data,
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch options for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch options: {str(e)}")


@router.get("/tradier-test")
async def test_tradier_connection():
    """Test Tradier API connection."""
    try:
        from clients.tradier import TradierClient
        
        async with TradierClient() as client:
            result = await client.test_connection()
            return result
    except Exception as e:
        logger.error(f"❌ Tradier connection test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Tradier connection test failed: {str(e)}"
        }

@router.get("/test-delta-parsing")
async def test_delta_parsing():
    """Test delta parsing with mock Tradier API response."""
    try:
        from clients.tradier import TradierDataManager
        
        # Mock Tradier API response similar to the example provided
        mock_response = {
            "options": {
                "option": [
                    {
                        "symbol": "VXX190517P00016000",
                        "description": "VXX May 17 2019 $16.00 Put",
                        "exch": "Z",
                        "type": "option",
                        "last": None,
                        "change": None,
                        "volume": 0,
                        "open": None,
                        "high": None,
                        "low": None,
                        "close": None,
                        "bid": 0.0,
                        "ask": 0.01,
                        "underlying": "VXX",
                        "strike": 16.0,
                        "change_percentage": None,
                        "average_volume": 0,
                        "last_volume": 0,
                        "trade_date": 0,
                        "prevclose": None,
                        "week_52_high": 0.0,
                        "week_52_low": 0.0,
                        "bidsize": 0,
                        "bidexch": "J",
                        "bid_date": 1557171657000,
                        "asksize": 611,
                        "askexch": "Z",
                        "ask_date": 1557172096000,
                        "open_interest": 10,
                        "contract_size": 100,
                        "expiration_date": "2019-05-17",
                        "expiration_type": "standard",
                        "option_type": "put",
                        "root_symbol": "VXX",
                        "greeks": {
                            "delta": 1.0,
                            "gamma": 1.95546E-10,
                            "theta": -0.00204837,
                            "vega": 3.54672E-9,
                            "rho": 0.106077,
                            "phi": -0.28801,
                            "bid_iv": 0.0,
                            "mid_iv": 0.0,
                            "ask_iv": 0.0,
                            "smv_vol": 0.380002,
                            "updated_at": "2019-08-29 14:59:08"
                        }
                    },
                    {
                        "symbol": "VXX190517C00016000",
                        "description": "VXX May 17 2019 $16.00 Call",
                        "exch": "Z",
                        "type": "option",
                        "last": None,
                        "change": None,
                        "volume": 0,
                        "open": None,
                        "high": None,
                        "low": None,
                        "close": None,
                        "bid": 10.85,
                        "ask": 11.0,
                        "underlying": "VXX",
                        "strike": 16.0,
                        "change_percentage": None,
                        "average_volume": 0,
                        "last_volume": 0,
                        "trade_date": 0,
                        "prevclose": None,
                        "week_52_high": 0.0,
                        "week_52_low": 0.0,
                        "bidsize": 55,
                        "bidexch": "C",
                        "bid_date": 1557172097000,
                        "asksize": 80,
                        "askexch": "E",
                        "ask_date": 1557172135000,
                        "open_interest": 0,
                        "contract_size": 100,
                        "expiration_date": "2019-05-17",
                        "expiration_type": "standard",
                        "option_type": "call",
                        "root_symbol": "VXX",
                        "greeks": {
                            "delta": 1.0,
                            "gamma": 1.95546E-10,
                            "theta": -0.00204837,
                            "vega": 3.54672E-9,
                            "rho": 0.106077,
                            "phi": -0.28801,
                            "bid_iv": 0.0,
                            "mid_iv": 0.0,
                            "ask_iv": 0.0,
                            "smv_vol": 0.380002,
                            "updated_at": "2019-08-29 14:59:08"
                        }
                    }
                ]
            }
        }
        
        # Test the parsing logic directly
        from clients.tradier import TradierDataManager
        tradier_manager = TradierDataManager(None)  # No DB needed for this test
        
        parsed_options = []
        for opt_data in mock_response["options"]["option"]:
            option = tradier_manager._parse_option_data("VXX", "2019-05-17", opt_data)
            if option:
                parsed_options.append({
                    "symbol": option.symbol,
                    "strike": option.strike,
                    "option_type": option.option_type,
                    "expiry": option.expiry.isoformat(),
                    "bid": option.bid,
                    "ask": option.ask,
                    "last": option.last,
                    "delta": option.delta,
                    "gamma": option.gamma,
                    "theta": option.theta,
                    "vega": option.vega,
                    "implied_volatility": option.implied_volatility,
                    "open_interest": option.open_interest,
                    "volume": option.volume,
                    "dte": option.dte
                })
        
        return {
            "status": "success",
            "message": "Delta parsing test completed",
            "parsed_options": parsed_options,
            "original_greeks": [
                {
                    "symbol": opt["symbol"],
                    "greeks": opt["greeks"]
                } for opt in mock_response["options"]["option"]
            ],
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Delta parsing test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Delta parsing test failed: {str(e)}"
        }

@router.get("/tradier-quote/{symbol}")
async def test_tradier_quote(symbol: str):
    """Test Tradier quote API for a specific symbol."""
    try:
        from clients.tradier import TradierClient
        
        async with TradierClient() as client:
            logger.info(f"🔗 Testing quote for {symbol}...")
            quote_data = await client.get_quote(symbol)
            logger.info(f"📊 Quote data: {quote_data}")
            
            return {
                "status": "success",
                "symbol": symbol,
                "quote_data": quote_data,
                "timestamp": pacific_now().isoformat()
            }
    except Exception as e:
        logger.error(f"❌ Tradier quote test failed for {symbol}: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Tradier quote test failed: {str(e)}"
        }

@router.get("/tradier-fundamentals/{symbol}")
async def test_tradier_fundamentals(symbol: str):
    """Test Tradier fundamentals API for a specific symbol."""
    try:
        from clients.tradier import TradierClient
        
        async with TradierClient() as client:
            # Test basic quote first
            logger.info(f"🔗 Testing basic quote for {symbol}...")
            quote_data = await client.get_quote(symbol)
            logger.info(f"📊 Quote data: {quote_data}")
            
            # Test fundamentals company data
            logger.info(f"🔗 Testing fundamentals company for {symbol}...")
            fundamentals_data = await client.get_fundamentals_company(symbol)
            logger.info(f"📊 Fundamentals company data: {fundamentals_data}")
            
            # Test fundamentals ratios data
            logger.info(f"🔗 Testing fundamentals ratios for {symbol}...")
            ratios_data = await client.get_fundamentals_ratios(symbol)
            logger.info(f"📊 Fundamentals ratios data: {ratios_data}")
            
            return {
                "status": "success",
                "symbol": symbol,
                "quote_data": quote_data,
                "fundamentals_company": fundamentals_data,
                "fundamentals_ratios": ratios_data,
                "timestamp": pacific_now().isoformat()
            }
    except Exception as e:
        logger.error(f"❌ Tradier fundamentals test failed for {symbol}: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Tradier fundamentals test failed: {str(e)}"
        }

@router.get("/status")
async def get_market_data_status(
    db: AsyncSession = Depends(get_async_db)
):
    """Get market data status and counts."""
    try:
        from sqlalchemy import func, select
        
        # Get ticker count
        ticker_result = await db.execute(
            select(func.count(InterestingTicker.id)).where(InterestingTicker.active == True)
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
                "timestamp": pacific_now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get market data status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# Interesting Tickers Management Endpoints

@router.get("/interesting-tickers")
async def get_interesting_tickers(
    db: AsyncSession = Depends(get_async_db)
):
    """Get all interesting tickers with their data."""
    try:
        from sqlalchemy import select
        
        # Get interesting tickers with their quotes
        result = await db.execute(
            select(InterestingTicker, TickerQuote)
            .outerjoin(TickerQuote, InterestingTicker.symbol == TickerQuote.symbol)
            .order_by(InterestingTicker.symbol)
        )
        rows = result.all()
        
        tickers = []
        for ticker, quote in rows:
            ticker_data = {
                "symbol": ticker.symbol,
                "name": ticker.name,
                "sector": ticker.sector,
                "industry": ticker.industry,
                "market_cap": ticker.market_cap,
                "beta": ticker.beta,
                "pe_ratio": ticker.pe_ratio,
                "dividend_yield": ticker.dividend_yield,
                "next_earnings_date": ticker.next_earnings_date.isoformat() if ticker.next_earnings_date else None,
                "active": ticker.active,
                "universe_score": ticker.universe_score,
                "source": ticker.source,
                "added_at": ticker.added_at.isoformat() if ticker.added_at else None,
                "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None,
                "current_price": quote.current_price if quote else None,
                "volume_avg_20d": quote.volume_avg_20d if quote else None,
                "volatility_30d": quote.volatility_30d if quote else None,
                "quote_updated_at": quote.updated_at.isoformat() if quote and quote.updated_at else None
            }
            tickers.append(ticker_data)
        
        return {
            "status": "success",
            "data": tickers,
            "count": len(tickers),
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get interesting tickers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get interesting tickers: {str(e)}")


@router.post("/interesting-tickers")
async def add_interesting_ticker(
    request: dict,
    db: AsyncSession = Depends(get_async_db)
):
    symbol = request.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    """Add a new interesting ticker and populate its data."""
    try:
        from sqlalchemy import select
        
        logger.info(f"🚀 Adding new interesting ticker: {symbol.upper()}")
        
        # Check if ticker already exists
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        existing_ticker = result.scalar_one_or_none()
        
        if existing_ticker:
            raise HTTPException(status_code=400, detail=f"Ticker {symbol.upper()} already exists")
        
        # Create new ticker
        ticker = InterestingTicker(
            symbol=symbol.upper(),
            active=True,
            source="manual",
            added_at=pacific_now(),
            updated_at=pacific_now()
        )
        db.add(ticker)
        await db.flush()  # Flush to get the ID
        
        logger.info(f"📝 Created new ticker record for {symbol.upper()}")
        
        # Populate data using market data service
        logger.info(f"📊 Populating market data for {symbol.upper()}...")
        market_data_service = MarketDataService(db)
        
        # Step 1: Update ticker market data (Tradier + API Ninjas)
        updated_ticker = await market_data_service._update_ticker_market_data(ticker)
        
        # Step 2: Force refresh the ticker data to ensure all fields are populated
        logger.info(f"🔄 Refreshing ticker data for {symbol.upper()}...")
        
        # Get the updated ticker from database
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        final_ticker = result.scalar_one_or_none()
        
        if final_ticker:
            logger.info(f"✅ Final ticker data for {symbol.upper()}:")
            logger.info(f"   📊 Name: {final_ticker.name}")
            logger.info(f"   📊 Sector: {final_ticker.sector}")
            logger.info(f"   📊 Industry: {final_ticker.industry}")
            logger.info(f"   📊 Market Cap: ${final_ticker.market_cap}")
            logger.info(f"   📊 P/E Ratio: {final_ticker.pe_ratio}")
            logger.info(f"   📊 Beta: {final_ticker.beta}")
            logger.info(f"   📊 Next Earnings: {final_ticker.next_earnings_date}")
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully added ticker {symbol.upper()}",
            "symbol": symbol.upper(),
            "timestamp": pacific_now().isoformat(),
            "ticker_data": {
                "name": final_ticker.name if final_ticker else None,
                "sector": final_ticker.sector if final_ticker else None,
                "industry": final_ticker.industry if final_ticker else None,
                "market_cap": final_ticker.market_cap if final_ticker else None,
                "pe_ratio": final_ticker.pe_ratio if final_ticker else None,
                "beta": final_ticker.beta if final_ticker else None,
                "next_earnings_date": final_ticker.next_earnings_date.isoformat() if final_ticker and final_ticker.next_earnings_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to add interesting ticker {symbol}: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to add ticker: {str(e)}")


@router.post("/interesting-tickers/{symbol}/refresh")
async def refresh_ticker_data(
    symbol: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Refresh market data for a specific ticker."""
    try:
        from sqlalchemy import select
        
        logger.info(f"🔄 Refreshing market data for ticker: {symbol.upper()}")
        
        # Get the ticker
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")
        
        # Update market data
        market_data_service = MarketDataService(db)
        updated_ticker = await market_data_service._update_ticker_market_data(ticker)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully refreshed data for {symbol.upper()}",
            "symbol": symbol.upper(),
            "timestamp": pacific_now().isoformat(),
            "ticker_data": {
                "name": updated_ticker.name,
                "sector": updated_ticker.sector,
                "industry": updated_ticker.industry,
                "market_cap": updated_ticker.market_cap,
                "pe_ratio": updated_ticker.pe_ratio,
                "beta": updated_ticker.beta,
                "next_earnings_date": updated_ticker.next_earnings_date.isoformat() if updated_ticker.next_earnings_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to refresh ticker data for {symbol}: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh ticker data: {str(e)}")

@router.put("/interesting-tickers/{symbol}/toggle")
async def toggle_ticker_active(
    symbol: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Toggle ticker active status."""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")
        
        # Toggle active status
        ticker.active = not ticker.active
        ticker.updated_at = pacific_now()
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Ticker {symbol.upper()} {'activated' if ticker.active else 'deactivated'}",
            "symbol": symbol.upper(),
            "active": ticker.active,
            "timestamp": pacific_now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to toggle ticker {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle ticker: {str(e)}")


@router.delete("/interesting-tickers/{symbol}")
async def remove_interesting_ticker(
    symbol: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Remove an interesting ticker."""
    try:
        from sqlalchemy import select, delete
        
        # Check if ticker exists
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")
        
        # Delete associated quote first (due to foreign key constraint)
        await db.execute(
            delete(TickerQuote).where(TickerQuote.symbol == symbol.upper())
        )
        
        # Delete the ticker
        await db.execute(
            delete(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully removed ticker {symbol.upper()}",
            "symbol": symbol.upper(),
            "timestamp": pacific_now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to remove ticker {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove ticker: {str(e)}")


@router.post("/interesting-tickers/{symbol}/refresh")
async def refresh_ticker_data(
    symbol: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Refresh data for a specific ticker."""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")
        
        # Refresh data using market data service
        market_data_service = MarketDataService(db)
        await market_data_service._update_ticker_market_data(ticker)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully refreshed data for {symbol.upper()}",
            "symbol": symbol.upper(),
            "timestamp": pacific_now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to refresh ticker {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh ticker: {str(e)}")


# Universe Management Endpoints

@router.get("/universe")
async def get_filtered_universe(
    max_tickers: int = 10,
    refresh_data: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """Get filtered universe of tickers for analysis."""
    try:
        universe_service = UniverseService(db)
        tickers = await universe_service.get_filtered_universe(max_tickers, refresh_data)
        
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
                        "pe_ratio": ticker.pe_ratio,
                        "beta": ticker.beta,
                        "dividend_yield": ticker.dividend_yield,
                        "next_earnings_date": ticker.next_earnings_date.isoformat() if ticker.next_earnings_date else None,
                        "universe_score": ticker.universe_score,
                        "active": ticker.active,
                        "source": ticker.source,
                        "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None,
                        "last_analysis_date": ticker.last_analysis_date.isoformat() if ticker.last_analysis_date else None
                    } for ticker in tickers
                ],
                "count": len(tickers),
                "max_tickers": max_tickers,
                "refresh_data": refresh_data
            },
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get filtered universe: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get filtered universe: {str(e)}")


@router.post("/universe/refresh")
async def refresh_universe_data(
    max_tickers: int = 10,
    db: AsyncSession = Depends(get_async_db)
):
    """Refresh market data for the universe."""
    try:
        universe_service = UniverseService(db)
        updated_tickers = await universe_service.refresh_universe_data(max_tickers)
        
        return {
            "status": "success",
            "message": "Universe data refresh completed",
            "data": {
                "updated_tickers_count": len(updated_tickers),
                "max_tickers": max_tickers,
                "tickers": [
                    {
                        "symbol": ticker.symbol,
                        "name": ticker.name,
                        "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
                    } for ticker in updated_tickers[:10]  # Show first 10
                ]
            },
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh universe data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh universe data: {str(e)}")


@router.get("/universe/statistics")
async def get_universe_statistics(
    db: AsyncSession = Depends(get_async_db)
):
    """Get comprehensive statistics about the current universe."""
    try:
        universe_service = UniverseService(db)
        statistics = await universe_service.get_universe_statistics()
        
        return {
            "status": "success",
            "data": statistics,
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get universe statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get universe statistics: {str(e)}")


@router.get("/universe/tickers-needing-updates")
async def get_tickers_needing_updates(
    max_tickers: int = 10,
    db: AsyncSession = Depends(get_async_db)
):
    """Get tickers that need market data updates."""
    try:
        universe_service = UniverseService(db)
        tickers = await universe_service.get_tickers_needing_updates(max_tickers)
        
        return {
            "status": "success",
            "data": {
                "tickers": [
                    {
                        "symbol": ticker.symbol,
                        "name": ticker.name,
                        "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None,
                        "active": ticker.active
                    } for ticker in tickers
                ],
                "count": len(tickers),
                "max_tickers": max_tickers
            },
            "timestamp": pacific_now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get tickers needing updates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tickers needing updates: {str(e)}")