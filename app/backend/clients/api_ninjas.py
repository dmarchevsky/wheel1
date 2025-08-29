"""API Ninjas client for fetching S&P 500 data."""

import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime

from config import settings
from utils.timezone import now_pacific

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
            logger.info(f"🏢 Getting company info for {ticker}...")
            
            # Try S&P 500 first (most comprehensive data)
            try:
                logger.info(f"🏢 Trying S&P 500 data for {ticker}...")
                companies = await self._make_request("/sp500", {"ticker": ticker})
                if companies and len(companies) > 0:
                    company_info = companies[0]
                    logger.info(f"✅ Found {ticker} in S&P 500 data: {company_info}")
                    return company_info
                else:
                    logger.info(f"📊 {ticker} not found in S&P 500 data")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get S&P 500 data for {ticker}: {e}")
            
            # Try market cap endpoint as fallback (might have basic company info)
            try:
                logger.info(f"🏢 Trying market cap data for {ticker}...")
                market_cap_data = await self._make_request("/marketcap", {"ticker": ticker})
                if market_cap_data and isinstance(market_cap_data, dict):
                    # Extract basic company info from market cap data
                    company_info = {
                        "ticker": market_cap_data.get("ticker"),
                        "company_name": market_cap_data.get("name"),
                        "sector": market_cap_data.get("sector"),  # If available
                        "sub_industry": market_cap_data.get("industry")  # If available
                    }
                    logger.info(f"✅ Found {ticker} in market cap data: {company_info}")
                    return company_info
                else:
                    logger.info(f"📊 {ticker} not found in market cap data")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get market cap data for {ticker}: {e}")
            
            logger.warning(f"⚠️ No company info found for {ticker} from any source")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get company info for {ticker}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return None
    
    async def get_earnings_calendar(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get earnings calendar data for a ticker using API Ninjas."""
        try:
            logger.info(f"📅 Getting earnings calendar for {ticker} with show_upcoming=true")
            
            # Get upcoming earnings dates
            params = {
                "ticker": ticker,
                "show_upcoming": "true"
            }
            logger.info(f"📅 API Ninjas earnings calendar params: {params}")
            
            earnings_data = await self._make_request("/earningscalendar", params)
            
            if earnings_data and len(earnings_data) > 0:
                logger.info(f"📅 Received {len(earnings_data)} earnings records for {ticker}")
                
                # Find the earliest upcoming earnings date
                from datetime import datetime
                current_date = now_pacific().date()
                upcoming_earnings = []
                
                # First pass: collect all upcoming earnings dates
                for i, earnings in enumerate(earnings_data):
                    earnings_date_str = earnings.get("date")
                    if earnings_date_str:
                        try:
                            earnings_date = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
                            logger.debug(f"📅 Earnings record {i+1}: {earnings_date_str} (parsed: {earnings_date})")
                            
                            if earnings_date > current_date:
                                upcoming_earnings.append({
                                    "earnings": earnings,
                                    "date": earnings_date,
                                    "index": i
                                })
                                logger.debug(f"📅 Found upcoming earnings: {earnings_date}")
                        except ValueError as e:
                            logger.warning(f"⚠️ Failed to parse earnings date '{earnings_date_str}' for {ticker}: {e}")
                            continue
                
                # Find the earliest upcoming earnings date
                if upcoming_earnings:
                    # Sort by date to find the earliest
                    upcoming_earnings.sort(key=lambda x: x["date"])
                    earliest_earnings = upcoming_earnings[0]
                    
                    logger.info(f"✅ Found earliest upcoming earnings date for {ticker}: {earliest_earnings['date']}")
                    logger.info(f"📊 Earnings details: EPS est={earliest_earnings['earnings'].get('estimated_eps')}, revenue est={earliest_earnings['earnings'].get('estimated_revenue')}")
                    
                    # Log all upcoming dates for reference
                    if len(upcoming_earnings) > 1:
                        logger.info(f"📅 All upcoming earnings dates for {ticker}: {[e['date'] for e in upcoming_earnings]}")
                    
                    return {
                        "earnings_date": earliest_earnings["date"],
                        "estimated_eps": earliest_earnings["earnings"].get("estimated_eps"),
                        "actual_eps": earliest_earnings["earnings"].get("actual_eps"),
                        "estimated_revenue": earliest_earnings["earnings"].get("estimated_revenue"),
                        "actual_revenue": earliest_earnings["earnings"].get("actual_revenue")
                    }
                else:
                    logger.info(f"📅 No upcoming earnings found for {ticker} (all dates are in the past)")
                    return None
            else:
                logger.info(f"📅 No earnings data returned for {ticker}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get earnings calendar for {ticker}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
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
    

