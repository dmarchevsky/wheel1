#!/usr/bin/env python3
"""Test script for the new data fetch logic using FMP API."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'backend'))

from sqlalchemy.ext.asyncio import AsyncSession
from db.session import AsyncSessionLocal
from services.market_data_service import MarketDataService
from utils.timezone import pacific_now


async def test_market_population():
    """Test the market population functionality."""
    print("🔄 Testing market population...")
    
    async with AsyncSessionLocal() as db:
        market_data_service = MarketDataService(db)
        
        # Test SP500 update
        print("📊 Testing SP500 universe update...")
        sp500_result = await market_data_service.update_sp500_universe()
        print(f"✅ SP500 update completed: {len(sp500_result)} tickers")
        
        # Test fundamentals update
        print("📈 Testing fundamentals update...")
        fundamentals_result = await market_data_service.update_all_fundamentals()
        print(f"✅ Fundamentals update completed: {fundamentals_result['successful_updates']}/{fundamentals_result['total_processed']} successful")


async def test_universe_scoring():
    """Test the universe scoring functionality."""
    print("🎯 Testing universe scoring...")
    
    async with AsyncSessionLocal() as db:
        market_data_service = MarketDataService(db)
        
        result = await market_data_service.calculate_universe_scores()
        print(f"✅ Universe scoring completed: {result['scored_tickers']}/{result['total_tickers']} tickers scored")


async def test_recommendation_updates():
    """Test the recommendation updates functionality."""
    print("📈 Testing recommendation updates...")
    
    async with AsyncSessionLocal() as db:
        market_data_service = MarketDataService(db)
        
        result = await market_data_service.update_recommendation_tickers()
        print(f"✅ Recommendation updates completed: {result['updated_quotes']} quotes, {result['updated_options']} option chains")


async def main():
    """Run all tests."""
    print("🧪 Testing new data fetch logic with FMP API...")
    print("=" * 50)
    
    try:
        # Test market population
        await test_market_population()
        print()
        
        # Test universe scoring
        await test_universe_scoring()
        print()
        
        # Test recommendation updates
        await test_recommendation_updates()
        print()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
