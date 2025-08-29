"""Settings API endpoints."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from db.session import get_async_db
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


class SettingSchema(BaseModel):
    """Setting schema response model."""
    key: str
    type: str
    default: Any
    min: Any = None
    max: Any = None
    description: str
    category: str


class SettingValue(BaseModel):
    """Setting value model."""
    value: Any


class SettingsResponse(BaseModel):
    """Settings response model."""
    settings: Dict[str, Any]
    schema: Dict[str, SettingSchema]


class UpdateSettingsRequest(BaseModel):
    """Update settings request model."""
    settings: Dict[str, Any]


@router.get("/", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_async_db)
):
    """Get all settings and their schema."""
    try:
        settings_service = SettingsService(db)
        
        # Get current settings values
        settings = await settings_service.get_all_settings()
        
        # Get settings schema
        schema_dict = settings_service.get_settings_schema()
        
        # Convert schema to response format
        schema_response = {}
        for key, metadata in schema_dict.items():
            schema_response[key] = SettingSchema(
                key=key,
                type=metadata["type"],
                default=metadata["default"],
                min=metadata.get("min"),
                max=metadata.get("max"),
                description=metadata["description"],
                category=metadata["category"]
            )
        
        return SettingsResponse(
            settings=settings,
            schema=schema_response
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch settings")


@router.get("/schema", response_model=Dict[str, SettingSchema])
async def get_settings_schema(
    db: AsyncSession = Depends(get_async_db)
):
    """Get settings schema with metadata."""
    try:
        settings_service = SettingsService(db)
        schema_dict = settings_service.get_settings_schema()
        
        # Convert to response format
        schema_response = {}
        for key, metadata in schema_dict.items():
            schema_response[key] = SettingSchema(
                key=key,
                type=metadata["type"],
                default=metadata["default"],
                min=metadata.get("min"),
                max=metadata.get("max"),
                description=metadata["description"],
                category=metadata["category"]
            )
        
        return schema_response
    except Exception as e:
        logger.error(f"Error fetching settings schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch settings schema")


@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific setting value."""
    try:
        settings_service = SettingsService(db)
        value = await settings_service.get_setting(key)
        
        if value is None:
            raise HTTPException(status_code=404, detail=f"Setting {key} not found")
        
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching setting {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch setting")


@router.put("/{key}")
async def update_setting(
    key: str,
    setting_data: SettingValue,
    db: AsyncSession = Depends(get_async_db)
):
    """Update a specific setting value."""
    try:
        settings_service = SettingsService(db)
        
        # Validate the setting exists in schema
        schema = settings_service.get_settings_schema()
        if key not in schema:
            raise HTTPException(status_code=400, detail=f"Invalid setting key: {key}")
        
        # Validate value range
        metadata = schema[key]
        value = setting_data.value
        
        # Type validation
        try:
            if metadata["type"] == "int":
                value = int(value)
            elif metadata["type"] == "float":
                value = float(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid value type for {key}. Expected {metadata['type']}"
            )
        
        # Range validation
        if metadata.get("min") is not None and value < metadata["min"]:
            raise HTTPException(
                status_code=400,
                detail=f"Value for {key} must be >= {metadata['min']}"
            )
        
        if metadata.get("max") is not None and value > metadata["max"]:
            raise HTTPException(
                status_code=400,
                detail=f"Value for {key} must be <= {metadata['max']}"
            )
        
        # Update setting
        success = await settings_service.set_setting(key, value)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update setting")
        
        return {"key": key, "value": value, "message": "Setting updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update setting")


@router.put("/", response_model=Dict[str, Any])
async def update_multiple_settings(
    request: UpdateSettingsRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Update multiple settings at once."""
    try:
        settings_service = SettingsService(db)
        schema = settings_service.get_settings_schema()
        
        # Validate all settings
        validated_settings = {}
        for key, value in request.settings.items():
            if key not in schema:
                raise HTTPException(status_code=400, detail=f"Invalid setting key: {key}")
            
            metadata = schema[key]
            
            # Type validation
            try:
                if metadata["type"] == "int":
                    validated_value = int(value)
                elif metadata["type"] == "float":
                    validated_value = float(value)
                else:
                    validated_value = value
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid value type for {key}. Expected {metadata['type']}"
                )
            
            # Range validation
            if metadata.get("min") is not None and validated_value < metadata["min"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Value for {key} must be >= {metadata['min']}"
                )
            
            if metadata.get("max") is not None and validated_value > metadata["max"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Value for {key} must be <= {metadata['max']}"
                )
            
            validated_settings[key] = validated_value
        
        # Update settings
        success = await settings_service.set_multiple_settings(validated_settings)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update settings")
        
        return {
            "message": f"Updated {len(validated_settings)} settings successfully",
            "updated_settings": validated_settings
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating multiple settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a setting (resets to default)."""
    try:
        settings_service = SettingsService(db)
        
        # Get schema to find default value
        schema = settings_service.get_settings_schema()
        if key not in schema:
            raise HTTPException(status_code=400, detail=f"Invalid setting key: {key}")
        
        # Delete the setting (it will fall back to environment/default)
        success = await settings_service.delete_setting(key)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete setting")
        
        # Return the default value
        default_value = schema[key]["default"]
        
        return {
            "key": key,
            "value": default_value,
            "message": "Setting deleted and reset to default"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete setting")


@router.post("/initialize")
async def initialize_settings(
    db: AsyncSession = Depends(get_async_db)
):
    """Initialize database with default settings."""
    try:
        settings_service = SettingsService(db)
        success = await settings_service.initialize_default_settings()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to initialize settings")
        
        return {"message": "Settings initialized successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize settings")
