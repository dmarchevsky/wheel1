"""Tradier API client for account operations (trading, positions, balances)."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings as env_settings


logger = logging.getLogger(__name__)


class TradierAPIError(Exception):
    """Custom exception for Tradier API errors."""
    pass


class TradierAccountClient:
    """Tradier API client focused on account operations."""
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the account client.
        
        Args:
            environment: "production" or "sandbox"
        """
        self.environment = environment
        
        if environment == "sandbox":
            self.base_url = env_settings.tradier_sandbox_base_url
            self.access_token = env_settings.tradier_sandbox_access_token
            self.account_id = env_settings.tradier_sandbox_account_id
        else:
            self.base_url = env_settings.tradier_base_url
            self.access_token = env_settings.tradier_access_token
            self.account_id = env_settings.tradier_account_id
        
        # Validate required configuration
        # For sandbox, we allow placeholder values during development
        if environment == "production":
            if not self.access_token or self.access_token == "REPLACE_ME":
                logger.error(f"Tradier {environment} access token not configured or set to placeholder value")
                raise ValueError(f"Tradier {environment} access token not properly configured")
            
            if not self.account_id or self.account_id == "REPLACE_ME":
                logger.error(f"Tradier {environment} account ID not configured or set to placeholder value")
                raise ValueError(f"Tradier {environment} account ID not properly configured")
        else:
            # For sandbox, just warn if not configured
            if not self.access_token or self.access_token == "REPLACE_ME":
                logger.warning(f"Tradier {environment} access token not configured - sandbox functionality will be limited")
            
            if not self.account_id or self.account_id == "REPLACE_ME":
                logger.warning(f"Tradier {environment} account ID not configured - sandbox functionality will be limited")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        logger.debug(f"Tradier account client initialized for {environment} with base URL: {self.base_url}")
        logger.debug(f"Tradier account ID: {self.account_id}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        # Check if credentials are properly configured before making requests
        if not self.access_token or self.access_token == "REPLACE_ME":
            raise TradierAPIError(f"Tradier {self.environment} access token not configured")
        
        if not self.account_id or self.account_id == "REPLACE_ME":
            raise TradierAPIError(f"Tradier {self.environment} account ID not configured")
        
        url = f"{self.base_url}{endpoint}"
        
        # Build full URL with parameters for logging
        full_url = url
        if params:
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"

        logger.debug(f"Tradier API request: {method} {full_url}")
        
        try:
            # Prepare request arguments
            request_kwargs = {
                "method": method,
                "url": url,
                "headers": self.headers,
            }
            
            if params:
                request_kwargs["params"] = params
            if data:
                request_kwargs["data"] = data
            
            response = await self.client.request(**request_kwargs)
            response.raise_for_status()
            
            # Check if response is empty
            response_text = response.text.strip()
            
            if not response_text:
                logger.warning(f"Empty response received for {method} {url}")
                return {}
            
            try:
                response_data = response.json()
                
                # Check for Tradier API errors
                if "errors" in response_data:
                    error_msg = response_data["errors"].get("error", "Unknown Tradier API error")
                    logger.error(f"Tradier API error: {error_msg}")
                    raise TradierAPIError(f"Tradier API error: {error_msg}")
                
                return response_data
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise TradierAPIError(f"Invalid JSON response: {e}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                logger.warning("Rate limited by Tradier API, waiting 2 seconds...")
                await asyncio.sleep(2)
                raise
            elif e.response.status_code in [301, 302, 303, 307, 308]:
                # Redirect error - this shouldn't happen with follow_redirects=True
                logger.error(f"Unexpected redirect response: {e.response.status_code}")
                raise TradierAPIError(f"Unexpected redirect: {e.response.status_code}")
            
            raise TradierAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
            
        except httpx.RequestError as e:
            raise TradierAPIError(f"Request error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected Tradier API error: {str(e)}")
            raise TradierAPIError(f"Unexpected error: {str(e)}")
    
    async def get_account_positions(self) -> List[Dict[str, Any]]:
        """Get account positions."""
        data = await self._make_request("GET", f"/accounts/{self.account_id}/positions")
        
        positions_data = data.get("positions", {})
        
        # Handle case where positions is "null" string or empty
        if positions_data == "null" or not positions_data:
            return []
        
        # Check if positions_data is directly a list (Tradier API format)
        if isinstance(positions_data, list):
            return positions_data
        
        # Handle nested structure: positions.position
        positions = positions_data.get("position", [])
        if not isinstance(positions, list):
            positions = [positions]
        
        return positions
    
    async def get_account_orders(self, include_tags: bool = False) -> List[Dict[str, Any]]:
        """Get account orders."""
        params = {"includeTags": str(include_tags).lower()}
        data = await self._make_request("GET", f"/accounts/{self.account_id}/orders", params)
        
        orders_data = data.get("orders", {})
        # Handle case where orders is "null" string
        if orders_data == "null" or not orders_data:
            return []
        
        orders = orders_data.get("order", [])
        if not isinstance(orders, list):
            orders = [orders]
        
        return orders
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order."""
        data = await self._make_request("POST", f"/accounts/{self.account_id}/orders", data=order_data)
        return data.get("order", {})
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        data = await self._make_request("GET", f"/accounts/{self.account_id}/orders/{order_id}")
        return data.get("order", {})
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        data = await self._make_request("DELETE", f"/accounts/{self.account_id}/orders/{order_id}")
        return data.get("order", {})
    
    async def get_account_balances(self) -> Dict[str, Any]:
        """Get account balances."""
        data = await self._make_request("GET", f"/accounts/{self.account_id}/balances")
        
        balances = data.get("balances", {})
        # Handle case where balances is "null" string
        if balances == "null":
            return {}
        
        return balances
    
    async def get_account_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get account history."""
        params = {
            "start": start_date,
            "end": end_date
        }
        data = await self._make_request("GET", f"/accounts/{self.account_id}/history", params)
        
        # Debug: Log the raw response from Tradier
        logger.info(f"DEBUG: Raw Tradier history response: {data}")
        
        # Handle empty or null responses
        if not data or "history" not in data:
            logger.info("DEBUG: No data or no history key in response, returning empty list")
            return []
        
        history_data = data.get("history", {})
        if not history_data:
            return []
        
        # Handle case where history is a string "null" instead of a dict
        if isinstance(history_data, str):
            logger.info(f"DEBUG: History data is a string: {history_data}")
            return []
        
        # Handle the event structure - it can be null, a string, a dict, or a list
        events = history_data.get("event", [])
        
        # If events is None or empty string, return empty list
        if not events:
            return []
        
        # If events is a string, it's likely an error message or null value, return empty list
        if isinstance(events, str):
            logger.warning(f"Unexpected string response for account history: {events}")
            return []
        
        # If events is a single dict, wrap it in a list
        if isinstance(events, dict):
            events = [events]
        
        # Ensure we return a list of dicts only
        return [event for event in events if isinstance(event, dict)]
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Tradier API connection with a simple request."""
        try:
            # Try to get account balances as a connection test
            data = await self.get_account_balances()
            return {
                "status": "success",
                "message": f"Tradier {self.environment} API connection working",
                "account_id": self.account_id,
                "base_url": self.base_url,
                "environment": self.environment
            }
        except Exception as e:
            logger.error(f"❌ Tradier {self.environment} API connection test failed: {e}")
            return {
                "status": "error",
                "message": f"Tradier {self.environment} API connection failed: {str(e)}",
                "account_id": self.account_id,
                "base_url": self.base_url,
                "environment": self.environment
            }
