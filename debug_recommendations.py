#!/usr/bin/env python3

"""Debug script to identify why recommendations are returning 0 results."""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app/backend'))

from db.session import SyncSessionLocal
from services.recommender_service import RecommenderService
from services.universe_service import UniverseService
from services.market_data_service import MarketDataService
from db.models import InterestingTicker, TickerQuote, Option, Position, Recommendation
from sqlalchemy import select, and_, func
from utils.timezone import now_pacific

async def debug_recommendations():
    """Debug the recommendation generation process step by step."""
    print("🔍 Debugging Recommendation Generation")
    print("=" * 60)
    
    # Create database session
    db = SyncSessionLocal()
    
    try:
        print("\n1. Checking database connectivity...")
        # Test basic database connectivity
        result = await db.execute(select(func.count(InterestingTicker.id)))
        total_tickers = result.scalar()
        print(f"   ✅ Database connected. Total tickers in database: {total_tickers}")
        
        print("\n2. Checking active tickers...")
        # Check active tickers
        result = await db.execute(
            select(InterestingTicker).where(InterestingTicker.active == True)
        )
        active_tickers = result.scalars().all()
        print(f"   📊 Active tickers: {len(active_tickers)}")
        
        if active_tickers:
            print("   📋 Sample active tickers:")
            for ticker in active_tickers[:5]:
                print(f"      - {ticker.symbol} (updated: {ticker.updated_at})")
        
        print("\n3. Checking ticker quotes...")
        # Check ticker quotes
        result = await db.execute(select(TickerQuote))
        quotes = result.scalars().all()
        print(f"   📊 Ticker quotes: {len(quotes)}")
        
        if quotes:
            print("   📋 Sample quotes:")
            for quote in quotes[:3]:
                print(f"      - {quote.symbol}: ${quote.current_price} (updated: {quote.updated_at})")
        
        print("\n4. Checking options data...")
        # Check options data
        result = await db.execute(select(Option))
        options = result.scalars().all()
        print(f"   📊 Total options: {len(options)}")
        
        if options:
            print("   📋 Sample options:")
            for option in options[:3]:
                print(f"      - {option.symbol} {option.strike} {option.option_type} (DTE: {option.dte})")
        
        print("\n5. Checking current positions...")
        # Check current positions
        result = await db.execute(
            select(Position).where(Position.status == "open")
        )
        positions = result.scalars().all()
        print(f"   📊 Open positions: {len(positions)}")
        
        if positions:
            print("   📋 Current positions:")
            for pos in positions:
                print(f"      - {pos.symbol}: {pos.shares} shares")
        
        print("\n6. Testing UniverseService...")
        # Test UniverseService
        universe_service = UniverseService(db)
        try:
            tickers = await universe_service.get_filtered_universe(fast_mode=True)
            print(f"   📊 UniverseService returned: {len(tickers)} tickers")
            
            if tickers:
                print("   📋 Top tickers by score:")
                for ticker in tickers[:5]:
                    score = ticker.universe_score or 0
                    print(f"      - {ticker.symbol}: {score:.3f}")
            else:
                print("   ❌ No tickers returned from UniverseService")
                
        except Exception as e:
            print(f"   ❌ UniverseService error: {e}")
        
        print("\n7. Testing MarketDataService...")
        # Test MarketDataService
        market_data_service = MarketDataService(db)
        try:
            # Check if we have recent data
            cutoff_time = now_pacific() - timedelta(hours=1)
            result = await db.execute(
                select(InterestingTicker).where(
                    and_(
                        InterestingTicker.active == True,
                        InterestingTicker.updated_at >= cutoff_time
                    )
                )
            )
            recent_tickers = result.scalars().all()
            print(f"   📊 Tickers with recent data (last hour): {len(recent_tickers)}")
            
            if not recent_tickers:
                print("   ⚠️  No recent ticker data. This might be the issue!")
                print("   💡 Try refreshing market data first:")
                print("      curl -X POST 'http://localhost:8000/v1/market-data/refresh-market-data'")
            
        except Exception as e:
            print(f"   ❌ MarketDataService error: {e}")
        
        print("\n8. Testing RecommenderService step by step...")
        # Test RecommenderService
        recommender_service = RecommenderService()
        
        # Step 1: Get universe
        print("   🔍 Step 1: Getting universe...")
        try:
            tickers = await recommender_service._get_universe(db, fast_mode=True)
            print(f"   📊 Universe tickers: {len(tickers)}")
            
            if not tickers:
                print("   ❌ No tickers in universe - this is the problem!")
                return
            
            # Step 2: Get positions
            print("   🔍 Step 2: Getting positions...")
            positions = await recommender_service._get_current_positions(db)
            print(f"   📊 Current positions: {positions}")
            
            # Step 3: Filter tickers
            print("   🔍 Step 3: Filtering tickers...")
            filtered_tickers = [ticker for ticker in tickers if ticker.symbol not in positions]
            print(f"   📊 Filtered tickers: {len(filtered_tickers)}")
            
            if not filtered_tickers:
                print("   ❌ No tickers after position filtering - all tickers have positions!")
                return
            
            # Step 4: Test options for first ticker
            print("   🔍 Step 4: Testing options for first ticker...")
            if filtered_tickers:
                first_ticker = filtered_tickers[0]
                print(f"   📊 Testing options for: {first_ticker.symbol}")
                
                options = await recommender_service._get_options_for_ticker(db, first_ticker)
                print(f"   📊 Options found: {len(options)}")
                
                if not options:
                    print("   ❌ No options found - this might be the issue!")
                    print("   💡 Possible causes:")
                    print("      - No options data in database")
                    print("      - Options data is stale (>1 hour old)")
                    print("      - Tradier API not returning options")
                    print("      - Options don't meet filtering criteria")
                else:
                    print("   ✅ Options found - scoring should work")
                    
        except Exception as e:
            print(f"   ❌ RecommenderService error: {e}")
            import traceback
            print(f"   📋 Traceback: {traceback.format_exc()}")
        
        print("\n9. Checking recommendation settings...")
        # Check configuration
        from config import settings
        print(f"   📊 Max recommendations: {settings.max_recommendations}")
        print(f"   📊 Put delta min: {settings.put_delta_min}")
        print(f"   📊 Put delta max: {settings.put_delta_max}")
        print(f"   📊 Min OI: {settings.min_oi}")
        print(f"   📊 Min volume: {settings.min_volume}")
        print(f"   📊 Annualized min %: {settings.annualized_min_pct}")
        
        print("\n10. Recommendations summary...")
        # Check existing recommendations
        result = await db.execute(
            select(Recommendation).where(Recommendation.status == "proposed")
        )
        current_recommendations = result.scalars().all()
        print(f"   📊 Current recommendations: {len(current_recommendations)}")
        
        if current_recommendations:
            print("   📋 Current recommendations:")
            for rec in current_recommendations:
                print(f"      - {rec.symbol}: {rec.score:.3f} (created: {rec.created_at})")
        
        print("\n" + "=" * 60)
        print("🔍 Debug Summary:")
        print("=" * 60)
        
        # Summary analysis
        if total_tickers == 0:
            print("❌ ISSUE: No tickers in database")
            print("   SOLUTION: Run S&P 500 universe update")
        elif len(active_tickers) == 0:
            print("❌ ISSUE: No active tickers")
            print("   SOLUTION: Check ticker activation status")
        elif len(quotes) == 0:
            print("❌ ISSUE: No ticker quotes")
            print("   SOLUTION: Refresh market data")
        elif len(options) == 0:
            print("❌ ISSUE: No options data")
            print("   SOLUTION: Fetch options data for tickers")
        else:
            print("✅ Data appears to be available")
            print("   Next step: Check individual ticker processing")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_recommendations())
