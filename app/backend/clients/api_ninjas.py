"""API Ninjas client for fetching S&P 500 data."""

import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)


class APINinjasError(Exception):
    """Custom exception for API Ninjas errors."""
    pass


class APINinjasClient:
    """API Ninjas client for fetching S&P 500 data."""
    
    def __init__(self):
        self.base_url = "https://api.api-ninjas.com/v1"
        self.api_key = settings.api_ninjas_api_key
        self.headers = {
            "X-Api-Key": self.api_key,
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        logger.info(f"Making API Ninjas request: GET {url}")
        if params:
            logger.info(f"Request params: {params}")
        
        try:
            response = await self.client.get(
                url=url,
                headers=self.headers,
                params=params
            )
            
            logger.info(f"API Ninjas response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"API Ninjas response data length: {len(data) if data else 0}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"API Ninjas HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                logger.warning("Rate limited by API Ninjas, waiting 2 seconds...")
                await asyncio.sleep(2)
                raise
            raise APINinjasError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"API Ninjas request error: {str(e)}")
            raise APINinjasError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in API Ninjas request: {str(e)}")
            raise APINinjasError(f"Unexpected error: {str(e)}")
    
    async def get_sp500_companies(self) -> List[Dict[str, Any]]:
        """Get current S&P 500 companies with sector information."""
        try:
            data = await self._make_request("/sp500")
            logger.info(f"Successfully fetched {len(data)} S&P 500 companies from API Ninjas")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 companies from API Ninjas: {e}")
            raise
    
    async def get_sp500_tickers(self) -> List[str]:
        """Get list of S&P 500 ticker symbols."""
        try:
            companies = await self.get_sp500_companies()
            tickers = [company["ticker"] for company in companies if company.get("ticker")]
            logger.info(f"Extracted {len(tickers)} ticker symbols from S&P 500 data")
            return tickers
        except Exception as e:
            logger.error(f"Failed to extract ticker symbols: {e}")
            raise
    
    async def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get specific company information by ticker."""
        try:
            companies = await self._make_request("/sp500", {"ticker": ticker})
            if companies and len(companies) > 0:
                return companies[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get company info for {ticker}: {e}")
            return None
