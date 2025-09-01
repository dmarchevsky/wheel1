"""Financial Modeling Prep (FMP) API client for fetching company information."""

import logging
import httpx
from typing import Dict, Optional, Any
from config import settings

logger = logging.getLogger(__name__)


class FMPAPIClient:
    """Client for Financial Modeling Prep API to fetch company information."""
    
    def __init__(self):
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.api_key = settings.fmp_api_key if hasattr(settings, 'fmp_api_key') else None
        
    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company profile from FMP API including comprehensive company data."""
        try:
            if not self.api_key:
                logger.warning("FMP API key not configured, skipping company profile fetch")
                return None
                
            url = f"{self.base_url}/profile/{symbol.upper()}"
            params = {
                "apikey": self.api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        company = data[0]  # Take the first result
                        
                        return {
                            "name": company.get("companyName"),
                            "sector": company.get("sector"),
                            "industry": company.get("industry"),
                            "market_cap": company.get("mktCap"),
                            "beta": company.get("beta"),
                            "volume": company.get("volAvg"),
                            "price": company.get("price"),
                            "exchange": company.get("exchange"),
                            "description": company.get("description"),
                            "ceo": company.get("ceo"),
                            "website": company.get("website"),
                            "country": company.get("country"),
                            "employees": company.get("fullTimeEmployees"),
                            "pe_ratio": company.get("pe"),
                            "dividend_yield": company.get("lastDiv"),
                            "fifty_two_week_high": company.get("52WeekHigh"),
                            "fifty_two_week_low": company.get("52WeekLow")
                        }
                    else:
                        logger.warning(f"No company profile data found for {symbol}")
                        return None
                else:
                    logger.error(f"FMP API error for {symbol}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching FMP company profile for {symbol}: {e}")
            return None
    
    async def get_company_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote data for a company."""
        try:
            if not self.api_key:
                logger.warning("FMP API key not configured, skipping quote fetch")
                return None
                
            url = f"{self.base_url}/quote/{symbol.upper()}"
            params = {
                "apikey": self.api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        quote = data[0]
                        
                        return {
                            "current_price": quote.get("price"),
                            "change": quote.get("change"),
                            "change_percent": quote.get("changesPercentage"),
                            "day_low": quote.get("dayLow"),
                            "day_high": quote.get("dayHigh"),
                            "year_low": quote.get("yearLow"),
                            "year_high": quote.get("yearHigh"),
                            "market_cap": quote.get("marketCap"),
                            "pe_ratio": quote.get("pe"),
                            "eps": quote.get("eps"),
                            "volume": quote.get("volume"),
                            "avg_volume": quote.get("avgVolume"),
                            "open": quote.get("open"),
                            "previous_close": quote.get("previousClose"),
                            "beta": quote.get("beta")
                        }
                    else:
                        logger.warning(f"No quote data found for {symbol}")
                        return None
                else:
                    logger.error(f"FMP API quote error for {symbol}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching FMP quote for {symbol}: {e}")
            return None
    
    async def get_sp500_constituents(self) -> Optional[list]:
        """Get S&P 500 constituents from FMP API."""
        try:
            if not self.api_key:
                logger.warning("FMP API key not configured, skipping SP500 fetch")
                return None
                
            url = f"{self.base_url}/sp500_constituent"
            params = {
                "apikey": self.api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data:
                        # Extract just the symbols
                        symbols = [item.get("symbol") for item in data if item.get("symbol")]
                        logger.info(f"Fetched {len(symbols)} SP500 constituents from FMP")
                        return symbols
                    else:
                        logger.warning("No SP500 constituents data found")
                        return None
                else:
                    logger.error(f"FMP API SP500 error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching SP500 constituents from FMP: {e}")
            return None
    
    async def get_company_ratios(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get key financial ratios for a company."""
        try:
            if not self.api_key:
                logger.warning("FMP API key not configured, skipping ratios fetch")
                return None
                
            url = f"{self.base_url}/ratios/{symbol.upper()}"
            params = {
                "apikey": self.api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        ratios = data[0]  # Most recent ratios
                        
                        return {
                            "pe_ratio": ratios.get("priceEarningsRatio"),
                            "pb_ratio": ratios.get("priceToBookRatio"),
                            "ps_ratio": ratios.get("priceToSalesRatio"),
                            "debt_to_equity": ratios.get("debtEquityRatio"),
                            "current_ratio": ratios.get("currentRatio"),
                            "quick_ratio": ratios.get("quickRatio"),
                            "return_on_equity": ratios.get("returnOnEquity"),
                            "return_on_assets": ratios.get("returnOnAssets"),
                            "gross_profit_margin": ratios.get("grossProfitMargin"),
                            "operating_margin": ratios.get("operatingProfitMargin"),
                            "net_profit_margin": ratios.get("netProfitMargin")
                        }
                    else:
                        logger.warning(f"No ratios data found for {symbol}")
                        return None
                else:
                    logger.error(f"FMP API ratios error for {symbol}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching FMP ratios for {symbol}: {e}")
            return None
