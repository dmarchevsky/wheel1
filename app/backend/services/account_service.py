"""Account service for managing Tradier account information."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional


from config import settings
from clients.tradier import TradierClient
from services.trading_environment_service import trading_env

logger = logging.getLogger(__name__)


class AccountService:
    """Service for managing account information."""
    
    def __init__(self):
        pass
    
    def _get_tradier_client(self) -> TradierClient:
        """Get Tradier client for current environment."""
        return trading_env.get_tradier_client()
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Tradier."""
        try:
            logger.info(f"Fetching account information from Tradier ({trading_env.current_environment})...")
            
            # Get environment-aware Tradier client
            async with self._get_tradier_client() as tradier_client:
                # Get account balances
                balances = await tradier_client.get_account_balances()
                
                # Log raw response for debugging
                logger.info(f"Raw Tradier balances response: {balances}")
                
                # Parse balance data
                account_info = self._parse_balance_data(balances)
                
                logger.info(f"Parsed account info: {account_info}")
                return account_info
            
        except Exception as e:
            logger.error(f"Error fetching account information: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return empty data with error context
            current_env = trading_env.current_environment
            return {
                "account_number": trading_env.get_tradier_client().account_id,
                "total_value": 0.0,
                "cash": 0.0,
                "long_stock_value": 0.0,
                "short_stock_value": 0.0,
                "long_option_value": 0.0,
                "short_option_value": 0.0,
                "buying_power": 0.0,
                "day_trade_buying_power": 0.0,
                "equity": 0.0,
                "last_updated": datetime.now().isoformat(),
                "_error_message": f"Failed to fetch account data from {current_env} environment: {str(e)}"
            }
    
    def _parse_balance_data(self, balances: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance data from Tradier API response."""
        try:
            # Extract account number
            account_number = balances.get("account_number", trading_env.get_tradier_client().account_id)
            
            # Extract cash values (direct from balances object)
            cash = float(balances.get("total_cash", 0))
            
            # Extract equity values (direct from balances object)
            equity = float(balances.get("equity", 0))
            total_value = float(balances.get("total_equity", 0))
            
            # Extract position values (direct from balances object)
            long_stock_value = float(balances.get("long_market_value", 0))
            short_stock_value = float(balances.get("short_market_value", 0))
            long_option_value = float(balances.get("option_long_value", 0))
            short_option_value = float(balances.get("option_short_value", 0))
            
            # Extract buying power from margin object
            margin = balances.get("margin", {})
            buying_power = float(margin.get("stock_buying_power", 0))
            day_trade_buying_power = float(margin.get("option_buying_power", 0))
            
            logger.info(f"Parsed values - Cash: {cash}, Total Value: {total_value}, Equity: {equity}")
            logger.info(f"Stock values - Long: {long_stock_value}, Short: {short_stock_value}")
            logger.info(f"Option values - Long: {long_option_value}, Short: {short_option_value}")
            logger.info(f"Buying power - Stock: {buying_power}, Options: {day_trade_buying_power}")
            
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
            logger.error(f"Raw balances data: {balances}")
            # Return fallback data
            return {
                "account_number": trading_env.get_tradier_client().account_id,
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
