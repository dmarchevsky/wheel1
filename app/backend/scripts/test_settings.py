#!/usr/bin/env python3
"""Test script for settings system."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_async_db
from services.settings_service import SettingsService, get_setting, get_all_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_settings():
    """Test the settings system."""
    async for db in get_async_db():
        try:
            settings_service = SettingsService(db)
            
            logger.info("Testing settings system...")
            
            # Test getting all settings
            all_settings = await settings_service.get_all_settings()
            logger.info(f"All settings: {len(all_settings)} items")
            
            # Test getting individual settings
            put_delta_min = await get_setting(db, "put_delta_min", 0.25)
            logger.info(f"put_delta_min: {put_delta_min}")
            
            dte_min = await get_setting(db, "dte_min", 21)
            logger.info(f"dte_min: {dte_min}")
            
            # Test updating a setting
            logger.info("Testing setting update...")
            success = await settings_service.set_setting("test_setting", "test_value")
            logger.info(f"Update test setting: {success}")
            
            # Test getting the updated setting
            test_value = await get_setting(db, "test_setting", "default")
            logger.info(f"test_setting value: {test_value}")
            
            # Test deleting the test setting
            logger.info("Testing setting deletion...")
            delete_success = await settings_service.delete_setting("test_setting")
            logger.info(f"Delete test setting: {delete_success}")
            
            # Test getting schema
            schema = settings_service.get_settings_schema()
            logger.info(f"Schema has {len(schema)} settings")
            
            # Test convenience functions
            all_settings_via_func = await get_all_settings(db)
            logger.info(f"All settings via function: {len(all_settings_via_func)} items")
            
            logger.info("Settings system test completed successfully!")
            
        except Exception as e:
            logger.error(f"Error testing settings: {e}")
        finally:
            break


if __name__ == "__main__":
    asyncio.run(test_settings())
