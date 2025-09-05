from utils.timezone import pacific_now
"""Scoring algorithms for Wheel Strategy recommendations."""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import Option, InterestingTicker
from config import settings as env_settings
from services.settings_service import get_setting
from datetime import datetime, timezone


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
    
    def calculate_contract_price(self, bid: float, ask: float, last: float = None) -> float:
        """Calculate contract price (premium received for selling put)."""
        if bid and ask:
            # Use mid price for cash-secured puts
            return (bid + ask) / 2
        elif last:
            return last
        elif bid:
            return bid
        elif ask:
            return ask
        return 0.0
    
    def calculate_total_credit(self, contract_price: float, quantity: int = 1) -> float:
        """Calculate total credit received (contract price * 100 * quantity)."""
        return contract_price * 100 * quantity
    
    def calculate_collateral_required(self, strike: float, quantity: int = 1) -> float:
        """Calculate collateral required for cash-secured put (strike * 100 * quantity)."""
        return strike * 100 * quantity
    
    def calculate_annualized_roi(self, total_credit: float, collateral_required: float, dte: int) -> float:
        """Calculate annualized ROI as percentage."""
        if dte <= 0 or collateral_required <= 0:
            return 0.0
        return (total_credit / collateral_required) / (dte / 365) * 100
    
    def calculate_bid_ask_spread_pct(self, bid: float, ask: float) -> float:
        """Calculate bid-ask spread as percentage of mid price."""
        if bid <= 0 or ask <= 0 or bid >= ask:
            return 999.0  # Return large but JSON-safe value instead of inf
        
        mid_price = (bid + ask) / 2
        if mid_price <= 0:
            return 999.0
            
        spread_pct = ((ask - bid) / mid_price) * 100
        # Ensure result is JSON-safe
        if spread_pct == float('inf') or spread_pct != spread_pct:  # NaN check
            return 999.0
        return min(spread_pct, 999.0)  # Cap at reasonable maximum
    
    def calculate_iv_rank(self, current_iv: float, historical_ivs: List[float] = None) -> float:
        """Calculate IV Rank (percentile of current IV vs historical)."""
        if historical_ivs and len(historical_ivs) > 0 and current_iv > 0:
            # Use actual historical data if available
            rank = (sum(1 for iv in historical_ivs if iv < current_iv) / len(historical_ivs)) * 100
            return rank
        elif current_iv > 0:
            # Simplified IV rank without historical data
            # Based on typical IV ranges for equity options
            return self.calculate_simplified_iv_rank(current_iv)
        else:
            return 50.0  # Default to middle rank
    
    def calculate_simplified_iv_rank(self, current_iv: float, historical_volatility: float = None) -> float:
        """Calculate simplified IV rank based on IV vs historical volatility or typical ranges."""
        if current_iv <= 0:
            return 0.0
        
        # Convert IV to percentage for easier comparison
        iv_pct = current_iv * 100
        
        # If we have historical volatility, use IV/HV ratio for better ranking
        if historical_volatility and historical_volatility > 0:
            # Convert HV to percentage to match IV
            hv_pct = historical_volatility
            if hv_pct < 1:  # If it's in decimal form, convert to percentage
                hv_pct = historical_volatility * 100
            
            # Calculate IV/HV ratio
            iv_hv_ratio = iv_pct / hv_pct
            
            # Convert ratio to percentile rank:
            # Ratio < 0.8: IV is low relative to HV -> Rank 0-30
            # Ratio 0.8-1.2: IV near HV (normal) -> Rank 30-70
            # Ratio > 1.2: IV is high relative to HV -> Rank 70-100
            
            if iv_hv_ratio <= 0.6:
                # Very low IV vs HV -> Rank 0-15
                return min(15, (iv_hv_ratio / 0.6) * 15)
            elif iv_hv_ratio <= 0.8:
                # Low IV vs HV -> Rank 15-30
                return 15 + ((iv_hv_ratio - 0.6) / 0.2) * 15
            elif iv_hv_ratio <= 1.0:
                # Normal IV vs HV -> Rank 30-50
                return 30 + ((iv_hv_ratio - 0.8) / 0.2) * 20
            elif iv_hv_ratio <= 1.2:
                # Elevated IV vs HV -> Rank 50-70
                return 50 + ((iv_hv_ratio - 1.0) / 0.2) * 20
            elif iv_hv_ratio <= 1.5:
                # High IV vs HV -> Rank 70-85
                return 70 + ((iv_hv_ratio - 1.2) / 0.3) * 15
            else:
                # Very high IV vs HV -> Rank 85-95 (capped)
                return min(95, 85 + ((iv_hv_ratio - 1.5) / 0.5) * 10)
        
        else:
            # Fallback to absolute IV ranges when no historical volatility
            # Typical IV ranges for equity options:
            # Very Low: 0-15%  -> Rank 0-20
            # Low: 15-25%      -> Rank 20-40  
            # Medium: 25-35%   -> Rank 40-60
            # High: 35-50%     -> Rank 60-80
            # Very High: 50%+  -> Rank 80-100
            
            if iv_pct <= 15:
                # Linear scale from 0-20 for 0-15% IV
                return (iv_pct / 15) * 20
            elif iv_pct <= 25:
                # Linear scale from 20-40 for 15-25% IV
                return 20 + ((iv_pct - 15) / 10) * 20
            elif iv_pct <= 35:
                # Linear scale from 40-60 for 25-35% IV
                return 40 + ((iv_pct - 25) / 10) * 20
            elif iv_pct <= 50:
                # Linear scale from 60-80 for 35-50% IV
                return 60 + ((iv_pct - 35) / 15) * 20
            else:
                # Linear scale from 80-100 for 50%+ IV, capped at 95
                return min(95, 80 + ((iv_pct - 50) / 25) * 20)
    
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
    
    def calculate_liquidity_score(self, oi: int, volume: int, spread_pct: float, 
                                oi_threshold: int = 1000, volume_threshold: int = 500) -> float:
        """Calculate liquidity score based on OI, volume, and spread."""
        if oi <= 0 or volume <= 0:
            return 0.0
        
        # Normalize OI and volume using provided thresholds
        oi_score = min(1.0, oi / oi_threshold)
        volume_score = min(1.0, volume / volume_threshold)
        
        # Spread score (inverse - lower spread is better)
        spread_score = max(0.0, 1.0 - (spread_pct / 10))  # 10% spread = 0 score
        
        # Combine scores with weights
        liquidity_score = (0.4 * oi_score + 0.4 * volume_score + 0.2 * spread_score)
        return liquidity_score
    
    async def calculate_risk_adjustment(self, symbol: str, earnings_date: Optional[datetime] = None) -> float:
        """Calculate risk adjustment factor."""
        risk_score = 1.0
        
        # Earnings blackout penalty
        if earnings_date:
            days_to_earnings = (earnings_date - pacific_now()).days
            earnings_blackout_days = await get_setting(self.db, "earnings_blackout_days", 7)
            if 0 <= days_to_earnings <= earnings_blackout_days:
                risk_score *= 0.3  # Significant penalty during earnings blackout
        
        return risk_score
    
    def calculate_qualitative_score(self, gpt_score: float) -> float:
        """Convert ChatGPT qualitative score to normalized score."""
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, gpt_score))
    
    def calculate_composite_score(self, annualized_roi: float, monte_carlo_probability: float,
                                **kwargs) -> float:
        """Calculate composite score using ROI and Monte-Carlo winning probability."""
        # Normalize ROI (assume 30%+ is excellent for annual ROI)
        normalized_roi = min(1.0, annualized_roi / 30.0) if annualized_roi > 0 else 0.0
        
        # Monte-Carlo probability is already between 0-1
        normalized_probability = max(0.0, min(1.0, monte_carlo_probability))
        
        # Simple weighted composite score: 60% ROI, 40% winning probability
        composite_score = (
            0.6 * normalized_roi +
            0.4 * normalized_probability
        )
        
        return composite_score
    
    def calculate_probability_of_profit_delta(self, delta: float) -> float:
        """Calculate probability of profit using delta approximation."""
        if delta is None:
            return 0.5  # Default 50% if no delta available
        
        # For puts, delta is negative, so we use absolute value
        # Probability ≈ 1 - |delta|
        return 1.0 - abs(delta)
    
    def calculate_probability_of_profit_black_scholes(
        self,
        current_price: float,
        strike: float, 
        time_to_expiry: float,
        risk_free_rate: float = 0.02,
        implied_volatility: float = None
    ) -> float:
        """Calculate probability of profit using Black-Scholes model."""
        if implied_volatility is None or implied_volatility <= 0:
            return 0.5  # Default if no IV available
        
        try:
            # For cash-secured puts, profit occurs when S_T > strike
            # Calculate d2 from Black-Scholes
            d2 = (math.log(current_price / strike) + 
                  (risk_free_rate - 0.5 * implied_volatility**2) * time_to_expiry) / \
                 (implied_volatility * math.sqrt(time_to_expiry))
            
            # Probability S_T > strike = N(d2)
            # Using normal distribution approximation
            probability = 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
            
            return max(0.0, min(1.0, probability))  # Ensure 0-1 range
            
        except (ValueError, ZeroDivisionError):
            return 0.5  # Default on calculation errors
    
    def calculate_probability_of_profit_monte_carlo(
        self,
        current_price: float,
        strike: float,
        time_to_expiry: float,
        implied_volatility: float,
        risk_free_rate: float = 0.02,
        num_simulations: int = 10000
    ) -> float:
        """Calculate probability of profit using Monte Carlo simulation."""
        if implied_volatility is None or implied_volatility <= 0:
            return 0.5  # Default if no IV available
        
        try:
            # Generate random price paths using geometric Brownian motion
            dt = time_to_expiry / 252  # Daily time steps
            drift = (risk_free_rate - 0.5 * implied_volatility**2) * dt
            diffusion = implied_volatility * np.sqrt(dt)
            
            # Simulate price paths
            price_paths = np.zeros((num_simulations, 252))
            price_paths[:, 0] = current_price
            
            for i in range(1, 252):
                random_shocks = np.random.normal(0, 1, num_simulations)
                price_paths[:, i] = price_paths[:, i-1] * np.exp(drift + diffusion * random_shocks)
            
            # Calculate final prices
            final_prices = price_paths[:, -1]
            
            # For cash-secured puts, profit if final price > strike
            profitable_paths = np.sum(final_prices > strike)
            probability = profitable_paths / num_simulations
            
            return max(0.0, min(1.0, probability))  # Ensure 0-1 range
            
        except (ValueError, ZeroDivisionError):
            return 0.5  # Default on calculation errors
    
    def calculate_probability_of_profit(
        self, 
        option: Option, 
        current_price: float,
        method: str = "delta"
    ) -> float:
        """Calculate probability of profit using specified method."""
        if method == "delta" and option.delta is not None:
            return self.calculate_probability_of_profit_delta(option.delta)
        
        elif method == "black_scholes" and option.implied_volatility:
            dte = (option.expiry - pacific_now()).days
            time_to_expiry = dte / 365.0  # Convert to years
            
            return self.calculate_probability_of_profit_black_scholes(
                current_price=current_price,
                strike=option.strike,
                time_to_expiry=time_to_expiry,
                implied_volatility=option.implied_volatility
            )
        
        else:
            # Fallback to delta method or default
            if option.delta is not None:
                return self.calculate_probability_of_profit_delta(option.delta)
            return 0.5  # Default 50%
    
    def calculate_probability_of_profit_both_methods(
        self,
        option: Option,
        current_price: float
    ) -> Dict[str, float]:
        """Calculate probability of profit using both Black-Scholes and Monte Carlo methods."""
        dte = (option.expiry - pacific_now()).days
        time_to_expiry = dte / 365.0  # Convert to years
        
        # Calculate using both methods
        black_scholes_prob = self.calculate_probability_of_profit_black_scholes(
            current_price=current_price,
            strike=option.strike,
            time_to_expiry=time_to_expiry,
            implied_volatility=option.implied_volatility
        )
        
        monte_carlo_prob = self.calculate_probability_of_profit_monte_carlo(
            current_price=current_price,
            strike=option.strike,
            time_to_expiry=time_to_expiry,
            implied_volatility=option.implied_volatility
        )
        
        return {
            "black_scholes": black_scholes_prob,
            "monte_carlo": monte_carlo_prob
        }

    async def score_option(self, option: Option, current_price: float, 
                    gpt_analysis: Dict = None) -> Dict[str, float]:
        """Score a single option contract."""
        # Basic calculations
        dte = (option.expiry - pacific_now()).days
        if dte <= 0:
            return {"score": 0.0, "rationale": {}}
        
        # Get mid price
        if option.bid and option.ask:
            mid_price = (option.bid + option.ask) / 2
            spread_pct = self.calculate_bid_ask_spread_pct(option.bid, option.ask)
        else:
            mid_price = option.last or 0
            spread_pct = 999.0  # Large but JSON-safe value
        
        # Calculate components
        annualized_yield = self.calculate_annualized_yield(mid_price, option.strike, dte)
        proximity_score = self.calculate_proximity_to_support(current_price, option.strike)
        
        # Get liquidity thresholds from settings
        try:
            oi_threshold = await get_setting(self.db, "liquidity_oi_threshold", 1000)
            volume_threshold = await get_setting(self.db, "liquidity_volume_threshold", 500)
        except:
            # Fallback to reasonable defaults if settings not available
            oi_threshold = 1000
            volume_threshold = 500
        
        liquidity_score = self.calculate_liquidity_score(
            option.open_interest or 0, 
            option.volume or 0, 
            spread_pct,
            oi_threshold,
            volume_threshold
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
        
        risk_adjustment = await self.calculate_risk_adjustment(
            option.symbol,
            earnings.earnings_date if earnings else None
        )
        
        # Qualitative score from GPT
        qualitative_score = 0.5  # Default
        if gpt_analysis and 'qualitative_score' in gpt_analysis:
            qualitative_score = self.calculate_qualitative_score(gpt_analysis['qualitative_score'])
        
        # Calculate probability of profit using both methods
        probability_data = self.calculate_probability_of_profit_both_methods(option, current_price)
        black_scholes_prob = probability_data["black_scholes"]
        monte_carlo_prob = probability_data["monte_carlo"]
        
        # Use Black-Scholes for scoring (more stable)
        probability_of_profit = black_scholes_prob
        
        # Calculate additional financial metrics first
        total_credit = self.calculate_total_credit(mid_price)
        collateral_required = self.calculate_collateral_required(option.strike)
        annualized_roi = self.calculate_annualized_roi(total_credit, collateral_required, dte)
        
        # Composite score using ROI and Monte-Carlo probability
        composite_score = self.calculate_composite_score(
            annualized_roi=annualized_roi,
            monte_carlo_probability=monte_carlo_prob
        )
        
        # Build rationale
        rationale = {
            "annualized_yield": annualized_yield,
            "annualized_roi": annualized_roi,  # Add ROI calculation
            "proximity_score": proximity_score,
            "liquidity_score": liquidity_score,
            "risk_adjustment": risk_adjustment,
            "qualitative_score": qualitative_score,
            "probability_of_profit_black_scholes": black_scholes_prob,
            "probability_of_profit_monte_carlo": monte_carlo_prob,
            "spread_pct": spread_pct,
            "mid_price": mid_price,
            "dte": dte,  # Add DTE
            "total_credit": total_credit,  # Add financial metrics
            "collateral_required": collateral_required,
            "contract_price": mid_price
        }
        
        # Sanitize all float values to ensure JSON compliance
        sanitized_rationale = self._sanitize_float_values(rationale)
        sanitized_score = self._sanitize_float_value(composite_score)
        
        return {
            "score": sanitized_score,
            "rationale": sanitized_rationale
        }
    
    def _sanitize_float_value(self, value: float) -> float:
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
    
    def _sanitize_float_values(self, data: dict) -> dict:
        """Recursively sanitize all float values in a dictionary."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, float):
                sanitized[key] = self._sanitize_float_value(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_float_values(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_float_value(v) if isinstance(v, float) else v for v in value]
            else:
                sanitized[key] = value
        return sanitized

    async def filter_options(self, options: List[Option], current_prices: Dict[str, float]) -> List[Tuple[Option, Dict]]:
        """Filter and score options based on criteria."""
        scored_options = []
        
        for option in options:
            if option.option_type != 'put':
                continue
            
            current_price = current_prices.get(option.symbol, 0)
            if current_price <= 0:
                continue
            
            # Apply filters
            if not await self._passes_filters(option, current_price):
                continue
            
            # Score the option
            score_result = await self.score_option(option, current_price)
            
            if score_result["score"] > 0:
                scored_options.append((option, score_result))
        
        # Sort by score descending
        scored_options.sort(key=lambda x: x[1]["score"], reverse=True)
        
        return scored_options
    
    async def _passes_filters(self, option: Option, current_price: float) -> bool:
        """Check if option passes all filters."""
        # Delta filter
        if option.delta:
            put_delta_min = await get_setting(self.db, "put_delta_min", 0.25)
            put_delta_max = await get_setting(self.db, "put_delta_max", 0.35)
            if not (put_delta_min <= abs(option.delta) <= put_delta_max):
                return False
        
        # IV Rank filter (simplified - would need historical data)
        if option.implied_volatility:
            # Assume reasonable IV range for now
            if not (0.1 <= option.implied_volatility <= 2.0):
                return False
        
        # OI and Volume filters - require minimum thresholds
        min_oi = await get_setting(self.db, "min_oi", 500)
        if not option.open_interest or option.open_interest < min_oi:
            return False
        
        min_volume = await get_setting(self.db, "min_volume", 200)
        if not option.volume or option.volume < min_volume:
            return False
        
        # Bid-ask spread filter
        if option.bid and option.ask:
            spread_pct = self.calculate_bid_ask_spread_pct(option.bid, option.ask)
            max_bid_ask_pct = await get_setting(self.db, "max_bid_ask_pct", 5.0)
            if spread_pct > max_bid_ask_pct:
                return False
        
        # Annualized yield filter - require minimum yield
        dte = (option.expiry - pacific_now()).days
        if dte > 0:
            # Get contract price (mid price preferred, fallback to last)
            if option.bid and option.ask:
                contract_price = (option.bid + option.ask) / 2
            elif option.last:
                contract_price = option.last
            else:
                # No pricing data available - reject
                return False
            
            annualized_yield = self.calculate_annualized_yield(contract_price, option.strike, dte)
            annualized_min_pct = await get_setting(self.db, "annualized_min_pct", 20.0)
            if annualized_yield < annualized_min_pct:
                return False
        
        return True
    
    async def get_top_recommendations(self, scored_options: List[Tuple[Option, Dict]]) -> List[Tuple[Option, Dict]]:
        """Get top recommendations based purely on score ranking."""
        # Simply return the top option by score
        return scored_options[:1] if scored_options else []
