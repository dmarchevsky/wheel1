#!/usr/bin/env python3
"""Test script to verify option chain filtering with delta and DTE criteria."""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.session import get_async_db
from db.models import InterestingTicker, Option
from clients.tradier import TradierDataManager
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_option_filtering():
    """Test option chain filtering with delta and DTE criteria."""
    async for db in get_async_db():
        try:
            logger.info("🔍 Testing option chain filtering...")
            
            # Test with a well-known ticker
            test_symbol = "AAPL"
            
            # Initialize TradierDataManager
            tradier_manager = TradierDataManager(db)
            
            # Test 1: Get optimal expiration
            logger.info(f"📅 Test 1: Getting optimal expiration for {test_symbol}...")
            optimal_expiration = await tradier_manager.get_optimal_expiration(test_symbol)
            if optimal_expiration:
                logger.info(f"✅ Optimal expiration: {optimal_expiration}")
                
                # Calculate DTE for verification
                exp_date = datetime.strptime(optimal_expiration, "%Y-%m-%d")
                dte = (exp_date - datetime.now()).days
                logger.info(f"📊 DTE: {dte} days (target: {settings.covered_call_dte_min}-{settings.covered_call_dte_max})")
                
                if settings.covered_call_dte_min <= dte <= settings.covered_call_dte_max:
                    logger.info("✅ DTE is within optimal range!")
                else:
                    logger.warning(f"⚠️  DTE is outside optimal range")
            else:
                logger.error("❌ Failed to get optimal expiration")
                return
            
            # Test 2: Fetch and filter options
            logger.info(f"📊 Test 2: Fetching and filtering options for {test_symbol}...")
            options = await tradier_manager.sync_options_data(test_symbol, optimal_expiration)
            logger.info(f"✅ Fetched {len(options)} filtered options")
            
            # Test 3: Verify filtering criteria
            logger.info(f"🔍 Test 3: Verifying filtering criteria...")
            
            for i, option in enumerate(options[:5]):  # Show first 5 options
                logger.info(f"   Option {i+1}: {option.symbol} {option.strike} {option.option_type}")
                logger.info(f"      DTE: {option.dte} days")
                logger.info(f"      Delta: {option.delta}")
                logger.info(f"      Open Interest: {option.open_interest}")
                
                # Verify DTE criteria
                if not (settings.covered_call_dte_min <= option.dte <= settings.covered_call_dte_max):
                    logger.error(f"❌ Option {i+1} failed DTE filter: {option.dte} days")
                
                # Verify delta criteria (for puts, delta should be negative)
                if option.option_type == "put":
                    if not (settings.put_delta_min <= abs(option.delta) <= settings.put_delta_max):
                        logger.error(f"❌ Option {i+1} failed delta filter: {option.delta}")
                
                # Verify basic liquidity
                if option.open_interest is not None and option.open_interest < 10:
                    logger.warning(f"⚠️  Option {i+1} has low open interest: {option.open_interest}")
            
            # Test 4: Check database storage
            logger.info(f"💾 Test 4: Checking database storage...")
            result = await db.execute(
                select(Option).where(
                    and_(
                        Option.symbol == test_symbol,
                        Option.option_type == "put",
                        Option.dte >= settings.covered_call_dte_min,
                        Option.dte <= settings.covered_call_dte_max,
                        Option.delta >= -settings.put_delta_max,
                        Option.delta <= -settings.put_delta_min
                    )
                )
            )
            stored_options = result.scalars().all()
            logger.info(f"📊 Found {len(stored_options)} options in database matching criteria")
            
            # Test 5: Test with another ticker
            test_symbol_2 = "MSFT"
            logger.info(f"📊 Test 5: Testing with {test_symbol_2}...")
            
            optimal_expiration_2 = await tradier_manager.get_optimal_expiration(test_symbol_2)
            if optimal_expiration_2:
                options_2 = await tradier_manager.sync_options_data(test_symbol_2, optimal_expiration_2)
                logger.info(f"✅ Fetched {len(options_2)} filtered options for {test_symbol_2}")
            else:
                logger.warning(f"⚠️  No optimal expiration found for {test_symbol_2}")
            
            logger.info("✅ Option filtering test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error during option filtering test: {e}")
            raise
        finally:
            break


if __name__ == "__main__":
    asyncio.run(test_option_filtering())
