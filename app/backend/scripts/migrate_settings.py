#!/usr/bin/env python3
"""Migrate settings from environment variables to database."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.session import get_async_db
from services.settings_service import SettingsService
from config import settings as env_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_settings():
    """Migrate settings from environment variables to database."""
    async for db in get_async_db():
        try:
            settings_service = SettingsService(db)
            
            logger.info("Starting settings migration...")
            
            # Check if settings table is empty
            result = await db.execute(text("SELECT COUNT(*) FROM settings"))
            count = result.scalar()
            
            if count > 0:
                logger.info(f"Settings table already has {count} entries. Skipping migration.")
                return
            
            # Define all settings to migrate with their current environment values
            settings_to_migrate = {
                # Risk/Scoring Thresholds
                "put_delta_min": env_settings.put_delta_min,
                "put_delta_max": env_settings.put_delta_max,
                "ivr_min": env_settings.ivr_min,
                "ivr_max": env_settings.ivr_max,
                "min_oi": env_settings.min_oi,
                "min_volume": env_settings.min_volume,
                "max_bid_ask_pct": env_settings.max_bid_ask_pct,
                "annualized_min_pct": env_settings.annualized_min_pct,
                "max_recommendations": env_settings.max_recommendations,
                "earnings_blackout_days": env_settings.earnings_blackout_days,
                
                # Trading Configuration
                "profit_target_pct": env_settings.profit_target_pct,
                "time_decay_threshold_days": env_settings.time_decay_threshold_days,
                "time_decay_premium_threshold_pct": env_settings.time_decay_premium_threshold_pct,
                "delta_threshold_close": env_settings.delta_threshold_close,
                "dte_min": 21,  # Default value since env var was removed
                "dte_max": 35,  # Default value since env var was removed
                "covered_call_delta_min": env_settings.covered_call_delta_min,
                "covered_call_delta_max": env_settings.covered_call_delta_max,
            }
            
            logger.info(f"Migrating {len(settings_to_migrate)} settings to database...")
            
            # Migrate settings
            success = await settings_service.set_multiple_settings(settings_to_migrate)
            
            if success:
                logger.info("✅ Settings migration completed successfully!")
                
                # Display migrated settings
                all_settings = await settings_service.get_all_settings()
                logger.info("Migrated settings:")
                for key, value in all_settings.items():
                    logger.info(f"  {key}: {value}")
            else:
                logger.error("❌ Settings migration failed!")
                
        except Exception as e:
            logger.error(f"Error during settings migration: {e}")
        finally:
            break


if __name__ == "__main__":
    asyncio.run(migrate_settings())
