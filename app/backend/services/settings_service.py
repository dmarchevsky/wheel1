"""Comprehensive settings service for managing application configuration."""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Setting

logger = logging.getLogger(__name__)


class SettingsService:
    """Comprehensive settings service for managing application configuration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Optional[Dict[str, Any]] = None
    
    # Database CRUD Operations
    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings from database."""
        try:
            if self._cache is not None:
                logger.debug("Returning cached settings")
                return self._cache
            
            logger.debug("Fetching settings from database")
            result = await self.db.execute(select(Setting))
            db_settings = result.scalars().all()
            
            logger.debug(f"Found {len(db_settings)} settings in database")
            settings_dict = {}
            for setting in db_settings:
                settings_dict[setting.key] = self._parse_setting_value(setting.key, setting.value)
                logger.debug(f"Database setting: {setting.key} = {setting.value} (parsed: {self._parse_setting_value(setting.key, setting.value)})")
            
            self._cache = settings_dict
            logger.debug(f"Final settings dict: {settings_dict}")
            return settings_dict
        except Exception as e:
            logger.error(f"Error fetching all settings: {e}")
            return {}
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value from database."""
        try:
            # Try to get from database first
            result = await self.db.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                return self._parse_setting_value(key, setting.value)
            else:
                # Return default if not found in database
                return default
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return default
    
    async def set_setting(self, key: str, value: Any) -> bool:
        """Set a setting value."""
        try:
            # Convert value to string for storage
            str_value = str(value)
            
            result = await self.db.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                # Update existing setting
                setting.value = str_value
            else:
                # Create new setting
                setting = Setting(key=key, value=str_value)
                self.db.add(setting)
            
            await self.db.commit()
            self._cache = None  # Clear cache
            logger.info(f"Setting {key} updated to {value}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error setting {key}: {e}")
            return False
    
    async def set_multiple_settings(self, settings: Dict[str, Any]) -> bool:
        """Set multiple settings at once."""
        try:
            for key, value in settings.items():
                str_value = str(value)
                
                result = await self.db.execute(
                    select(Setting).where(Setting.key == key)
                )
                setting = result.scalar_one_or_none()
                
                if setting:
                    setting.value = str_value
                else:
                    setting = Setting(key=key, value=str_value)
                    self.db.add(setting)
            
            await self.db.commit()
            self._cache = None  # Clear cache
            logger.info(f"Updated {len(settings)} settings")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error setting multiple settings: {e}")
            return False
    
    async def delete_setting(self, key: str) -> bool:
        """Delete a setting (resets to default)."""
        try:
            result = await self.db.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                await self.db.delete(setting)
                await self.db.commit()
                self._cache = None  # Clear cache
                logger.info(f"Setting {key} deleted")
                return True
            else:
                logger.warning(f"Setting {key} not found")
                return False
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting setting {key}: {e}")
            return False
    
    async def initialize_default_settings(self) -> bool:
        """Initialize database with default settings if empty."""
        try:
            # Check if settings table is empty
            result = await self.db.execute(select(Setting))
            existing_settings = result.scalars().all()
            
            if existing_settings:
                logger.info("Settings table already has data, skipping initialization")
                return True
            
            # Get schema with defaults
            schema = self._get_settings_schema()
            
            # Create default settings
            for key, metadata in schema.items():
                setting = Setting(key=key, value=str(metadata["default"]))
                self.db.add(setting)
            
            await self.db.commit()
            logger.info(f"Initialized {len(schema)} default settings")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error initializing default settings: {e}")
            return False
    
    # Schema and Metadata
    def get_settings_schema(self) -> Dict[str, Dict[str, Any]]:
        """Get the settings schema with metadata."""
        return {
            # Risk/Scoring Thresholds
            "put_delta_min": {
                "type": "float",
                "default": 0.25,
                "min": 0.0,
                "max": 1.0,
                "description": "Minimum delta for put options",
                "category": "Risk/Scoring Thresholds"
            },
            "put_delta_max": {
                "type": "float",
                "default": 0.35,
                "min": 0.0,
                "max": 1.0,
                "description": "Maximum delta for put options",
                "category": "Risk/Scoring Thresholds"
            },
            "ivr_min": {
                "type": "float",
                "default": 30.0,
                "min": 0.0,
                "max": 100.0,
                "description": "Minimum implied volatility rank",
                "category": "Risk/Scoring Thresholds"
            },
            "ivr_max": {
                "type": "float",
                "default": 60.0,
                "min": 0.0,
                "max": 100.0,
                "description": "Maximum implied volatility rank",
                "category": "Risk/Scoring Thresholds"
            },
            "min_oi": {
                "type": "int",
                "default": 500,
                "min": 0,
                "max": 100000,
                "description": "Minimum open interest",
                "category": "Risk/Scoring Thresholds"
            },
            "min_volume": {
                "type": "int",
                "default": 200,
                "min": 0,
                "max": 100000,
                "description": "Minimum volume",
                "category": "Risk/Scoring Thresholds"
            },
            "max_bid_ask_pct": {
                "type": "float",
                "default": 5.0,
                "min": 0.0,
                "max": 100.0,
                "description": "Maximum bid-ask spread percentage",
                "category": "Risk/Scoring Thresholds"
            },
            "annualized_min_pct": {
                "type": "float",
                "default": 20.0,
                "min": 0.0,
                "max": 100.0,
                "description": "Minimum annualized return percentage",
                "category": "Risk/Scoring Thresholds"
            },

            "top_universe_score": {
                "type": "int",
                "default": 50,
                "min": 10,
                "max": 500,
                "description": "Number of top-scored tickers to consider for recommendations",
                "category": "Universe Selection"
            },
            "min_score_threshold": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "description": "Minimum score threshold for recommendations",
                "category": "Risk/Scoring Thresholds"
            },
            "earnings_blackout_days": {
                "type": "int",
                "default": 7,
                "min": 0,
                "max": 30,
                "description": "Days to avoid trading around earnings",
                "category": "Risk/Scoring Thresholds"
            },
            
            # Trading Configuration
            "profit_target_pct": {
                "type": "float",
                "default": 70.0,
                "min": 0.0,
                "max": 100.0,
                "description": "Profit target percentage",
                "category": "Trading Configuration"
            },
            "time_decay_threshold_days": {
                "type": "int",
                "default": 7,
                "min": 1,
                "max": 30,
                "description": "Days before expiration to consider time decay",
                "category": "Trading Configuration"
            },
            "time_decay_premium_threshold_pct": {
                "type": "float",
                "default": 20.0,
                "min": 0.0,
                "max": 100.0,
                "description": "Premium threshold percentage for time decay",
                "category": "Trading Configuration"
            },
            "delta_threshold_close": {
                "type": "float",
                "default": 0.45,
                "min": 0.0,
                "max": 1.0,
                "description": "Delta threshold for closing positions",
                "category": "Trading Configuration"
            },
            "dte_min": {
                "type": "int",
                "default": 21,
                "min": 1,
                "max": 60,
                "description": "Minimum days to expiration for all options",
                "category": "Trading Configuration"
            },
            "dte_max": {
                "type": "int",
                "default": 35,
                "min": 1,
                "max": 60,
                "description": "Maximum days to expiration for all options",
                "category": "Trading Configuration"
            },
            "covered_call_delta_min": {
                "type": "float",
                "default": 0.20,
                "min": 0.0,
                "max": 1.0,
                "description": "Minimum delta for covered calls",
                "category": "Trading Configuration"
            },
            "covered_call_delta_max": {
                "type": "float",
                "default": 0.30,
                "min": 0.0,
                "max": 1.0,
                "description": "Maximum delta for covered calls",
                "category": "Trading Configuration"
            },
            "max_ticker_price": {
                "type": "float",
                "default": 500.0,
                "min": 1.0,
                "max": 10000.0,
                "description": "Maximum ticker price",
                "category": "Risk/Scoring Thresholds"
            }
        }
    
    # Utility Methods
    def clear_cache(self):
        """Clear the settings cache."""
        self._cache = None
    
    def _parse_setting_value(self, key: str, value: str) -> Any:
        """Parse setting value to appropriate type."""
        schema = self.get_settings_schema()
        if key not in schema:
            return value
        
        setting_type = schema[key]["type"]
        
        try:
            if setting_type == "int":
                return int(value)
            elif setting_type == "float":
                return float(value)
            elif setting_type == "bool":
                return value.lower() in ("true", "1", "yes", "on")
            else:
                return value
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse setting {key}={value}, using default")
            return schema[key]["default"]
    



# Convenience functions for easy access
async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    """Get a setting value from database with environment fallback."""
    settings_service = SettingsService(db)
    return await settings_service.get_setting(key, default)


async def get_all_settings(db: AsyncSession) -> dict:
    """Get all settings from database with environment fallback."""
    settings_service = SettingsService(db)
    return await settings_service.get_all_settings()

