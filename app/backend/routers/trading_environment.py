"""API router for trading environment management."""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Literal, Optional
import hashlib
from services.trading_environment_service import trading_env, TradingEnvironment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading-environment", tags=["Trading Environment"])


def get_session_id(request: Request) -> Optional[str]:
    """Generate a session ID based on client information."""
    try:
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else ""
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        
        ip = forwarded_for if forwarded_for else client_ip
        session_data = f"{user_agent}:{ip}"
        session_id = hashlib.md5(session_data.encode()).hexdigest()[:16]
        
        # Check if frontend has an environment preference and sync it
        env_preference = request.headers.get("x-trading-environment")
        if env_preference and env_preference in ["production", "sandbox"]:
            trading_env.set_environment(env_preference, session_id)
        
        return session_id
    except Exception as e:
        logger.warning(f"Could not generate session ID: {e}")
        return None


class EnvironmentSwitch(BaseModel):
    environment: TradingEnvironment

class EnvironmentStatus(BaseModel):
    current_environment: TradingEnvironment
    available_environments: list[str]
    data_source: str
    account_operations: str

@router.get("/status", response_model=EnvironmentStatus)
async def get_environment_status(request: Request):
    """Get current trading environment status."""
    try:
        session_id = get_session_id(request)
        info = trading_env.get_environment_info(session_id)
        return EnvironmentStatus(**info)
    except Exception as e:
        logger.error(f"Failed to get environment status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get environment status: {str(e)}")

@router.post("/switch")
async def switch_environment(env_request: EnvironmentSwitch, request: Request):
    """Switch trading environment."""
    try:
        session_id = get_session_id(request)
        # Test connection to the target environment first
        test_result = await trading_env.test_environment_connection(env_request.environment)
        
        # Always allow switching, but warn if connection test fails
        trading_env.set_environment(env_request.environment, session_id)
        
        if test_result["status"] != "success":
            # Switch succeeded but connection test failed - this is OK for development
            logger.warning(f"Switched to {env_request.environment} but connection test failed: {test_result['message']} (session: {session_id})")
            return {
                "status": "success",
                "message": f"Switched to {env_request.environment} environment (⚠️ Connection test failed: {test_result['message']})",
                "environment": env_request.environment,
                "connection_test": test_result,
                "warning": f"Environment switched but not fully configured: {test_result['message']}"
            }
        
        return {
            "status": "success",
            "message": f"Successfully switched to {env_request.environment} environment",
            "environment": env_request.environment,
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
