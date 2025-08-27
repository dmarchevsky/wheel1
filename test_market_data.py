#!/usr/bin/env python3

"""Test script to debug the market data service."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app/backend'))

from db.session import SyncSessionLocal
from services.market_data_service import MarketDataService

async def test_market_data_service():
    """Test the market data service to debug issues."""
    print("🔍 Debugging Market Data Service")
    print("=" * 50)
    
    # Create database session
    db = SyncSessionLocal()
    
    try:
        print("\n1. Testing Market Data Service initialization...")
        market_data_service = MarketDataService(db)
        print("   ✅ Market data service initialized")
        
        print("\n2. Testing S&P 500 constituents fetching...")
        sp500_tickers = await market_data_service._get_sp500_constituents()
        print(f"   📊 Found {len(sp500_tickers)} S&P 500 constituents")
        
        if sp500_tickers:
            print("   📋 Sample constituents:")
            for ticker in sp500_tickers[:5]:
                print(f"      - {ticker['symbol']}")
        
        print("\n3. Testing ticker upsert...")
        if sp500_tickers:
            # Test with first ticker
            test_ticker = sp500_tickers[0]
            print(f"   🧪 Testing with {test_ticker['symbol']}...")
            
            try:
                ticker = await market_data_service._upsert_ticker(test_ticker)
                if ticker:
                    print(f"   ✅ Successfully upserted {ticker.symbol}")
                    print(f"      Name: {ticker.name}")
                    print(f"      Sector: {ticker.sector}")
                    print(f"      Price: ${ticker.current_price}")
                    print(f"      Market Cap: ${ticker.market_cap:.1f}B")
                else:
                    print(f"   ❌ Failed to upsert {test_ticker['symbol']}")
            except Exception as e:
                print(f"   ❌ Error upserting {test_ticker['symbol']}: {e}")
        
        print("\n4. Testing full S&P 500 update...")
        try:
            updated_tickers = await market_data_service.update_sp500_universe()
            print(f"   📊 Updated {len(updated_tickers)} tickers")
            
            if updated_tickers:
                print("   📋 Sample updated tickers:")
                for ticker in updated_tickers[:3]:
                    print(f"      - {ticker.symbol}: {ticker.name}")
                    print(f"        Sector: {ticker.sector}, Price: ${ticker.current_price}")
            else:
                print("   ⚠️ No tickers were updated")
                
        except Exception as e:
            print(f"   ❌ Error in full update: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n5. Testing market summary...")
        try:
            summary = await market_data_service.get_market_summary()
            print(f"   📊 Market Summary: {summary}")
        except Exception as e:
            print(f"   ❌ Error getting summary: {e}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_market_data_service())








