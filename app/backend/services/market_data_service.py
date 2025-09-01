from utils.timezone import pacific_now
"""Market data service for dynamic ticker management and S&P 500 universe selection."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select

from config import settings
from db.models import InterestingTicker, TickerQuote, Option
from clients.tradier import TradierDataManager
from clients.api_ninjas import APINinjasClient
from clients.fmp_api import FMPAPIClient
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing dynamic ticker universe and market data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tradier_data = TradierDataManager(db)
        self.api_ninjas = APINinjasClient()
        self.fmp_api = FMPAPIClient()
    
    async def update_sp500_universe(self) -> List[InterestingTicker]:
        """Update the ticker universe with current S&P 500 constituents."""
        logger.info("🔄 Updating S&P 500 universe...")
        
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
            
            logger.info(f"Successfully updated {len(updated_tickers)} S&P 500 tickers")
            return updated_tickers
            
        except Exception as e:
            logger.error(f"Error updating S&P 500 universe: {e}")
            return []
    
    async def update_all_fundamentals(self) -> Dict[str, Any]:
        """Update fundamentals for all interesting_tickers using FMP API and API Ninjas."""
        logger.info("🔄 Updating fundamentals for all interesting tickers...")
        
        try:
            # Get all active tickers
            result = await self.db.execute(
                select(InterestingTicker).where(InterestingTicker.active == True)
            )
            all_tickers = result.scalars().all()
            
            if not all_tickers:
                logger.warning("No active tickers found")
                return {"success": False, "message": "No active tickers found"}
            
            logger.info(f"Updating fundamentals for {len(all_tickers)} tickers")
            
            successful_updates = 0
            failed_updates = 0
            updated_tickers = []
            
            for i, ticker in enumerate(all_tickers):
                try:
                    logger.info(f"Processing fundamentals for {i+1}/{len(all_tickers)}: {ticker.symbol}")
                    
                    # Update fundamentals
                    updated_ticker = await self._update_ticker_fundamentals(ticker)
                    if updated_ticker:
                        successful_updates += 1
                        updated_tickers.append(ticker.symbol)
                        logger.info(f"✅ Updated fundamentals for {ticker.symbol}")
                    else:
                        failed_updates += 1
                        logger.warning(f"❌ Failed to update fundamentals for {ticker.symbol}")
                    
                    # Rate limiting
                    if (i + 1) % 5 == 0:
                        logger.info(f"Processed {i + 1}/{len(all_tickers)} tickers, pausing...")
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    failed_updates += 1
                    logger.error(f"Error updating fundamentals for {ticker.symbol}: {e}")
                    continue
            
            # Commit all changes
            await self.db.commit()
            
            success_rate = (successful_updates / len(all_tickers)) * 100 if all_tickers else 0
            
            result = {
                "success": True,
                "total_processed": len(all_tickers),
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "success_rate": success_rate,
                "updated_tickers": updated_tickers,
                "timestamp": pacific_now().isoformat()
            }
            
            logger.info(f"Fundamentals update completed: {successful_updates}/{len(all_tickers)} successful ({success_rate:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error updating all fundamentals: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def _update_ticker_fundamentals(self, ticker: InterestingTicker) -> Optional[InterestingTicker]:
        """Update ticker fundamentals using FMP API and API Ninjas."""
        try:
            symbol = ticker.symbol
            
            # 1. Update company info using FMP API (comprehensive data)
            logger.info(f"📊 Fetching company profile from FMP API for {symbol}")
            fmp_profile = await self.fmp_api.get_company_profile(symbol)
            
            if fmp_profile:
                # Update company name, sector, industry
                if not ticker.name and fmp_profile.get("name"):
                    ticker.name = fmp_profile["name"]
                    logger.info(f"✅ Updated name for {symbol}: {ticker.name}")
                
                if not ticker.sector and fmp_profile.get("sector"):
                    ticker.sector = fmp_profile["sector"]
                    logger.info(f"✅ Updated sector for {symbol}: {ticker.sector}")
                
                if not ticker.industry and fmp_profile.get("industry"):
                    ticker.industry = fmp_profile["industry"]
                    logger.info(f"✅ Updated industry for {symbol}: {ticker.industry}")
                
                # Update market cap from FMP (more reliable than API Ninjas)
                if fmp_profile.get("market_cap"):
                    # Convert to billions if needed
                    market_cap = fmp_profile["market_cap"]
                    if market_cap and market_cap > 0:
                        ticker.market_cap = market_cap / 1000000000  # Convert to billions
                        logger.info(f"✅ Updated market cap for {symbol}: ${ticker.market_cap:.1f}B")
                
                # Update beta from FMP
                if fmp_profile.get("beta") is not None:
                    ticker.beta = fmp_profile["beta"]
                    logger.info(f"✅ Updated beta for {symbol}: {ticker.beta}")
                
                # Update P/E ratio from FMP
                if fmp_profile.get("pe_ratio") is not None:
                    ticker.pe_ratio = fmp_profile["pe_ratio"]
                    logger.info(f"✅ Updated P/E ratio for {symbol}: {ticker.pe_ratio}")
                
                # Update dividend yield from FMP
                if fmp_profile.get("dividend_yield") is not None:
                    ticker.dividend_yield = fmp_profile["dividend_yield"]
                    logger.info(f"✅ Updated dividend yield for {symbol}: {ticker.dividend_yield}")
                
                logger.info(f"✅ Updated FMP profile data for {symbol}")
            else:
                logger.warning(f"⚠️ No FMP profile data for {symbol}")
            
            # 2. Update earnings dates using API Ninjas (keep as fallback)
            logger.info(f"📅 Fetching earnings data for {symbol}")
            earnings_data = await self.api_ninjas.get_earnings_calendar(symbol)
            if earnings_data and earnings_data.get("earnings_date"):
                ticker.next_earnings_date = earnings_data["earnings_date"]
                logger.info(f"✅ Updated earnings date for {symbol}: {earnings_data['earnings_date']}")
            else:
                logger.warning(f"⚠️ No earnings data for {symbol}")
            
            # 3. Fallback to API Ninjas for market cap if FMP didn't provide it
            if not ticker.market_cap:
                logger.info(f"💰 Fetching market cap from API Ninjas for {symbol}")
                market_cap_data = await self.api_ninjas.get_market_cap(symbol)
                if market_cap_data and market_cap_data.get("market_cap"):
                    ticker.market_cap = market_cap_data["market_cap"]
                    logger.info(f"✅ Updated market cap from API Ninjas for {symbol}: ${ticker.market_cap:.1f}B")
                else:
                    logger.warning(f"⚠️ No market cap data available for {symbol}")
            
            # 4. Fallback to Tradier for fundamentals if FMP didn't provide them
            if not ticker.pe_ratio or not ticker.beta or not ticker.dividend_yield:
                logger.info(f"📈 Fetching additional fundamentals from Tradier for {symbol}")
                tradier_data = await self.tradier_data.sync_ticker_data(symbol)
                if tradier_data:
                    if not ticker.pe_ratio and tradier_data.get("pe_ratio") is not None:
                        ticker.pe_ratio = tradier_data["pe_ratio"]
                    
                    if not ticker.dividend_yield and tradier_data.get("dividend_yield") is not None:
                        ticker.dividend_yield = tradier_data["dividend_yield"]
                    
                    if not ticker.beta and tradier_data.get("beta") is not None:
                        ticker.beta = tradier_data["beta"]
                    
                    logger.info(f"✅ Updated Tradier fundamentals for {symbol}")
                else:
                    logger.warning(f"⚠️ No Tradier data for {symbol}")
            
            # Update timestamp
            ticker.updated_at = pacific_now()
            
            return ticker
            
        except Exception as e:
            logger.error(f"Error updating fundamentals for {ticker.symbol}: {e}")
            return None
            
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
    
    async def _calculate_universe_score(self, ticker: InterestingTicker) -> float:
        """Calculate universe score specifically optimized for Wheel Strategy."""
        try:
            score = 0.0
            
            # Get quote data
            result = await self.db.execute(
                select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
            )
            quote = result.scalar_one_or_none()
            
            # =============================================================================
            # WHEEL STRATEGY OPTIMIZED SCORING
            # =============================================================================
            
            # 1. OPTIONS SUITABILITY (40% of total score)
            options_score = await self._calculate_options_suitability_score(ticker, quote)
            score += options_score * 0.4
            
            # 2. TECHNICAL SETUP (25% of total score)
            technical_score = await self._calculate_technical_setup_score(ticker, quote)
            score += technical_score * 0.25
            
            # 3. FUNDAMENTAL QUALITY (20% of total score)
            fundamental_score = await self._calculate_fundamental_quality_score(ticker)
            score += fundamental_score * 0.20
            
            # 4. RISK ASSESSMENT (15% of total score)
            risk_score = await self._calculate_risk_assessment_score(ticker, quote)
            score += risk_score * 0.15
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Error calculating wheel strategy score for {ticker.symbol}: {e}")
            return 0.0
    
    async def _calculate_options_suitability_score(self, ticker: InterestingTicker, quote: TickerQuote) -> float:
        """Calculate options suitability score for wheel strategy."""
        try:
            score = 0.0
            
            # Check if we have recent options data
            result = await self.db.execute(
                select(Option).where(
                    and_(
                        Option.underlying_symbol == ticker.symbol,
                        Option.option_type == "put",
                        Option.updated_at >= pacific_now() - timedelta(hours=24)
                    )
                )
            )
            recent_options = result.scalars().all()
            
            if recent_options:
                # Calculate average metrics from recent options
                total_oi = sum(opt.open_interest or 0 for opt in recent_options)
                total_volume = sum(opt.volume or 0 for opt in recent_options)
                avg_iv = sum(opt.implied_volatility or 0 for opt in recent_options) / len(recent_options)
                
                # Options liquidity score (0.0 - 0.4)
                if total_oi > 10000:  # High liquidity
                    score += 0.4
                elif total_oi > 5000:  # Good liquidity
                    score += 0.3
                elif total_oi > 2000:  # Moderate liquidity
                    score += 0.2
                elif total_oi > 500:  # Minimum liquidity
                    score += 0.1
                
                # Volume activity score (0.0 - 0.3)
                if total_volume > 5000:
                    score += 0.3
                elif total_volume > 2000:
                    score += 0.2
                elif total_volume > 500:
                    score += 0.1
                
                # Implied volatility score (0.0 - 0.3)
                if 0.2 <= avg_iv <= 0.6:  # Sweet spot for premium selling
                    score += 0.3
                elif 0.1 <= avg_iv <= 0.8:  # Acceptable range
                    score += 0.2
                elif avg_iv > 0.8:  # High IV (good for premium, but higher risk)
                    score += 0.1
            else:
                # No recent options data - estimate based on market cap and volume
                if ticker.market_cap and ticker.market_cap > 10:  # > $10B
                    score += 0.2  # Large caps typically have good options
                if quote and quote.volume_avg_20d and quote.volume_avg_20d > 5000000:
                    score += 0.1  # High volume suggests options activity
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating options suitability for {ticker.symbol}: {e}")
            return 0.0
    
    async def _calculate_technical_setup_score(self, ticker: InterestingTicker, quote: TickerQuote) -> float:
        """Calculate technical setup score for wheel strategy."""
        try:
            score = 0.0
            
            if not quote or not quote.current_price:
                return 0.0
            
            current_price = quote.current_price
            
            # Get historical price data for technical analysis
            # For now, we'll use a simplified approach based on available data
            # In production, you'd want to fetch historical prices from FMP or another source
            
            # Price stability score (0.0 - 0.3)
            if quote.volatility_30d:
                if 0.15 <= quote.volatility_30d <= 0.35:  # Sweet spot for wheel strategy
                    score += 0.3
                elif 0.1 <= quote.volatility_30d <= 0.5:  # Acceptable range
                    score += 0.2
                elif quote.volatility_30d < 0.1:  # Too stable (low premiums)
                    score += 0.1
                elif quote.volatility_30d > 0.5:  # Too volatile (high risk)
                    score += 0.1
            
            # Support level proximity score (0.0 - 0.4)
            # For wheel strategy, we want stocks near support for put selling
            if ticker.market_cap:
                # Estimate support levels based on market cap and current price
                # Large caps: 10-15% below current price
                # Mid caps: 15-20% below current price
                if ticker.market_cap > 50:  # Large cap
                    support_distance = 0.12  # 12% below current
                elif ticker.market_cap > 10:  # Mid cap
                    support_distance = 0.18  # 18% below current
                else:  # Small cap
                    support_distance = 0.25  # 25% below current
                
                # Higher score for stocks closer to support
                score += 0.4 * (1.0 - support_distance)
            
            # Trend strength score (0.0 - 0.3)
            # For wheel strategy, we prefer stocks in sideways or slightly bullish trends
            if quote.volume_avg_20d and quote.volume_avg_20d > 1000000:
                score += 0.3  # Good volume suggests healthy trading activity
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating technical setup for {ticker.symbol}: {e}")
            return 0.0
    
    async def _calculate_fundamental_quality_score(self, ticker: InterestingTicker) -> float:
        """Calculate fundamental quality score for wheel strategy."""
        try:
            score = 0.0
            
            # Company size and stability (0.0 - 0.4)
            if ticker.market_cap:
                if ticker.market_cap > 100:  # > $100B - Very stable
                    score += 0.4
                elif ticker.market_cap > 50:  # > $50B - Stable
                    score += 0.35
                elif ticker.market_cap > 20:  # > $20B - Good
                    score += 0.3
                elif ticker.market_cap > 10:  # > $10B - Acceptable
                    score += 0.25
                elif ticker.market_cap > 5:  # > $5B - Minimum for wheel
                    score += 0.2
            
            # Valuation quality (0.0 - 0.3)
            if ticker.pe_ratio:
                if 8 <= ticker.pe_ratio <= 30:  # Reasonable valuation
                    score += 0.3
                elif 5 <= ticker.pe_ratio <= 40:  # Acceptable range
                    score += 0.2
                elif ticker.pe_ratio < 5:  # Very cheap (potential value trap)
                    score += 0.1
                elif ticker.pe_ratio > 40:  # Expensive (higher risk)
                    score += 0.1
            
            # Financial health (0.0 - 0.3)
            if ticker.beta:
                if 0.6 <= ticker.beta <= 1.4:  # Moderate volatility
                    score += 0.3
                elif 0.4 <= ticker.beta <= 1.6:  # Acceptable range
                    score += 0.2
                elif ticker.beta < 0.4:  # Too stable (low premiums)
                    score += 0.1
                elif ticker.beta > 1.6:  # Too volatile (high risk)
                    score += 0.1
            
            # Dividend stability (0.0 - 0.1)
            if ticker.dividend_yield and ticker.dividend_yield > 0:
                score += 0.1  # Dividend-paying stocks are generally more stable
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating fundamental quality for {ticker.symbol}: {e}")
            return 0.0
    
    async def _calculate_risk_assessment_score(self, ticker: InterestingTicker, quote: TickerQuote) -> float:
        """Calculate risk assessment score for wheel strategy."""
        try:
            score = 0.0
            
            # Earnings blackout risk (0.0 - 0.4)
            if ticker.next_earnings_date:
                days_to_earnings = (ticker.next_earnings_date - pacific_now()).days
                if days_to_earnings > 30:  # Far from earnings (low risk)
                    score += 0.4
                elif days_to_earnings > 14:  # Moderate distance (medium risk)
                    score += 0.3
                elif days_to_earnings > 7:  # Close to earnings (higher risk)
                    score += 0.2
                elif days_to_earnings > 0:  # Very close to earnings (high risk)
                    score += 0.1
                else:  # Earnings today or passed (medium risk)
                    score += 0.2
            else:
                # No earnings date - assume low risk
                score += 0.3
            
            # Sector risk assessment (0.0 - 0.3)
            if ticker.sector:
                low_risk_sectors = ["Consumer Staples", "Utilities", "Healthcare", "Real Estate"]
                medium_risk_sectors = ["Consumer Discretionary", "Industrials", "Materials", "Communication Services"]
                high_risk_sectors = ["Technology", "Energy", "Financial Services"]
                
                if ticker.sector in low_risk_sectors:
                    score += 0.3
                elif ticker.sector in medium_risk_sectors:
                    score += 0.2
                elif ticker.sector in high_risk_sectors:
                    score += 0.1
                else:
                    score += 0.2  # Unknown sector
            
            # Market cap stability (0.0 - 0.3)
            if ticker.market_cap:
                if ticker.market_cap > 100:  # Very stable
                    score += 0.3
                elif ticker.market_cap > 50:  # Stable
                    score += 0.25
                elif ticker.market_cap > 20:  # Good
                    score += 0.2
                elif ticker.market_cap > 10:  # Acceptable
                    score += 0.15
                elif ticker.market_cap > 5:  # Higher risk
                    score += 0.1
                else:  # High risk
                    score += 0.05
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk assessment for {ticker.symbol}: {e}")
            return 0.0
    
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
            
            # Calculate and update put/call ratio
            put_call_ratio = await self._calculate_put_call_ratio(symbol)
            if put_call_ratio is not None:
                quote.put_call_ratio = put_call_ratio
                logger.debug(f"Updated put/call ratio for {symbol}: {put_call_ratio:.3f}")
            
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
    
    # =============================================================================
    # 2. UNIVERSE SCORING (Daily) - WHEEL STRATEGY OPTIMIZED
    # =============================================================================
    
    async def calculate_universe_scores(self) -> Dict[str, Any]:
        """Calculate universe scores for all interesting_tickers daily."""
        logger.info("🔄 Calculating wheel strategy universe scores for all tickers...")
        
        try:
            # Get all active tickers
            result = await self.db.execute(
                select(InterestingTicker).where(InterestingTicker.active == True)
            )
            all_tickers = result.scalars().all()
            
            if not all_tickers:
                logger.warning("No active tickers found for scoring")
                return {"success": False, "message": "No active tickers found"}
            
            logger.info(f"Calculating wheel strategy scores for {len(all_tickers)} tickers")
            
            scored_tickers = 0
            failed_scoring = 0
            
            for ticker in all_tickers:
                try:
                    # Calculate wheel strategy universe score
                    score = await self._calculate_universe_score(ticker)
                    ticker.universe_score = score
                    ticker.last_analysis_date = pacific_now()
                    scored_tickers += 1
                    
                    logger.debug(f"✅ Scored {ticker.symbol}: {score:.3f}")
                    
                except Exception as e:
                    failed_scoring += 1
                    logger.error(f"Error scoring {ticker.symbol}: {e}")
                    continue
            
            # Commit score updates
            await self.db.commit()
            
            result = {
                "success": True,
                "total_tickers": len(all_tickers),
                "scored_tickers": scored_tickers,
                "failed_scoring": failed_scoring,
                "timestamp": pacific_now().isoformat()
            }
            
            logger.info(f"Wheel strategy universe scoring completed: {scored_tickers}/{len(all_tickers)} tickers scored")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating wheel strategy universe scores: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    # =============================================================================
    # 3. RECOMMENDATIONS (Top 20 SP500 + Manual tickers)
    # =============================================================================
    
    async def update_recommendation_tickers(self) -> Dict[str, Any]:
        """Update ticker quotes and option chains for top 20 SP500 and manual tickers."""
        logger.info("🔄 Updating recommendation tickers (top 20 SP500 + manual)...")
        
        try:
            # Get top 20 SP500 tickers by universe score
            result = await self.db.execute(
                select(InterestingTicker)
                .where(InterestingTicker.active == True, InterestingTicker.source == "sp500")
                .order_by(InterestingTicker.universe_score.desc().nullslast())
                .limit(20)
            )
            top_sp500_tickers = result.scalars().all()
            
            # Get all manual tickers
            result = await self.db.execute(
                select(InterestingTicker)
                .where(InterestingTicker.active == True, InterestingTicker.source == "manual")
            )
            manual_tickers = result.scalars().all()
            
            # Combine tickers for processing
            recommendation_tickers = top_sp500_tickers + manual_tickers
            
            if not recommendation_tickers:
                logger.warning("No tickers found for recommendation updates")
                return {"success": False, "message": "No tickers found"}
            
            logger.info(f"Updating {len(recommendation_tickers)} recommendation tickers "
                       f"({len(top_sp500_tickers)} top SP500 + {len(manual_tickers)} manual)")
            
            updated_quotes = 0
            updated_options = 0
            failed_updates = 0
            
            for ticker in recommendation_tickers:
                try:
                    logger.info(f"Processing recommendation ticker: {ticker.symbol}")
                    
                    # Update ticker quote
                    quote_updated = await self._update_ticker_quote_for_recommendations(ticker.symbol)
                    if quote_updated:
                        updated_quotes += 1
                    
                    # Update option chain
                    options_updated = await self._update_option_chain(ticker.symbol)
                    if options_updated:
                        updated_options += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    failed_updates += 1
                    logger.error(f"Error updating recommendation data for {ticker.symbol}: {e}")
                    continue
            
            # Commit all changes
            await self.db.commit()
            
            result = {
                "success": True,
                "total_tickers": len(recommendation_tickers),
                "updated_quotes": updated_quotes,
                "updated_options": updated_options,
                "failed_updates": failed_updates,
                "timestamp": pacific_now().isoformat()
            }
            
            logger.info(f"Recommendation updates completed: "
                       f"{updated_quotes} quotes, {updated_options} option chains updated")
            return result
            
        except Exception as e:
            logger.error(f"Error updating recommendation tickers: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def _calculate_put_call_ratio(self, symbol: str) -> Optional[float]:
        """Calculate put/call ratio from options data."""
        try:
            # Get recent options data (last 24 hours)
            result = await self.db.execute(
                select(Option).where(
                    and_(
                        Option.underlying_symbol == symbol,
                        Option.updated_at >= pacific_now() - timedelta(hours=24)
                    )
                )
            )
            options = result.scalars().all()
            
            if not options:
                logger.debug(f"No recent options data for {symbol} to calculate put/call ratio")
                return None
            
            # Calculate put/call ratio
            put_volume = sum(opt.volume or 0 for opt in options if opt.option_type == "put")
            call_volume = sum(opt.volume or 0 for opt in options if opt.option_type == "call")
            
            if call_volume == 0:
                if put_volume == 0:
                    return None  # No volume data
                return float('inf')  # All puts, no calls
            
            put_call_ratio = put_volume / call_volume
            logger.debug(f"Calculated put/call ratio for {symbol}: {put_call_ratio:.3f} (put_vol: {put_volume}, call_vol: {call_volume})")
            return put_call_ratio
            
        except Exception as e:
            logger.error(f"Error calculating put/call ratio for {symbol}: {e}")
            return None

    async def _update_ticker_quote_for_recommendations(self, symbol: str) -> bool:
        """Update ticker quote with fresh market data for recommendations."""
        try:
            # Try FMP API first for comprehensive quote data
            fmp_quote = await self.fmp_api.get_company_quote(symbol)
            
            # Fallback to Tradier if FMP fails
            tradier_data = None
            if not fmp_quote:
                logger.info(f"FMP quote failed for {symbol}, falling back to Tradier...")
                tradier_data = await self.tradier_data.sync_ticker_data(symbol)
            
            if not fmp_quote and not tradier_data:
                logger.warning(f"No quote data available for {symbol}")
                return False
            
            # Update or create quote
            result = await self.db.execute(
                select(TickerQuote).where(TickerQuote.symbol == symbol)
            )
            quote = result.scalar_one_or_none()
            
            if not quote:
                quote = TickerQuote(
                    symbol=symbol,
                    updated_at=pacific_now()
                )
                self.db.add(quote)
            
            # Update with FMP data (preferred) or Tradier fallback
            if fmp_quote:
                if fmp_quote.get("current_price") is not None:
                    quote.current_price = fmp_quote["current_price"]
                if fmp_quote.get("avg_volume") is not None:
                    quote.volume_avg_20d = fmp_quote["avg_volume"]
                # Note: FMP doesn't provide volatility, so we'll keep existing or use Tradier
                
                logger.info(f"✅ Updated quote from FMP for {symbol}: ${quote.current_price}")
            else:
                # Use Tradier data
                if tradier_data.get("current_price") is not None:
                    quote.current_price = tradier_data["current_price"]
                if tradier_data.get("volume_avg_20d") is not None:
                    quote.volume_avg_20d = tradier_data["volume_avg_20d"]
                if tradier_data.get("volatility_30d") is not None:
                    quote.volatility_30d = tradier_data["volatility_30d"]
                
                logger.info(f"✅ Updated quote from Tradier for {symbol}: ${quote.current_price}")
            
            # Calculate and update put/call ratio
            put_call_ratio = await self._calculate_put_call_ratio(symbol)
            if put_call_ratio is not None:
                quote.put_call_ratio = put_call_ratio
                logger.info(f"✅ Updated put/call ratio for {symbol}: {put_call_ratio:.3f}")
            
            quote.updated_at = pacific_now()
            return True
            
        except Exception as e:
            logger.error(f"Error updating quote for {symbol}: {e}")
            return False
    
    async def _update_option_chain(self, symbol: str) -> bool:
        """Update option chain for a ticker."""
        try:
            # Use TradierDataManager to sync options
            options_data = await self.tradier_data.sync_options_data(symbol)
            
            if options_data:
                logger.info(f"✅ Updated option chain for {symbol}: {len(options_data)} options")
                return True
            else:
                logger.warning(f"No options data for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating options for {symbol}: {e}")
            return False
    
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
                        data_log = f"Successfully updated data for {symbol}"
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
                        logger.warning(f"Failed to update data for {symbol}")
                    
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
            
            logger.info(f"Weekly SP500 population completed: {successful_updates}/{len(sp500_symbols)} successful updates")
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
