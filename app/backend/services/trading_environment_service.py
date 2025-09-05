"""Service for managing trading environment (production vs sandbox)."""

import logging
from typing import Literal, Dict, Optional
from clients.tradier import TradierClient, TradierDataManager
from clients.tradier_account import TradierAccountClient
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TradingEnvironment = Literal["production", "sandbox"]

class TradingEnvironmentService:
    """Service for managing trading environment switching with session persistence."""
    
    def __init__(self):
        self._current_environment: TradingEnvironment = "production"
        self._session_environments: Dict[str, TradingEnvironment] = {}
    
    @property
    def current_environment(self) -> TradingEnvironment:
        """Get the current trading environment."""
        return self._current_environment
    
    def get_session_environment(self, session_id: Optional[str]) -> TradingEnvironment:
        """Get environment for a specific session, fallback to global."""
        if session_id and session_id in self._session_environments:
            return self._session_environments[session_id]
        return self._current_environment
    
    def set_environment(self, environment: TradingEnvironment, session_id: Optional[str] = None) -> None:
        """
        Set the current trading environment.
        
        Args:
            environment: "production" or "sandbox"
            session_id: Optional session ID for per-session environments
        """
        if environment not in ["production", "sandbox"]:
            raise ValueError("Environment must be 'production' or 'sandbox'")
        
        if session_id:
            self._session_environments[session_id] = environment
            logger.info(f"Trading environment set to: {environment} for session {session_id}")
        else:
            self._current_environment = environment
            logger.info(f"Global trading environment set to: {environment}")
    
    def get_tradier_client(self, session_id: Optional[str] = None) -> TradierClient:
        """Get a Tradier client for the current environment."""
        env = self.get_session_environment(session_id)
        return TradierClient(env)
    
    def get_tradier_account_client(self, session_id: Optional[str] = None) -> TradierAccountClient:
        """Get a Tradier account client for the current environment."""
        env = self.get_session_environment(session_id)
        return TradierAccountClient(env)
    
    def get_tradier_data_manager(self, db: AsyncSession, session_id: Optional[str] = None) -> TradierDataManager:
        """Get a Tradier data manager for the current environment."""
        env = self.get_session_environment(session_id)
        return TradierDataManager(db, env)
    
    async def test_environment_connection(self, environment: TradingEnvironment) -> dict:
        """
        Test connection to a specific environment.
        
        Args:
            environment: Environment to test
            
        Returns:
            Connection test result
        """
        try:
            async with TradierAccountClient(environment) as client:
                result = await client.test_connection()
                return result
        except Exception as e:
            logger.error(f"Failed to test {environment} environment: {e}")
            return {
                "status": "error",
                "message": f"Failed to test {environment} environment: {str(e)}",
                "environment": environment
            }
    
    def get_environment_info(self, session_id: Optional[str] = None) -> dict:
        """Get information about the current environment."""
        env = self.get_session_environment(session_id)
        return {
            "current_environment": env,
            "available_environments": ["production", "sandbox"],
            "data_source": "production",  # Data always comes from production
            "account_operations": env
        }

# Global instance
trading_env = TradingEnvironmentService()
