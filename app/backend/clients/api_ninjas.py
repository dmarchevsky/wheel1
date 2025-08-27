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
    
    async def get_earnings_calendar(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get earnings calendar data for a ticker using API Ninjas."""
        try:
            # Get upcoming earnings dates
            earnings_data = await self._make_request("/earningscalendar", {
                "ticker": ticker,
                "show_upcoming": "true"
            })
            
            if earnings_data and len(earnings_data) > 0:
                # Find the next upcoming earnings date
                from datetime import datetime
                current_date = datetime.utcnow().date()
                
                for earnings in earnings_data:
                    earnings_date_str = earnings.get("date")
                    if earnings_date_str:
                        try:
                            earnings_date = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
                            if earnings_date > current_date:
                                logger.info(f"Found next earnings date for {ticker}: {earnings_date}")
                                return {
                                    "earnings_date": earnings_date,
                                    "estimated_eps": earnings.get("estimated_eps"),
                                    "actual_eps": earnings.get("actual_eps"),
                                    "estimated_revenue": earnings.get("estimated_revenue"),
                                    "actual_revenue": earnings.get("actual_revenue")
                                }
                        except ValueError:
                            continue
                
                logger.debug(f"No upcoming earnings found for {ticker}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get earnings calendar for {ticker}: {e}")
            return None
    
    async def get_market_cap(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get market cap data for a ticker using API Ninjas."""
        try:
            # Get market cap data
            market_cap_data = await self._make_request("/marketcap", {"ticker": ticker})
            
            if market_cap_data and isinstance(market_cap_data, dict):
                # Convert market cap from USD to billions for consistency
                market_cap_usd = market_cap_data.get("market_cap")
                if market_cap_usd:
                    market_cap_billions = float(market_cap_usd) / 1e9
                    logger.info(f"Got market cap for {ticker}: ${market_cap_billions:.1f}B")
                    return {
                        "ticker": market_cap_data.get("ticker"),
                        "name": market_cap_data.get("name"),
                        "market_cap": market_cap_billions,  # In billions
                        "market_cap_usd": market_cap_usd,   # Original USD value
                        "updated": market_cap_data.get("updated")
                    }
                else:
                    logger.warning(f"No market cap data found for {ticker}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market cap for {ticker}: {e}")
            return None
    

