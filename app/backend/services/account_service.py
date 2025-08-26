"""Account service for managing Tradier account information."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from config import settings
from clients.tradier import TradierClient

logger = logging.getLogger(__name__)


class AccountService:
    """Service for managing account information."""
    
    def __init__(self):
        self.tradier_client = TradierClient()
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Tradier."""
        try:
            logger.info("Fetching account information from Tradier...")
            
            # Get account balances
            balances = await self.tradier_client.get_account_balances()
            
            # Parse balance data
            account_info = self._parse_balance_data(balances)
            
            logger.info("Successfully fetched account information")
            return account_info
            
        except Exception as e:
            logger.error(f"Error fetching account information: {e}")
            # Return fallback data
            return {
                "account_number": settings.tradier_account_id,
                "total_value": 0.0,
                "cash": 0.0,
                "long_stock_value": 0.0,
                "short_stock_value": 0.0,
                "long_option_value": 0.0,
                "short_option_value": 0.0,
                "buying_power": 0.0,
                "day_trade_buying_power": 0.0,
                "equity": 0.0,
                "last_updated": datetime.now().isoformat()
            }
    
    def _parse_balance_data(self, balances: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance data from Tradier API response."""
        try:
            # Extract account number
            account_number = balances.get("account_number", settings.tradier_account_id)
            
            # Extract cash and buying power
            cash = float(balances.get("cash", {}).get("cash", 0))
            buying_power = float(balances.get("cash", {}).get("buying_power", 0))
            day_trade_buying_power = float(balances.get("cash", {}).get("day_trade_buying_power", 0))
            
            # Extract equity values
            equity = float(balances.get("account", {}).get("equity", 0))
            total_value = float(balances.get("account", {}).get("total_equity", 0))
            
            # Extract position values
            long_stock_value = float(balances.get("account", {}).get("long_market_value", 0))
            short_stock_value = float(balances.get("account", {}).get("short_market_value", 0))
            long_option_value = float(balances.get("account", {}).get("long_option_market_value", 0))
            short_option_value = float(balances.get("account", {}).get("short_option_market_value", 0))
            
            return {
                "account_number": account_number,
                "total_value": total_value,
                "cash": cash,
                "long_stock_value": long_stock_value,
                "short_stock_value": short_stock_value,
                "long_option_value": long_option_value,
                "short_option_value": short_option_value,
                "buying_power": buying_power,
                "day_trade_buying_power": day_trade_buying_power,
                "equity": equity,
                "last_updated": datetime.now().isoformat()
            }
            
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error parsing balance data: {e}")
            # Return fallback data
            return {
                "account_number": settings.tradier_account_id,
                "total_value": 0.0,
                "cash": 0.0,
                "long_stock_value": 0.0,
                "short_stock_value": 0.0,
                "long_option_value": 0.0,
                "short_option_value": 0.0,
                "buying_power": 0.0,
                "day_trade_buying_power": 0.0,
                "equity": 0.0,
                "last_updated": datetime.now().isoformat()
            }
