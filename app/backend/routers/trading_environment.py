"""API router for trading environment management."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from services.trading_environment_service import trading_env, TradingEnvironment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading-environment", tags=["Trading Environment"])

class EnvironmentSwitch(BaseModel):
    environment: TradingEnvironment

class EnvironmentStatus(BaseModel):
    current_environment: TradingEnvironment
    available_environments: list[str]
    data_source: str
    account_operations: str

@router.get("/status", response_model=EnvironmentStatus)
async def get_environment_status():
    """Get current trading environment status."""
    try:
        info = trading_env.get_environment_info()
        return EnvironmentStatus(**info)
    except Exception as e:
        logger.error(f"Failed to get environment status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get environment status: {str(e)}")

@router.post("/switch")
async def switch_environment(request: EnvironmentSwitch):
    """Switch trading environment."""
    try:
        # Test connection to the target environment first
        test_result = await trading_env.test_environment_connection(request.environment)
        
        # Always allow switching, but warn if connection test fails
        trading_env.set_environment(request.environment)
        
        if test_result["status"] != "success":
            # Switch succeeded but connection test failed - this is OK for development
            logger.warning(f"Switched to {request.environment} but connection test failed: {test_result['message']}")
            return {
                "status": "success",
                "message": f"Switched to {request.environment} environment (⚠️ Connection test failed: {test_result['message']})",
                "environment": request.environment,
                "connection_test": test_result,
                "warning": f"Environment switched but not fully configured: {test_result['message']}"
            }
        
        return {
            "status": "success",
            "message": f"Successfully switched to {request.environment} environment",
            "environment": request.environment,
            "connection_test": test_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch environment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch environment: {str(e)}")

@router.post("/test/{environment}")
async def test_environment(environment: TradingEnvironment):
    """Test connection to a specific environment."""
    try:
        result = await trading_env.test_environment_connection(environment)
        return result
    except Exception as e:
        logger.error(f"Failed to test {environment} environment: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to test {environment} environment: {str(e)}"
        )
