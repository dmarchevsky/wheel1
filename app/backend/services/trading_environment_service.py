"""Service for managing trading environment (production vs sandbox)."""

import logging
from typing import Literal
from clients.tradier import TradierClient, TradierDataManager
from clients.tradier_account import TradierAccountClient
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TradingEnvironment = Literal["production", "sandbox"]

class TradingEnvironmentService:
    """Service for managing trading environment switching."""
    
    def __init__(self):
        self._current_environment: TradingEnvironment = "production"
    
    @property
    def current_environment(self) -> TradingEnvironment:
        """Get the current trading environment."""
        return self._current_environment
    
    def set_environment(self, environment: TradingEnvironment) -> None:
        """
        Set the current trading environment.
        
        Args:
            environment: "production" or "sandbox"
        """
        if environment not in ["production", "sandbox"]:
            raise ValueError("Environment must be 'production' or 'sandbox'")
        
        self._current_environment = environment
        logger.info(f"Trading environment set to: {environment}")
    
    def get_tradier_client(self) -> TradierClient:
        """Get a Tradier client for the current environment."""
        return TradierClient(self._current_environment)
    
    def get_tradier_account_client(self) -> TradierAccountClient:
        """Get a Tradier account client for the current environment."""
        return TradierAccountClient(self._current_environment)
    
    def get_tradier_data_manager(self, db: AsyncSession) -> TradierDataManager:
        """Get a Tradier data manager for the current environment."""
        return TradierDataManager(db, self._current_environment)
    
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
    
    def get_environment_info(self) -> dict:
        """Get information about the current environment."""
        return {
            "current_environment": self._current_environment,
            "available_environments": ["production", "sandbox"],
            "data_source": "production",  # Data always comes from production
            "account_operations": self._current_environment
        }

# Global instance
trading_env = TradingEnvironmentService()
