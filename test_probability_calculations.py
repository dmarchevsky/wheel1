#!/usr/bin/env python3
"""Test script for probability of profit calculations."""

import math
import numpy as np
from datetime import datetime, timezone
from typing import Dict

def calculate_probability_of_profit_black_scholes(
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

def calculate_probability_of_profit_delta(delta: float) -> float:
    """Calculate probability of profit using delta approximation."""
    if delta is None:
        return 0.5  # Default 50% if no delta available
    
    # For puts, delta is negative, so we use absolute value
    # Probability ≈ 1 - |delta|
    return 1.0 - abs(delta)

def test_probability_calculations():
    """Test probability calculations with real data from the database."""
    
    # Test data from our database
    test_cases = [
        {
            "symbol": "U",
            "current_price": 39.41,
            "strike": 37.0,
            "implied_volatility": 0.655776,
            "delta": -0.33,
            "expiry": "2025-09-26T00:00:00.000Z"
        },
        {
            "symbol": "HOOD", 
            "current_price": 104.03,
            "strike": 99.0,
            "implied_volatility": 0.596628,
            "delta": -0.35,
            "expiry": "2025-09-26T00:00:00.000Z"
        }
    ]
    
    print("🎯 Probability of Profit Calculations Test")
    print("=" * 60)
    
    for case in test_cases:
        print(f"\n📊 {case['symbol']} Cash-Secured Put Analysis:")
        print(f"   Current Price: ${case['current_price']:.2f}")
        print(f"   Strike Price:  ${case['strike']:.2f}")
        print(f"   Implied Vol:   {case['implied_volatility']:.1%}")
        print(f"   Delta:         {case['delta']:.2f}")
        
        # Calculate time to expiry (simplified - using fixed date)
        expiry_date = datetime.fromisoformat(case['expiry'].replace('Z', '+00:00'))
        current_date = datetime.now(timezone.utc)
        dte = (expiry_date - current_date).days
        time_to_expiry = dte / 365.0
        
        print(f"   DTE:           {dte} days ({time_to_expiry:.3f} years)")
        
        # Calculate probabilities using different methods
        delta_prob = calculate_probability_of_profit_delta(case['delta'])
        black_scholes_prob = calculate_probability_of_profit_black_scholes(
            current_price=case['current_price'],
            strike=case['strike'],
            time_to_expiry=time_to_expiry,
            implied_volatility=case['implied_volatility']
        )
        monte_carlo_prob = calculate_probability_of_profit_monte_carlo(
            current_price=case['current_price'],
            strike=case['strike'],
            time_to_expiry=time_to_expiry,
            implied_volatility=case['implied_volatility']
        )
        
        print(f"\n📈 Probability of Profit Results:")
        print(f"   Delta Method:        {delta_prob:.1%}")
        print(f"   Black-Scholes:       {black_scholes_prob:.1%}")
        print(f"   Monte Carlo:         {monte_carlo_prob:.1%}")
        
        # Calculate average for comparison
        avg_prob = (delta_prob + black_scholes_prob + monte_carlo_prob) / 3
        print(f"   Average:             {avg_prob:.1%}")
        
        # Risk assessment
        print(f"\n⚠️  Risk Assessment:")
        if avg_prob >= 0.7:
            risk_level = "Low Risk"
        elif avg_prob >= 0.5:
            risk_level = "Moderate Risk"
        else:
            risk_level = "High Risk"
        print(f"   Risk Level:          {risk_level}")
        
        # Profit potential analysis
        price_ratio = case['strike'] / case['current_price']
        print(f"   Strike/Price Ratio:  {price_ratio:.3f}")
        if price_ratio > 0.95:
            print(f"   Note: Strike close to current price - higher assignment risk")
        elif price_ratio < 0.85:
            print(f"   Note: Deep OTM - lower premium but safer")
        
        print("-" * 60)

if __name__ == "__main__":
    test_probability_calculations()
