"""Scoring algorithms for Wheel Strategy recommendations."""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import Option, Ticker, EarningsCalendar
from config import settings


class ScoringEngine:
    """Engine for scoring cash-secured put opportunities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def calculate_annualized_yield(self, premium: float, strike: float, dte: int) -> float:
        """Calculate annualized yield for cash-secured put."""
        if dte <= 0 or strike <= 0:
            return 0.0
        
        # Annualized yield = (premium / (strike * 100)) / (DTE/365)
        annualized_yield = (premium / (strike * 100)) / (dte / 365) * 100
        return annualized_yield
    
    def calculate_bid_ask_spread_pct(self, bid: float, ask: float) -> float:
        """Calculate bid-ask spread as percentage of mid price."""
        if bid <= 0 or ask <= 0 or bid >= ask:
            return float('inf')
        
        mid_price = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid_price) * 100
        return spread_pct
    
    def calculate_iv_rank(self, current_iv: float, historical_ivs: List[float]) -> float:
        """Calculate IV Rank (percentile of current IV vs historical)."""
        if not historical_ivs or current_iv <= 0:
            return 50.0  # Default to middle rank
        
        # Calculate percentile
        rank = (sum(1 for iv in historical_ivs if iv < current_iv) / len(historical_ivs)) * 100
        return rank
    
    def calculate_proximity_to_support(self, current_price: float, strike: float, 
                                     ma_50: float = None, ma_200: float = None) -> float:
        """Calculate proximity to support levels."""
        if current_price <= 0 or strike <= 0:
            return 0.0
        
        # Base score on strike vs current price
        price_ratio = strike / current_price
        
        # Penalize if strike is too far below current price (>10% discount)
        if price_ratio < 0.9:
            return 0.0
        
        # Reward if strike is near current price (0.95-1.05 range)
        if 0.95 <= price_ratio <= 1.05:
            base_score = 1.0
        else:
            # Linear decay outside optimal range
            base_score = max(0.0, 1.0 - abs(price_ratio - 1.0) * 10)
        
        # Adjust based on moving averages if available
        if ma_50 and ma_200:
            # Penalize if current price is well below 200DMA
            if current_price < ma_200 * 0.8:
                base_score *= 0.5
            
            # Reward if strike is above 50DMA
            if strike > ma_50:
                base_score *= 1.2
        
        return min(1.0, base_score)
    
    def calculate_liquidity_score(self, oi: int, volume: int, spread_pct: float) -> float:
        """Calculate liquidity score based on OI, volume, and spread."""
        if oi <= 0 or volume <= 0:
            return 0.0
        
        # Normalize OI and volume (assuming good liquidity starts at 500 OI, 200 volume)
        oi_score = min(1.0, oi / 1000)
        volume_score = min(1.0, volume / 500)
        
        # Spread score (inverse - lower spread is better)
        spread_score = max(0.0, 1.0 - (spread_pct / 10))  # 10% spread = 0 score
        
        # Combine scores with weights
        liquidity_score = (0.4 * oi_score + 0.4 * volume_score + 0.2 * spread_score)
        return liquidity_score
    
    def calculate_risk_adjustment(self, symbol: str, earnings_date: Optional[datetime] = None,
                                sector: str = None) -> float:
        """Calculate risk adjustment factor."""
        risk_score = 1.0
        
        # Earnings blackout penalty
        if earnings_date:
            days_to_earnings = (earnings_date - datetime.utcnow()).days
            if 0 <= days_to_earnings <= settings.earnings_blackout_days:
                risk_score *= 0.3  # Significant penalty during earnings blackout
        
        # Sector risk adjustments (simplified)
        high_risk_sectors = ['biotech', 'energy', 'financials']
        if sector and sector.lower() in high_risk_sectors:
            risk_score *= 0.8
        
        return risk_score
    
    def calculate_qualitative_score(self, gpt_score: float) -> float:
        """Convert ChatGPT qualitative score to normalized score."""
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, gpt_score))
    
    def calculate_composite_score(self, annualized_yield: float, proximity_score: float,
                                liquidity_score: float, risk_adjustment: float,
                                qualitative_score: float) -> float:
        """Calculate composite score using weighted components."""
        # Normalize annualized yield (assume 20%+ is excellent)
        normalized_yield = min(1.0, annualized_yield / 20.0)
        
        # Weighted composite score
        composite_score = (
            0.35 * normalized_yield +
            0.20 * proximity_score +
            0.15 * liquidity_score +
            0.15 * risk_adjustment +
            0.15 * qualitative_score
        )
        
        return composite_score
    
    def score_option(self, option: Option, current_price: float, 
                    gpt_analysis: Dict = None) -> Dict[str, float]:
        """Score a single option contract."""
        # Basic calculations
        dte = (option.expiry - datetime.utcnow()).days
        if dte <= 0:
            return {"score": 0.0, "rationale": {}}
        
        # Get mid price
        if option.bid and option.ask:
            mid_price = (option.bid + option.ask) / 2
            spread_pct = self.calculate_bid_ask_spread_pct(option.bid, option.ask)
        else:
            mid_price = option.last or 0
            spread_pct = float('inf')
        
        # Calculate components
        annualized_yield = self.calculate_annualized_yield(mid_price, option.strike, dte)
        proximity_score = self.calculate_proximity_to_support(current_price, option.strike)
        liquidity_score = self.calculate_liquidity_score(
            option.open_interest or 0, 
            option.volume or 0, 
            spread_pct
        )
        
        # Risk adjustment
        # Note: These queries would need to be async, but for now we'll use default values
        # ticker = await self.db.execute(select(Ticker).where(Ticker.symbol == option.symbol)).scalar_one_or_none()
        # earnings = await self.db.execute(select(EarningsCalendar).where(
        #     EarningsCalendar.symbol == option.symbol,
        #     EarningsCalendar.earnings_date > datetime.utcnow()
        # ).order_by(EarningsCalendar.earnings_date)).scalar_one_or_none()
        
        ticker = None
        earnings = None
        
        risk_adjustment = self.calculate_risk_adjustment(
            option.symbol,
            earnings.earnings_date if earnings else None,
            ticker.sector if ticker else None
        )
        
        # Qualitative score from GPT
        qualitative_score = 0.5  # Default
        if gpt_analysis and 'qualitative_score' in gpt_analysis:
            qualitative_score = self.calculate_qualitative_score(gpt_analysis['qualitative_score'])
        
        # Composite score
        composite_score = self.calculate_composite_score(
            annualized_yield, proximity_score, liquidity_score, 
            risk_adjustment, qualitative_score
        )
        
        # Build rationale
        rationale = {
            "annualized_yield": annualized_yield,
            "proximity_score": proximity_score,
            "liquidity_score": liquidity_score,
            "risk_adjustment": risk_adjustment,
            "qualitative_score": qualitative_score,
            "dte": dte,
            "spread_pct": spread_pct,
            "mid_price": mid_price
        }
        
        return {
            "score": composite_score,
            "rationale": rationale
        }
    
    def filter_options(self, options: List[Option], current_prices: Dict[str, float]) -> List[Tuple[Option, Dict]]:
        """Filter and score options based on criteria."""
        scored_options = []
        
        for option in options:
            if option.option_type != 'put':
                continue
            
            current_price = current_prices.get(option.symbol, 0)
            if current_price <= 0:
                continue
            
            # Apply filters
            if not self._passes_filters(option, current_price):
                continue
            
            # Score the option
            score_result = self.score_option(option, current_price)
            
            if score_result["score"] > 0:
                scored_options.append((option, score_result))
        
        # Sort by score descending
        scored_options.sort(key=lambda x: x[1]["score"], reverse=True)
        
        return scored_options
    
    def _passes_filters(self, option: Option, current_price: float) -> bool:
        """Check if option passes all filters."""
        # Delta filter
        if option.delta:
            if not (settings.put_delta_min <= abs(option.delta) <= settings.put_delta_max):
                return False
        
        # IV Rank filter (simplified - would need historical data)
        if option.implied_volatility:
            # Assume reasonable IV range for now
            if not (0.1 <= option.implied_volatility <= 2.0):
                return False
        
        # OI and Volume filters
        if option.open_interest and option.open_interest < settings.min_oi:
            return False
        
        if option.volume and option.volume < settings.min_volume:
            return False
        
        # Bid-ask spread filter
        if option.bid and option.ask:
            spread_pct = self.calculate_bid_ask_spread_pct(option.bid, option.ask)
            if spread_pct > settings.max_bid_ask_pct:
                return False
        
        # Annualized yield filter
        dte = (option.expiry - datetime.utcnow()).days
        if dte > 0 and option.bid and option.ask:
            mid_price = (option.bid + option.ask) / 2
            annualized_yield = self.calculate_annualized_yield(mid_price, option.strike, dte)
            if annualized_yield < settings.annualized_min_pct:
                return False
        
        return True
    
    def get_top_recommendations(self, scored_options: List[Tuple[Option, Dict]], 
                              max_recommendations: int = None) -> List[Tuple[Option, Dict]]:
        """Get top recommendations with sector diversification."""
        if max_recommendations is None:
            max_recommendations = settings.max_recommendations
        
        if len(scored_options) <= max_recommendations:
            return scored_options[:max_recommendations]
        
        # Simple sector diversification
        selected = []
        sectors_seen = set()
        
        for option, score_result in scored_options:
            # Note: This query would need to be async, but for now we'll use a default sector
            # ticker = await self.db.execute(select(Ticker).where(Ticker.symbol == option.symbol)).scalar_one_or_none()
            # sector = ticker.sector if ticker else "unknown"
            sector = "unknown"  # Default for now
            
            # Prefer different sectors
            if sector not in sectors_seen or len(selected) < max_recommendations // 2:
                selected.append((option, score_result))
                sectors_seen.add(sector)
            
            if len(selected) >= max_recommendations:
                break
        
        return selected
