from utils.timezone import pacific_now
"""Market data service for dynamic ticker management and S&P 500 universe selection."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select

from config import settings
from db.models import InterestingTicker, TickerQuote
from clients.tradier import TradierDataManager
from clients.api_ninjas import APINinjasClient
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing dynamic ticker universe and market data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tradier_data = TradierDataManager(db)
        self.api_ninjas = APINinjasClient()
    
    async def update_sp500_universe(self) -> List[InterestingTicker]:
        """Update the ticker universe with current S&P 500 constituents."""
        logger.info("Updating S&P 500 universe...")
        
        try:
            # Get current S&P 500 constituents using API Ninjas
            sp500_symbols = await self.api_ninjas.get_sp500_tickers()
            
            if not sp500_symbols:
                logger.error("Failed to fetch S&P 500 constituents")
                return []
            
            logger.info(f"Found {len(sp500_symbols)} S&P 500 constituents")
            logger.info(f"First few tickers: {sp500_symbols[:5]}")
            
            # Update tickers table with rate limiting
            updated_tickers = []
            for i, symbol in enumerate(sp500_symbols):
                logger.info(f"Processing ticker {i+1}/{len(sp500_symbols)}: {symbol}")
                ticker_data = {"symbol": symbol}
                ticker = await self._upsert_ticker(ticker_data)
                if ticker:
                    updated_tickers.append(ticker)
                    logger.info(f"Successfully processed ticker: {ticker.symbol}")
                else:
                    logger.warning(f"Failed to process ticker: {symbol}")
                
                # Rate limiting: pause every 10 requests to avoid hitting API limits
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(sp500_symbols)} tickers, pausing for rate limiting...")
                    await asyncio.sleep(2)  # 2 second pause every 10 requests
            
            # Deactivate tickers no longer in S&P 500
            await self._deactivate_old_tickers(sp500_symbols)
            
            logger.info(f"Successfully updated {len(updated_tickers)} tickers")
            return updated_tickers
            
        except Exception as e:
            logger.error(f"Error updating S&P 500 universe: {e}")
            return []
    

    async def _upsert_ticker(self, ticker_data: Dict[str, Any]) -> Optional[InterestingTicker]:
        """Create or update a ticker with market data."""
        try:
            symbol = ticker_data["symbol"]
            
            # Check if ticker exists
            result = await self.db.execute(
                select(InterestingTicker).where(InterestingTicker.symbol == symbol)
            )
            ticker = result.scalar_one_or_none()
            
            if not ticker:
                # Create new ticker
                ticker = InterestingTicker(
                    symbol=symbol,
                    active=True,
                    source="sp500",
                    added_at=pacific_now(),
                    updated_at=pacific_now()
                )
                self.db.add(ticker)
                logger.info(f"Created new ticker: {symbol}")
            else:
                # Update existing ticker
                ticker.active = True
                ticker.updated_at = pacific_now()
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
    
    async def _update_ticker_market_data(self, ticker: InterestingTicker) -> InterestingTicker:
        """Update ticker market data using Tradier API and API Ninjas."""
        try:
            # Get Tradier data (price, volume, fundamentals)
            tradier_data = await self.tradier_data.sync_ticker_data(ticker.symbol)
            
            # Update fundamental data in InterestingTicker from Tradier
            if tradier_data:
                # Update fundamental data (P/E ratio, dividend yield, beta, name)
                if tradier_data.get("pe_ratio") is not None:
                    ticker.pe_ratio = tradier_data["pe_ratio"]
                
                if tradier_data.get("dividend_yield") is not None:
                    ticker.dividend_yield = tradier_data["dividend_yield"]
                
                if tradier_data.get("beta") is not None:
                    ticker.beta = tradier_data["beta"]
                
                # Update name from Tradier if available
                if tradier_data.get("name") and not ticker.name:
                    ticker.name = tradier_data["name"]
            else:
                logger.warning(f"⚠️ No Tradier data received for {ticker.symbol}")
            
            # Get API Ninjas data (sector, industry, market cap, earnings)
            await self._enrich_with_api_ninjas_data(ticker)
            
            # Update or create TickerQuote for market data
            await self._update_ticker_quote(ticker.symbol, tradier_data)
            
            return ticker    
        except Exception as e:
            logger.error(f"❌ Error updating market data for {ticker.symbol}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            # Return the original ticker if update fails
            return ticker
    
    async def _enrich_with_api_ninjas_data(self, ticker: InterestingTicker) -> None:
        """Enrich ticker data with API Ninjas information."""
        try:
            symbol = ticker.symbol
            
            # Get company information (sector, industry, name)
            try:
                company_info = await self.api_ninjas.get_company_info(symbol)
                if company_info:
                    # Always update with fresh data, don't check if existing is None
                    if company_info.get('company_name'):
                        ticker.name = company_info['company_name']
                    
                    if company_info.get('sector'):
                        ticker.sector = company_info['sector']
                    
                    if company_info.get('sub_industry'):
                        ticker.industry = company_info['sub_industry']
                else:
                    logger.warning(f"⚠️ No company info returned for {symbol}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get API Ninjas company data for {symbol}: {e}")
            
            # Get market cap data
            try:
                market_cap_data = await self.api_ninjas.get_market_cap(symbol)
                if market_cap_data and market_cap_data.get("market_cap"):
                    ticker.market_cap = market_cap_data["market_cap"]
                    logger.info(f"✅ Updated market cap for {symbol}: ${ticker.market_cap:.1f}B")
                else:
                    logger.warning(f"⚠️ No market cap data available for {symbol} from API Ninjas")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get market cap data for {symbol}: {e}")
                import traceback
                logger.warning(f"📋 Market cap traceback: {traceback.format_exc()}")
            
            # Get earnings calendar data
            try:
                logger.info(f"📅 Getting earnings calendar for {symbol}...")
                earnings_data = await self.api_ninjas.get_earnings_calendar(symbol)
                if earnings_data and earnings_data.get("earnings_date"):
                    ticker.next_earnings_date = earnings_data["earnings_date"]
                    logger.info(f"✅ Updated earnings date for {symbol}: {earnings_data['earnings_date']}")
                else:
                    logger.warning(f"⚠️ No upcoming earnings found for {symbol}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get earnings data for {symbol}: {e}")
                import traceback
                logger.warning(f"📋 Earnings traceback: {traceback.format_exc()}")
                
        except Exception as e:
            logger.error(f"❌ Error enriching data with API Ninjas for {ticker.symbol}: {e}")
            import traceback
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
    
    async def _update_ticker_quote(self, symbol: str, tradier_data) -> None:
        """Update or create TickerQuote with frequently changing market data."""
        try:
            # Check if quote exists
            result = await self.db.execute(
                select(TickerQuote).where(TickerQuote.symbol == symbol)
            )
            quote = result.scalar_one_or_none()
            
            if not quote:
                # Create new quote
                quote = TickerQuote(
                    symbol=symbol,
                    updated_at=pacific_now()
                )
                self.db.add(quote)
                logger.info(f"Created new quote for {symbol}")
            else:
                quote.updated_at = pacific_now()
                logger.debug(f"Updated existing quote for {symbol}")
            
            # Update market data from Tradier
            if tradier_data:
                if tradier_data.get("current_price") is not None:
                    quote.current_price = tradier_data["current_price"]
                if tradier_data.get("volume_avg_20d") is not None:
                    quote.volume_avg_20d = tradier_data["volume_avg_20d"]
                if tradier_data.get("volatility_30d") is not None:
                    quote.volatility_30d = tradier_data["volatility_30d"]
            
            logger.info(f"Updated quote for {symbol}: price=${quote.current_price}, "
                       f"volume_avg_20d={quote.volume_avg_20d}, volatility_30d={quote.volatility_30d}")
            
        except Exception as e:
            logger.error(f"Error updating quote for {symbol}: {e}")
    
    async def _deactivate_old_tickers(self, current_symbols: List[str]) -> None:
        """Deactivate tickers no longer in the current universe."""
        try:
            current_symbols_set = set(current_symbols)
            
            # Find tickers not in current universe
            result = await self.db.execute(
                select(InterestingTicker).where(
                    and_(
                        InterestingTicker.active == True,
                        ~InterestingTicker.symbol.in_(current_symbols_set)
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
    
    async def refresh_market_data(self, max_tickers: int = None) -> List[InterestingTicker]:
        """Refresh market data for active tickers."""
        # Remove the artificial limit - refresh all tickers that need updating
        logger.info(f"Refreshing market data for all active tickers that need updating")
        
        # Get active tickers that need updating (older than 1 hour)
        cutoff_time = pacific_now() - timedelta(hours=1)
        result = await self.db.execute(
            select(InterestingTicker).where(
                and_(
                    InterestingTicker.active == True,
                    or_(
                        InterestingTicker.updated_at == None,
                        InterestingTicker.updated_at < cutoff_time
                    )
                )
            )
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
                select(func.count(InterestingTicker.id)).where(InterestingTicker.active == True)
            )
            total_tickers = result.scalar()
            
            # Get recently updated tickers
            result = await self.db.execute(
                select(func.count(InterestingTicker.id)).where(
                    InterestingTicker.updated_at >= pacific_now() - timedelta(hours=24)
                )
            )
            recent_updates = result.scalar()
            
            # Sector distribution
            result = await self.db.execute(
                select(InterestingTicker.sector, func.count(InterestingTicker.id)).where(
                    InterestingTicker.active == True
                ).group_by(InterestingTicker.sector)
            )
            sector_counts = result.all()
            
            return {
                "total_active_tickers": total_tickers,
                "recently_updated": recent_updates,
                "sector_distribution": dict(sector_counts),
                "last_update": pacific_now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {"error": str(e)}
    
    async def populate_sp500_fundamentals_and_earnings(self) -> Dict[str, Any]:
        """Populate SP500 fundamentals and earnings data weekly."""
        logger.info("Starting weekly SP500 fundamentals and earnings population...")
        
        try:
            # Get current SP500 constituents using API Ninjas
            sp500_symbols = await self.api_ninjas.get_sp500_tickers()
            
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
                    
                    # Check if ticker exists in interesting_tickers
                    result = await self.db.execute(
                        select(InterestingTicker).where(InterestingTicker.symbol == symbol)
                    )
                    ticker = result.scalar_one_or_none()
                    
                    if not ticker:
                        # Create new ticker if it doesn't exist
                        ticker = InterestingTicker(
                            symbol=symbol,
                            active=True,
                            source="sp500",
                            added_at=pacific_now(),
                            updated_at=pacific_now()
                        )
                        self.db.add(ticker)
                        logger.info(f"Created new ticker: {symbol}")
                    
                    # Update ticker fundamentals and market data
                    updated_ticker = await self._update_ticker_market_data(ticker)
                    
                    if updated_ticker:
                        successful_updates += 1
                        successful_tickers.append(symbol)
                        
                        # Get quote data for logging
                        quote_result = await self.db.execute(
                            select(TickerQuote).where(TickerQuote.symbol == symbol)
                        )
                        quote = quote_result.scalar_one_or_none()
                        
                        # Log additional data if available
                        data_log = f"✅ Successfully updated data for {symbol}"
                        if quote and quote.current_price:
                            data_log += f" (price: ${quote.current_price})"
                        if updated_ticker.sector:
                            data_log += f", sector: {updated_ticker.sector}"
                        if updated_ticker.market_cap:
                            data_log += f", market cap: ${updated_ticker.market_cap:.1f}B"
                        if updated_ticker.pe_ratio:
                            data_log += f", P/E: {updated_ticker.pe_ratio:.1f}"
                        if updated_ticker.next_earnings_date:
                            data_log += f", next earnings: {updated_ticker.next_earnings_date.strftime('%Y-%m-%d')}"
                        
                        logger.info(data_log)
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