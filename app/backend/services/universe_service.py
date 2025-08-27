"""Universe selection service for sophisticated ticker filtering and scoring."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, func, select
import numpy as np

from config import settings
from db.models import InterestingTicker, TickerQuote, Option, Trade
from clients.tradier import TradierDataManager

logger = logging.getLogger(__name__)


class UniverseService:
    """Service for sophisticated universe selection and scoring."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tradier_data = TradierDataManager(db)
    
    async def get_filtered_universe(self, max_tickers: int = None) -> List[InterestingTicker]:
        """Get filtered universe of tickers for analysis."""
        if max_tickers is None:
            max_tickers = settings.max_tickers_per_cycle
        
        logger.info(f"Selecting universe of up to {max_tickers} tickers")
        
        # Get all active tickers
        result = await self.db.execute(
            select(InterestingTicker).where(InterestingTicker.active == True)
        )
        all_tickers = result.scalars().all()
        
        if not all_tickers:
            logger.warning("No active tickers found")
            return []
        
        # Apply filters and scoring
        filtered_tickers = []
        for ticker in all_tickers:
            try:
                # Update ticker data if needed
                await self._update_ticker_data(ticker)
                
                # Apply filters
                if not await self._passes_basic_filters(ticker):
                    continue
                
                if not await self._passes_options_filters(ticker):
                    continue
                
                if not await self._passes_earnings_filters(ticker):
                    continue
                
                # Calculate universe score
                universe_score = await self._calculate_universe_score(ticker)
                ticker.universe_score = universe_score
                ticker.last_analysis_date = datetime.utcnow()
                
                filtered_tickers.append(ticker)
                
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker.symbol}: {e}")
                continue
        
        # Sort by universe score and return top tickers
        filtered_tickers.sort(key=lambda x: x.universe_score or 0, reverse=True)
        
        # Commit score updates
        await self.db.commit()
        
        selected_tickers = filtered_tickers[:max_tickers]
        logger.info(f"Selected {len(selected_tickers)} tickers for analysis")
        
        return selected_tickers
    
    async def _update_ticker_data(self, ticker: InterestingTicker) -> None:
        """Update ticker market data if stale."""
        try:
            # Update if data is older than 1 hour
            if (ticker.updated_at is None or 
                datetime.utcnow() - ticker.updated_at > timedelta(hours=1)):
                
                await self.tradier_data.sync_ticker_data(ticker.symbol)
                logger.debug(f"Updated data for {ticker.symbol}")
                
        except Exception as e:
            logger.warning(f"Failed to update data for {ticker.symbol}: {e}")
    
    async def _passes_basic_filters(self, ticker: InterestingTicker) -> bool:
        """Apply basic fundamental and technical filters."""
        
        # Get quote data for market data filters
        result = await self.db.execute(
            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
        )
        quote = result.scalar_one_or_none()
        
        # Price filter - avoid penny stocks and very expensive stocks
        if quote is None or quote.current_price is None or quote.current_price < 5.0 or quote.current_price > 500.0:
            return False
        
        # Market cap filter - focus on mid to large cap
        if ticker.market_cap is None or ticker.market_cap < 1.0:  # Less than $1B
            return False
        
        # Volume filter - ensure sufficient liquidity
        if quote.volume_avg_20d is None or quote.volume_avg_20d < 500000:  # 500k shares/day
            return False
        
        # Volatility filter - avoid extremely volatile stocks
        if quote.volatility_30d is not None and quote.volatility_30d > 0.8:  # >80% annualized
            return False
        
        # Beta filter - avoid extremely high beta stocks
        if ticker.beta is not None and ticker.beta > 2.0:
            return False
        
        # P/E filter - avoid extremely expensive stocks
        if ticker.pe_ratio is not None and ticker.pe_ratio > 50:
            return False
        
        return True
    
    async def _passes_options_filters(self, ticker: InterestingTicker) -> bool:
        """Check if ticker has suitable options for cash-secured puts."""
        try:
            # Check if we have any options data (relaxed filter for development)
            result = await self.db.execute(
                select(func.count(Option.id)).where(
                    and_(
                        Option.symbol == ticker.symbol,
                        Option.option_type == "put"
                        # Temporarily removed strict filters for development
                        # Option.dte >= 30,
                        # Option.dte <= 60,
                        # Option.delta >= settings.put_delta_min,
                        # Option.delta <= settings.put_delta_max,
                        # Option.open_interest >= settings.min_oi,
                        # Option.volume >= settings.min_volume
                    )
                )
            )
            options_count = result.scalar()
            
            # Need at least 1 option (relaxed from 3 for development)
            return options_count >= 1
            
        except Exception as e:
            logger.warning(f"Error checking options for {ticker.symbol}: {e}")
            return False
    
    async def _passes_earnings_filters(self, ticker: InterestingTicker) -> bool:
        """Check if ticker is not in earnings blackout period."""
        try:
            # Check for upcoming earnings using ticker's next_earnings_date
            if ticker.next_earnings_date is None:
                return True  # No earnings date, allow trading
            
            blackout_start = datetime.utcnow() - timedelta(days=settings.earnings_blackout_days)
            blackout_end = datetime.utcnow() + timedelta(days=settings.earnings_blackout_days)
            
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
