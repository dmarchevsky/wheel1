"""Universe selection service for sophisticated ticker filtering and scoring."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, func, select
import numpy as np

from config import settings as env_settings
from services.settings_service import get_setting
from db.models import InterestingTicker, TickerQuote, Option, Trade
from services.market_data_service import MarketDataService
from utils.timezone import now_pacific

logger = logging.getLogger(__name__)


class UniverseService:
    """Service for sophisticated universe selection and scoring."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data_service = MarketDataService(db)
    
    async def get_filtered_universe(self, max_tickers: int = None, refresh_data: bool = True, fast_mode: bool = False) -> List[InterestingTicker]:
        """Get filtered universe of tickers for analysis."""
        logger.info(f"Selecting universe of all tickers that pass filters (fast_mode={fast_mode})")
        
        # Optionally refresh market data first (skip in fast mode)
        if refresh_data and not fast_mode:
            logger.info("Refreshing market data before universe selection")
            await self.refresh_universe_data(max_tickers)
        elif fast_mode:
            logger.info("Fast mode: skipping data refresh")
        
        # Get all active tickers
        result = await self.db.execute(
            select(InterestingTicker).where(InterestingTicker.active == True)
        )
        all_tickers = result.scalars().all()
        
        if not all_tickers:
            logger.warning("No active tickers found")
            return []
        
        logger.info(f"Processing {len(all_tickers)} active tickers for universe selection")
        
        # Apply filters and scoring
        filtered_tickers = []
        for ticker in all_tickers:
            try:
                # Apply filters (data should already be fresh from refresh_universe_data)
                if not await self._passes_basic_filters(ticker):
                    logger.debug(f"Ticker {ticker.symbol} failed basic filters")
                    continue
                
                if not await self._passes_options_filters(ticker):
                    logger.debug(f"Ticker {ticker.symbol} failed options filters")
                    continue
                
                if not await self._passes_earnings_filters(ticker):
                    logger.debug(f"Ticker {ticker.symbol} failed earnings filters")
                    continue
                
                # Calculate universe score
                universe_score = await self._calculate_universe_score(ticker)
                ticker.universe_score = universe_score
                ticker.last_analysis_date = now_pacific()
                
                filtered_tickers.append(ticker)
                logger.debug(f"Ticker {ticker.symbol} passed all filters with score {universe_score:.3f}")
                
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker.symbol}: {e}")
                continue
        
        # Sort by universe score and return all filtered tickers
        filtered_tickers.sort(key=lambda x: x.universe_score or 0, reverse=True)
        
        # Commit score updates
        await self.db.commit()
        
        # Return all filtered tickers without artificial limits
        logger.info(f"Selected {len(filtered_tickers)} tickers for analysis (all filtered tickers)")
        
        # Log top tickers for debugging
        if filtered_tickers:
            top_tickers = [(t.symbol, t.universe_score or 0) for t in filtered_tickers[:5]]
            logger.info(f"Top 5 tickers: {top_tickers}")
        
        return filtered_tickers
    
    async def refresh_universe_data(self, max_tickers: int = None) -> List[InterestingTicker]:
        """Refresh market data for the entire universe using MarketDataService."""
        logger.info(f"Refreshing universe data for all active tickers")
        
        try:
            # Use MarketDataService to refresh data for active tickers
            updated_tickers = await self.market_data_service.refresh_market_data(max_tickers)
            
            logger.info(f"Refreshed data for {len(updated_tickers)} tickers in universe")
            return updated_tickers
            
        except Exception as e:
            logger.error(f"Error refreshing universe data: {e}")
            return []
    
    async def _update_ticker_data(self, ticker: InterestingTicker) -> None:
        """Update ticker market data if stale using MarketDataService."""
        try:
            # Update if data is older than 1 hour
            if (ticker.updated_at is None or 
                now_pacific() - ticker.updated_at > timedelta(hours=1)):
                
                # Use MarketDataService to update both fundamental and quote data
                await self.market_data_service._update_ticker_market_data(ticker)
                logger.debug(f"Updated comprehensive data for {ticker.symbol}")
                
        except Exception as e:
            logger.warning(f"Failed to update data for {ticker.symbol}: {e}")
    
    async def _passes_basic_filters(self, ticker: InterestingTicker) -> bool:
        """Apply basic fundamental and technical filters (relaxed for development)."""
        
        # Get quote data for market data filters
        result = await self.db.execute(
            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
        )
        quote = result.scalar_one_or_none()
        
        # Price filter - avoid penny stocks and very expensive stocks (relaxed)
        if quote is None or quote.current_price is None or quote.current_price < 3.0 or quote.current_price > 1000.0:
            logger.debug(f"Ticker {ticker.symbol} failed price filter: price={quote.current_price if quote else None}")
            return False
        
        # Market cap filter - focus on mid to large cap (relaxed)
        if ticker.market_cap is None or ticker.market_cap < 0.5:  # Less than $500M (relaxed from $1B)
            logger.debug(f"Ticker {ticker.symbol} failed market cap filter: market_cap={ticker.market_cap}")
            return False
        
        # Volume filter - ensure sufficient liquidity (relaxed)
        if quote.volume_avg_20d is None or quote.volume_avg_20d < 100000:  # 100k shares/day (relaxed from 500k)
            logger.debug(f"Ticker {ticker.symbol} failed volume filter: volume={quote.volume_avg_20d}")
            return False
        
        # Volatility filter - avoid extremely volatile stocks (relaxed)
        # Note: volatility is stored as percentage (e.g., 50.0 = 50%), so compare with percentage value
        if quote.volatility_30d is not None and quote.volatility_30d > 120.0:  # >120% annualized (relaxed from 80%)
            logger.debug(f"Ticker {ticker.symbol} failed volatility filter: volatility={quote.volatility_30d}%")
            return False
        
        # Beta filter - avoid extremely high beta stocks (relaxed)
        if ticker.beta is not None and ticker.beta > 4.0:  # >4.0 (relaxed from 2.0)
            logger.debug(f"Ticker {ticker.symbol} failed beta filter: beta={ticker.beta}")
            return False
        
        # P/E filter - avoid extremely expensive stocks (relaxed)
        if ticker.pe_ratio is not None and ticker.pe_ratio > 200:  # >200 (relaxed from 50)
            logger.debug(f"Ticker {ticker.symbol} failed P/E filter: pe_ratio={ticker.pe_ratio}")
            return False
        
        logger.debug(f"Ticker {ticker.symbol} passed all basic filters")
        return True
    
    async def _passes_options_filters(self, ticker: InterestingTicker) -> bool:
        """Check if ticker has suitable options for cash-secured puts (relaxed for development)."""
        try:
            # For development, temporarily skip options filter to allow more tickers
            # TODO: Re-enable options filter when options data is populated
            logger.debug(f"Skipping options filter for {ticker.symbol} (development mode)")
            return True
            
            # Original options filter (commented out for development)
            # result = await self.db.execute(
            #     select(func.count(Option.id)).where(
            #         and_(
            #             Option.symbol == ticker.symbol,
            #             Option.option_type == "put"
            #         )
            #     )
            # )
            # options_count = result.scalar()
            # return options_count >= 1
            
        except Exception as e:
            logger.warning(f"Error checking options for {ticker.symbol}: {e}")
            return True  # Default to allowing in development
    
    async def _passes_earnings_filters(self, ticker: InterestingTicker) -> bool:
        """Check if ticker is not in earnings blackout period."""
        try:
            # Check for upcoming earnings using ticker's next_earnings_date
            if ticker.next_earnings_date is None:
                return True  # No earnings date, allow trading
            
            earnings_blackout_days = await get_setting(self.db, "earnings_blackout_days", 7)
            blackout_start = now_pacific() - timedelta(days=earnings_blackout_days)
            blackout_end = now_pacific() + timedelta(days=earnings_blackout_days)
            
            # Check if next earnings date is within blackout period
            if blackout_start <= ticker.next_earnings_date <= blackout_end:
                logger.debug(f"Ticker {ticker.symbol} in earnings blackout period: {ticker.next_earnings_date}")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking earnings for {ticker.symbol}: {e}")
            return True  # Default to allowing if we can't check
    
    async def _calculate_universe_score(self, ticker: InterestingTicker) -> float:
        """Calculate composite universe score for ticker."""
        score = 0.0
        weights = 0.0
        
        # Get quote data for market data scoring
        result = await self.db.execute(
            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
        )
        quote = result.scalar_one_or_none()
        
        # 1. Market Cap Score (25% weight) - prefer mid-cap to large-cap
        if ticker.market_cap is not None:
            if 5.0 <= ticker.market_cap <= 50.0:  # $5B-$50B mid-cap
                cap_score = 1.0
            elif 50.0 < ticker.market_cap <= 200.0:  # $50B-$200B large-cap
                cap_score = 0.9
            elif ticker.market_cap > 200.0:  # Mega-cap
                cap_score = 0.8
            else:  # Small-cap
                cap_score = 0.6
            
            score += cap_score * 0.25
            weights += 0.25
        
        # 2. Volume Score (20% weight) - prefer higher volume
        if quote and quote.volume_avg_20d is not None:
            volume_score = min(1.0, quote.volume_avg_20d / 2000000)  # Normalize to 2M shares
            score += volume_score * 0.20
            weights += 0.20
        
        # 3. Volatility Score (20% weight) - prefer moderate volatility
        if quote and quote.volatility_30d is not None:
            if 0.2 <= quote.volatility_30d <= 0.4:  # Sweet spot for options
                vol_score = 1.0
            elif 0.1 <= quote.volatility_30d < 0.2:
                vol_score = 0.7
            elif 0.4 < quote.volatility_30d <= 0.6:
                vol_score = 0.8
            else:
                vol_score = 0.3
            
            score += vol_score * 0.20
            weights += 0.20
        
        # 4. Beta Score (15% weight) - prefer moderate beta
        if ticker.beta is not None:
            if 0.8 <= ticker.beta <= 1.2:  # Market-like beta
                beta_score = 1.0
            elif 0.5 <= ticker.beta < 0.8:
                beta_score = 0.8
            elif 1.2 < ticker.beta <= 1.5:
                beta_score = 0.7
            else:
                beta_score = 0.4
            
            score += beta_score * 0.15
            weights += 0.15
        
        # 5. P/E Score (10% weight) - prefer reasonable valuations
        if ticker.pe_ratio is not None:
            if 10.0 <= ticker.pe_ratio <= 25.0:  # Reasonable P/E
                pe_score = 1.0
            elif 5.0 <= ticker.pe_ratio < 10.0:
                pe_score = 0.8
            elif 25.0 < ticker.pe_ratio <= 35.0:
                pe_score = 0.6
            else:
                pe_score = 0.3
            
            score += pe_score * 0.10
            weights += 0.10
        
        # 6. Dividend Score (10% weight) - bonus for dividend payers
        if ticker.dividend_yield is not None and ticker.dividend_yield > 0:
            div_score = min(1.0, ticker.dividend_yield / 3.0)  # Normalize to 3%
            score += div_score * 0.10
            weights += 0.10
        
        # Normalize by total weights
        if weights > 0:
            return score / weights
        else:
            return 0.0
    
    def get_sector_diversification(self, selected_tickers: List[InterestingTicker]) -> Dict[str, int]:
        """Get sector distribution of selected tickers."""
        sector_counts = {}
        for ticker in selected_tickers:
            sector = ticker.sector or "Unknown"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        return sector_counts
    
    async def get_universe_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the current universe."""
        try:
            # Get all active tickers
            result = await self.db.execute(
                select(InterestingTicker).where(InterestingTicker.active == True)
            )
            all_tickers = result.scalars().all()
            
            if not all_tickers:
                return {
                    "total_tickers": 0,
                    "data_completeness": {},
                    "sector_distribution": {},
                    "market_cap_distribution": {},
                    "average_scores": {},
                    "data_freshness": {}
                }
            
            # Data completeness statistics
            data_completeness = {
                "with_sector": sum(1 for t in all_tickers if t.sector),
                "with_industry": sum(1 for t in all_tickers if t.industry),
                "with_market_cap": sum(1 for t in all_tickers if t.market_cap),
                "with_pe_ratio": sum(1 for t in all_tickers if t.pe_ratio),
                "with_beta": sum(1 for t in all_tickers if t.beta),
                "with_earnings_date": sum(1 for t in all_tickers if t.next_earnings_date),
                "with_universe_score": sum(1 for t in all_tickers if t.universe_score),
            }
            
            # Sector distribution
            sector_dist = self.get_sector_diversification(all_tickers)
            
            # Market cap distribution
            market_cap_dist = {"small": 0, "mid": 0, "large": 0, "mega": 0}
            for ticker in all_tickers:
                if ticker.market_cap:
                    if ticker.market_cap < 5.0:
                        market_cap_dist["small"] += 1
                    elif ticker.market_cap < 50.0:
                        market_cap_dist["mid"] += 1
                    elif ticker.market_cap < 200.0:
                        market_cap_dist["large"] += 1
                    else:
                        market_cap_dist["mega"] += 1
            
            # Average scores
            scores_with_values = [t.universe_score for t in all_tickers if t.universe_score]
            average_scores = {
                "universe_score": sum(scores_with_values) / len(scores_with_values) if scores_with_values else 0,
                "pe_ratio": sum(t.pe_ratio for t in all_tickers if t.pe_ratio) / len([t for t in all_tickers if t.pe_ratio]) if any(t.pe_ratio for t in all_tickers) else 0,
                "beta": sum(t.beta for t in all_tickers if t.beta) / len([t for t in all_tickers if t.beta]) if any(t.beta for t in all_tickers) else 0,
            }
            
            # Data freshness
            now = now_pacific()
            recent_updates = sum(1 for t in all_tickers if t.updated_at and (now - t.updated_at) < timedelta(hours=1))
            data_freshness = {
                "updated_last_hour": recent_updates,
                "total_tickers": len(all_tickers),
                "freshness_percentage": (recent_updates / len(all_tickers)) * 100 if all_tickers else 0
            }
            
            return {
                "total_tickers": len(all_tickers),
                "data_completeness": data_completeness,
                "sector_distribution": sector_dist,
                "market_cap_distribution": market_cap_dist,
                "average_scores": average_scores,
                "data_freshness": data_freshness
            }
            
        except Exception as e:
            logger.error(f"Error getting universe statistics: {e}")
            return {}
    
    async def get_tickers_needing_updates(self, max_tickers: int = None) -> List[InterestingTicker]:
        """Get tickers that need market data updates."""
        try:
            # Get active tickers that need updating (older than 1 hour)
            cutoff_time = now_pacific() - timedelta(hours=1)
            query = select(InterestingTicker).where(
                and_(
                    InterestingTicker.active == True,
                    or_(
                        InterestingTicker.updated_at == None,
                        InterestingTicker.updated_at < cutoff_time
                    )
                )
            )
            
            # Apply limit if specified
            if max_tickers is not None:
                query = query.limit(max_tickers)
            
            result = await self.db.execute(query)
            tickers_needing_updates = result.scalars().all()
            
            logger.info(f"Found {len(tickers_needing_updates)} tickers needing updates")
            return tickers_needing_updates
            
        except Exception as e:
            logger.error(f"Error getting tickers needing updates: {e}")
            return []
    
    def optimize_for_diversification(self, tickers: List[InterestingTicker], max_tickers: int) -> List[InterestingTicker]:
        """Optimize selection for sector diversification."""
        if len(tickers) <= max_tickers:
            return tickers
        
        # Group by sector
        sector_groups = {}
        for ticker in tickers:
            sector = ticker.sector or "Unknown"
            if sector not in sector_groups:
                sector_groups[sector] = []
            sector_groups[sector].append(ticker)
        
        # Sort each sector by score
        for sector in sector_groups:
            sector_groups[sector].sort(key=lambda x: x.universe_score or 0, reverse=True)
        
        # Select tickers with diversification
        selected = []
        sector_indices = {sector: 0 for sector in sector_groups}
        
        while len(selected) < max_tickers:
            # Find sector with highest score ticker
            best_sector = None
            best_score = -1
            
            for sector, tickers_in_sector in sector_groups.items():
                if sector_indices[sector] < len(tickers_in_sector):
                    ticker = tickers_in_sector[sector_indices[sector]]
                    if (ticker.universe_score or 0) > best_score:
                        best_score = ticker.universe_score or 0
                        best_sector = sector
            
            if best_sector is None:
                break
            
            # Add ticker from best sector
            ticker = sector_groups[best_sector][sector_indices[best_sector]]
            selected.append(ticker)
            sector_indices[best_sector] += 1
        
        return selected
