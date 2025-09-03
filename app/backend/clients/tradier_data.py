"""Tradier API client for data gathering operations (market data, quotes, options)."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings as env_settings


logger = logging.getLogger(__name__)


class TradierAPIError(Exception):
    """Custom exception for Tradier API errors."""
    pass


class TradierDataClient:
    """Tradier API client focused on data gathering operations."""
    
    def __init__(self, base_url: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize the data client.
        
        Args:
            base_url: API base URL (defaults to production)
            access_token: Access token (defaults to production token)
        """
        self.base_url = base_url or env_settings.tradier_base_url
        self.access_token = access_token or env_settings.tradier_access_token
        
        # Validate required configuration
        if not self.access_token or self.access_token == "REPLACE_ME":
            logger.error("Tradier access token not configured or set to placeholder value")
            raise ValueError("Tradier access token not properly configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        logger.debug(f"Tradier data client initialized with base URL: {self.base_url}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        # Use provided base_url or default to self.base_url
        request_base_url = base_url if base_url else self.base_url
        url = f"{request_base_url}{endpoint}"
        
        # Build full URL with parameters for logging
        full_url = url
        if params:
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"

        logger.debug(f"Tradier API request: {method} {full_url}")
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            
            response.raise_for_status()
            
            # Check if response is empty
            response_text = response.text.strip()
            
            if not response_text:
                logger.warning(f"Empty response received for {method} {url}")
                return {}
            
            try:
                data = response.json()
                
                # Check for Tradier API errors
                if "errors" in data:
                    error_msg = data["errors"].get("error", "Unknown Tradier API error")
                    logger.error(f"Tradier API error: {error_msg}")
                    raise TradierAPIError(f"Tradier API error: {error_msg}")
                
                return data
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
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a symbol."""
        params = {"symbols": symbol}
        data = await self._make_request("GET", "/markets/quotes", params)
        quote_data = data.get("quotes", {}).get("quote", {})
        return quote_data
    
    async def get_options_chain(self, symbol: str, expiration: str) -> List[Dict[str, Any]]:
        """Get options chain for a symbol and expiration."""
        params = {
            "symbol": symbol,
            "expiration": expiration,
            "greeks": "true"  # Request greeks data
        }
        data = await self._make_request("GET", "/markets/options/chains", params)
        
        # Debug: Log the raw response to see what we're getting
        logger.info(f"🔍 Raw Tradier API response for {symbol} {expiration}: {data}")
        
        options = data.get("options", {}).get("option", [])
        if not isinstance(options, list):
            options = [options]
        
        # Debug: Check if any options have greeks data
        greeks_count = 0
        for opt in options:
            if opt.get("greeks"):
                greeks_count += 1
        logger.info(f"📊 Found {greeks_count} options with greeks data out of {len(options)} total options")
        
        return options
    
    async def get_option_strikes(self, symbol: str, expiration: str) -> List[float]:
        """Get available strikes for a symbol and expiration."""
        params = {
            "symbol": symbol,
            "expiration": expiration
        }
        data = await self._make_request("GET", "/markets/options/strikes", params)
        
        strikes = data.get("strikes", {}).get("strike", [])
        if not isinstance(strikes, list):
            strikes = [strikes]
        
        float_strikes = [float(s) for s in strikes]
        return float_strikes
    
    async def get_option_expirations(self, symbol: str) -> List[str]:
        """Get available expirations for a symbol."""
        params = {"symbol": symbol}
        data = await self._make_request("GET", "/markets/options/expirations", params)
        
        expirations = data.get("expirations", {}).get("date", [])
        if not isinstance(expirations, list):
            expirations = [expirations]
        
        return expirations
    
    async def get_fundamentals_company(self, symbol: str) -> Dict[str, Any]:
        """Get company fundamental data from Tradier API beta endpoint."""
        params = {"symbols": symbol}
        try:
            # Use beta base URL for fundamentals endpoints
            beta_url = "https://api.tradier.com/beta"
            data = await self._make_request("GET", "/markets/fundamentals/company", params, base_url=beta_url)
            return data
        except Exception as e:
            logger.error(f"❌ Failed to get company fundamentals for {symbol}: {e}")
            return {}
    
    async def get_fundamentals_ratios(self, symbol: str) -> Dict[str, Any]:
        """Get financial ratios from Tradier API beta endpoint."""
        params = {"symbols": symbol}
        try:
            # Use beta base URL for fundamentals endpoints
            beta_url = "https://api.tradier.com/beta"
            data = await self._make_request("GET", "/markets/fundamentals/ratios", params, base_url=beta_url)
            return data
        except Exception as e:
            logger.error(f"❌ Failed to get financial ratios for {symbol}: {e}")
            return {}
