#!/usr/bin/env python3
"""Test script to verify Pacific timezone timestamps."""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_async_db
from db.models import InterestingTicker, Recommendation, Option, Trade
from utils.timezone import now_pacific, format_pacific_datetime, is_pacific_timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_timezone_conversion():
    """Test that all timestamps are in Pacific timezone."""
    async for db in get_async_db():
        try:
            logger.info("🔍 Testing timezone conversion...")
            
            # Test current time
            current_pacific = datetime.now(timezone.utc)
            logger.info(f"📍 Current Pacific time: {format_pacific_datetime(current_pacific)}")
            logger.info(f"📍 Is Pacific timezone: {is_pacific_timezone(current_pacific)}")
            
            # Test database timestamps
            tables_to_test = [
                ("interesting_tickers", InterestingTicker, "updated_at"),
                ("recommendations", Recommendation, "created_at"),
                ("options", Option, "updated_at"),
                ("trades", Trade, "created_at"),
            ]
            
            for table_name, model, column_name in tables_to_test:
                logger.info(f"📊 Testing {table_name}.{column_name}...")
                
                # Get a sample record
                result = await db.execute(select(model).limit(1))
                sample = result.scalar_one_or_none()
                
                if sample:
                    timestamp = getattr(sample, column_name)
                    if timestamp:
                        logger.info(f"   📅 Raw timestamp: {timestamp}")
                        logger.info(f"   📅 Formatted Pacific: {format_pacific_datetime(timestamp)}")
                        logger.info(f"   📅 Is Pacific: {is_pacific_timezone(timestamp)}")
                        logger.info(f"   📅 Timezone info: {timestamp.tzinfo}")
                    else:
                        logger.info(f"   ⚠️  No timestamp found in {column_name}")
                else:
                    logger.info(f"   ⚠️  No records found in {table_name}")
            
            # Test creating a new record
            logger.info("🧪 Testing new record creation...")
            
            # Create a test ticker (if it doesn't exist)
            test_symbol = "TEST_TZ"
            existing = await db.execute(
                select(InterestingTicker).where(InterestingTicker.symbol == test_symbol)
            )
            existing_ticker = existing.scalar_one_or_none()
            
            if not existing_ticker:
                new_ticker = InterestingTicker(
                    symbol=test_symbol,
                    name="Timezone Test Ticker",
                    sector="Test",
                    active=False  # Mark as inactive so it doesn't interfere
                )
                db.add(new_ticker)
                await db.commit()
                
                # Check the timestamp
                logger.info(f"   📅 New ticker created_at: {format_pacific_datetime(new_ticker.created_at)}")
                logger.info(f"   📅 Is Pacific: {is_pacific_timezone(new_ticker.created_at)}")
                
                # Clean up
                await db.delete(new_ticker)
                await db.commit()
                logger.info("   🧹 Test record cleaned up")
            else:
                logger.info("   ⚠️  Test ticker already exists, skipping creation test")
            
            logger.info("✅ Timezone test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error during timezone test: {e}")
            raise
        finally:
            break


if __name__ == "__main__":
    asyncio.run(test_timezone_conversion())
