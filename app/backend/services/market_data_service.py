"""Market data service for dynamic ticker management and S&P 500 universe selection."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, func, select
import httpx
import yfinance as yf
import pandas as pd

from config import settings
from db.models import Ticker, Option, EarningsCalendar
from clients.tradier import TradierDataManager

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing dynamic ticker universe and market data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tradier_data = TradierDataManager(db)
    
    async def update_sp500_universe(self) -> List[Ticker]:
        """Update the ticker universe with current S&P 500 constituents."""
        logger.info("Updating S&P 500 universe...")
        
        try:
            # Get current S&P 500 constituents
            sp500_tickers = await self._get_sp500_constituents()
            
            if not sp500_tickers:
                logger.error("Failed to fetch S&P 500 constituents")
                return []
            
            logger.info(f"Found {len(sp500_tickers)} S&P 500 constituents")
            logger.info(f"First few tickers: {sp500_tickers[:5]}")
            
            # Update tickers table with rate limiting
            updated_tickers = []
            for i, ticker_data in enumerate(sp500_tickers):
                logger.info(f"Processing ticker {i+1}/{len(sp500_tickers)}: {ticker_data}")
                ticker = await self._upsert_ticker(ticker_data)
                if ticker:
                    updated_tickers.append(ticker)
                    logger.info(f"Successfully processed ticker: {ticker.symbol}")
                else:
                    logger.warning(f"Failed to process ticker: {ticker_data}")
                
                # Rate limiting: pause every 10 requests to avoid hitting API limits
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(sp500_tickers)} tickers, pausing for rate limiting...")
                    await asyncio.sleep(2)  # 2 second pause every 10 requests
            
            # Deactivate tickers no longer in S&P 500
            await self._deactivate_old_tickers(sp500_tickers)
            
            logger.info(f"Successfully updated {len(updated_tickers)} tickers")
            return updated_tickers
            
        except Exception as e:
            logger.error(f"Error updating S&P 500 universe: {e}")
            return []
    
    async def _get_sp500_constituents(self) -> List[Dict[str, Any]]:
        """Get current S&P 500 constituents with basic info."""
        try:
            # Method 1: Try using yfinance to get S&P 500 constituents
            sp500 = yf.Ticker("^GSPC")
            constituents = sp500.info.get('constituents', [])
            
            if constituents:
                logger.info(f"Found {len(constituents)} constituents via yfinance")
                return [{"symbol": symbol} for symbol in constituents]
            
            # Method 2: Fallback to a curated list of major S&P 500 stocks
            logger.warning("Using fallback S&P 500 list")
            return self._get_fallback_sp500_list()
            
        except Exception as e:
            logger.error(f"Error fetching S&P 500 constituents: {e}")
            return self._get_fallback_sp500_list()
    
    def _get_fallback_sp500_list(self) -> List[Dict[str, Any]]:
        """Fallback list of major S&P 500 stocks."""
        # Top 100 S&P 500 stocks by market cap (simplified)
        return [
            {"symbol": "AAPL"}, {"symbol": "MSFT"}, {"symbol": "GOOGL"}, {"symbol": "AMZN"},
            {"symbol": "NVDA"}, {"symbol": "META"}, {"symbol": "BRK-B"}, {"symbol": "LLY"},
            {"symbol": "TSLA"}, {"symbol": "V"}, {"symbol": "UNH"}, {"symbol": "XOM"},
            {"symbol": "JNJ"}, {"symbol": "WMT"}, {"symbol": "JPM"}, {"symbol": "PG"},
            {"symbol": "MA"}, {"symbol": "HD"}, {"symbol": "CVX"}, {"symbol": "AVGO"},
            {"symbol": "ABBV"}, {"symbol": "PFE"}, {"symbol": "KO"}, {"symbol": "BAC"},
            {"symbol": "PEP"}, {"symbol": "COST"}, {"symbol": "TMO"}, {"symbol": "ACN"},
            {"symbol": "DHR"}, {"symbol": "VZ"}, {"symbol": "MRK"}, {"symbol": "ABT"},
            {"symbol": "WFC"}, {"symbol": "CMCSA"}, {"symbol": "ADBE"}, {"symbol": "NFLX"},
            {"symbol": "CRM"}, {"symbol": "PM"}, {"symbol": "TXN"}, {"symbol": "NEE"},
            {"symbol": "RTX"}, {"symbol": "HON"}, {"symbol": "QCOM"}, {"symbol": "LOW"},
            {"symbol": "UNP"}, {"symbol": "UPS"}, {"symbol": "IBM"}, {"symbol": "MS"},
            {"symbol": "BMY"}, {"symbol": "CAT"}, {"symbol": "GS"}, {"symbol": "AMAT"},
            {"symbol": "SPGI"}, {"symbol": "INTU"}, {"symbol": "AXP"}, {"symbol": "GILD"},
            {"symbol": "ISRG"}, {"symbol": "VRTX"}, {"symbol": "ADI"}, {"symbol": "TGT"},
            {"symbol": "PLD"}, {"symbol": "SCHW"}, {"symbol": "ITW"}, {"symbol": "BDX"},
            {"symbol": "TJX"}, {"symbol": "CB"}, {"symbol": "SO"}, {"symbol": "DUK"},
            {"symbol": "NSC"}, {"symbol": "CME"}, {"symbol": "EOG"}, {"symbol": "SLB"},
            {"symbol": "USB"}, {"symbol": "PGR"}, {"symbol": "CI"}, {"symbol": "AON"},
            {"symbol": "ETN"}, {"symbol": "MMC"}, {"symbol": "APD"}, {"symbol": "SHW"},
            {"symbol": "TFC"}, {"symbol": "PNC"}, {"symbol": "COF"}, {"symbol": "BLK"},
            {"symbol": "MO"}, {"symbol": "GE"}, {"symbol": "FIS"}, {"symbol": "ICE"},
            {"symbol": "NOC"}, {"symbol": "SRE"}, {"symbol": "PSA"}, {"symbol": "AIG"},
            {"symbol": "MET"}, {"symbol": "PRU"}, {"symbol": "ALL"}, {"symbol": "TRV"},
            {"symbol": "C"}, {"symbol": "WBA"}, {"symbol": "GM"}, {"symbol": "F"},
            {"symbol": "DAL"}, {"symbol": "UAL"}, {"symbol": "AAL"}, {"symbol": "LUV"},
            {"symbol": "UAL"}, {"symbol": "DAL"}, {"symbol": "AAL"}, {"symbol": "LUV"}
        ]
    
    async def _upsert_ticker(self, ticker_data: Dict[str, Any]) -> Optional[Ticker]:
        """Create or update a ticker with market data."""
        try:
            symbol = ticker_data["symbol"]
            
            # Check if ticker exists
            result = await self.db.execute(
                select(Ticker).where(Ticker.symbol == symbol)
            )
            ticker = result.scalar_one_or_none()
            
            if not ticker:
                # Create new ticker
                ticker = Ticker(
                    symbol=symbol,
                    active=True,
                    updated_at=datetime.utcnow()
                )
                self.db.add(ticker)
                logger.info(f"Created new ticker: {symbol}")
            else:
                # Update existing ticker
                ticker.active = True
                ticker.updated_at = datetime.utcnow()
                logger.debug(f"Updated existing ticker: {symbol}")
            
            # Fetch and update market data using TradierDataManager
            await self._update_ticker_market_data(ticker)
            
            # Commit the changes
            await self.db.commit()
            
            return ticker
            
        except Exception as e:
            logger.error(f"Error upserting ticker {ticker_data.get('symbol', 'unknown')}: {e}")
            await self.db.rollback()
            return None
    
    async def _update_ticker_market_data(self, ticker: Ticker) -> Ticker:
        """Update ticker market data using Tradier API."""
        try:
            # Use TradierDataManager to get comprehensive data
            tradier_manager = TradierDataManager(self.db)
            updated_ticker = await tradier_manager.sync_ticker_data(ticker.symbol)
            
            logger.info(f"Updated market data for {ticker.symbol}: price=${updated_ticker.current_price}, "
                       f"volume={updated_ticker.volume_avg_20d}, market_cap=${updated_ticker.market_cap}, "
                       f"beta={updated_ticker.beta}, pe_ratio={updated_ticker.pe_ratio}")
            
            return updated_ticker
            
        except Exception as e:
            logger.error(f"Error updating market data for {ticker.symbol}: {e}")
            # Return the original ticker if update fails
            return ticker
    
    async def _deactivate_old_tickers(self, current_tickers: List[Dict[str, Any]]) -> None:
        """Deactivate tickers no longer in the current universe."""
        try:
            current_symbols = {t["symbol"] for t in current_tickers}
            
            # Find tickers not in current universe
            result = await self.db.execute(
                select(Ticker).where(
                    and_(
                        Ticker.active == True,
                        ~Ticker.symbol.in_(current_symbols)
                    )
                )
            )
            old_tickers = result.scalars().all()
            
            for ticker in old_tickers:
                ticker.active = False
                logger.info(f"Deactivated ticker: {ticker.symbol}")
            
            if old_tickers:
                await self.db.commit()
                logger.info(f"Deactivated {len(old_tickers)} old tickers")
                
        except Exception as e:
            logger.error(f"Error deactivating old tickers: {e}")
    
    async def refresh_market_data(self, max_tickers: int = None) -> List[Ticker]:
        """Refresh market data for active tickers."""
        if max_tickers is None:
            max_tickers = settings.max_tickers_per_cycle
        
        logger.info(f"Refreshing market data for up to {max_tickers} tickers")
        
        # Get active tickers that need updating (older than 1 hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        result = await self.db.execute(
            select(Ticker).where(
                and_(
                    Ticker.active == True,
                    or_(
                        Ticker.updated_at == None,
                        Ticker.updated_at < cutoff_time
                    )
                )
            ).limit(max_tickers)
        )
        tickers_to_update = result.scalars().all()
        
        updated_tickers = []
        for ticker in tickers_to_update:
            try:
                updated_ticker = await self._update_ticker_market_data(ticker)
                updated_tickers.append(updated_ticker)
            except Exception as e:
                logger.warning(f"Error refreshing {ticker.symbol}: {e}")
        
        await self.db.commit()
        logger.info(f"Refreshed market data for {len(updated_tickers)} tickers")
        
        return updated_tickers
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get summary of current market data."""
        try:
            # Get total active tickers
            result = await self.db.execute(
                select(func.count(Ticker.id)).where(Ticker.active == True)
            )
            total_tickers = result.scalar()
            
            # Get recently updated tickers
            result = await self.db.execute(
                select(func.count(Ticker.id)).where(
                    Ticker.updated_at >= datetime.utcnow() - timedelta(hours=24)
                )
            )
            recent_updates = result.scalar()
            
            # Sector distribution
            result = await self.db.execute(
                select(Ticker.sector, func.count(Ticker.id)).where(
                    Ticker.active == True
                ).group_by(Ticker.sector)
            )
            sector_counts = result.all()
            
            return {
                "total_active_tickers": total_tickers,
                "recently_updated": recent_updates,
                "sector_distribution": dict(sector_counts),
                "last_update": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {"error": str(e)}
    
    async def populate_sp500_fundamentals_and_earnings(self) -> Dict[str, Any]:
        """Populate SP500 fundamentals and earnings data weekly."""
        logger.info("Starting weekly SP500 fundamentals and earnings population...")
        
        try:
            # Get current SP500 constituents
            sp500_symbols = await self.tradier_data.client.get_sp500_constituents()
            
            if not sp500_symbols:
                logger.error("Failed to fetch SP500 constituents")
                return {
                    "success": False,
                    "error": "Failed to fetch SP500 constituents",
                    "total_processed": 0,
                    "successful_updates": 0,
                    "successful_tickers": []
                }
            
            logger.info(f"Processing {len(sp500_symbols)} SP500 tickers")
            
            successful_updates = 0
            successful_tickers = []
            failed_tickers = []
            
            # Process each ticker with rate limiting
            for i, symbol in enumerate(sp500_symbols):
                try:
                    logger.info(f"Processing ticker {i+1}/{len(sp500_symbols)}: {symbol}")
                    
                    # Update ticker fundamentals
                    ticker = await self.tradier_data.sync_ticker_data(symbol)
                    
                    if ticker and ticker.current_price is not None:
                        # Basic quote data was successfully updated
                        successful_updates += 1
                        successful_tickers.append(symbol)
                        
                        # Log additional data if available
                        data_log = f"✅ Successfully updated data for {symbol} (price: ${ticker.current_price})"
                        if ticker.sector:
                            data_log += f", sector: {ticker.sector}"
                        if ticker.market_cap:
                            data_log += f", market cap: ${ticker.market_cap:.1f}B"
                        if ticker.pe_ratio:
                            data_log += f", P/E: {ticker.pe_ratio:.1f}"
                        if ticker.next_earnings_date:
                            data_log += f", next earnings: {ticker.next_earnings_date.strftime('%Y-%m-%d')}"
                        
                        logger.info(data_log)
                        
                        # Also try to update earnings calendar (already done in sync_ticker_data)
                        # This is now handled within sync_ticker_data method
                    else:
                        failed_tickers.append(symbol)
                        logger.warning(f"❌ Failed to update data for {symbol}")
                    
                    # Rate limiting: pause every 10 requests
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(sp500_symbols)} tickers, pausing for rate limiting...")
                        await asyncio.sleep(2)  # 2 second pause every 10 requests
                    
                except Exception as e:
                    failed_tickers.append(symbol)
                    logger.error(f"Error processing {symbol}: {e}")
                    continue
            
            # Commit any remaining changes
            await self.db.commit()
            
            # Prepare result
            result = {
                "success": True,
                "total_processed": len(sp500_symbols),
                "successful_updates": successful_updates,
                "successful_tickers": successful_tickers,
                "failed_tickers": failed_tickers,
                "success_rate": (successful_updates / len(sp500_symbols)) * 100 if sp500_symbols else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Weekly SP500 population completed: {successful_updates}/{len(sp500_symbols)} successful updates")
            logger.info(f"Successful tickers: {successful_tickers[:10]}{'...' if len(successful_tickers) > 10 else ''}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in weekly SP500 population: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "total_processed": 0,
                "successful_updates": 0,
                "successful_tickers": [],
                "timestamp": datetime.utcnow().isoformat()
            }