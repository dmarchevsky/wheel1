"""Tradier API client with retry logic and rate limiting."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Option, Ticker, Position, OptionPosition, Trade, EarningsCalendar
from clients.api_ninjas import APINinjasClient

logger = logging.getLogger(__name__)


class TradierAPIError(Exception):
    """Custom exception for Tradier API errors."""
    pass


class TradierClient:
    """Tradier API client with retry logic and rate limiting."""
    
    def __init__(self):
        self.base_url = settings.tradier_base_url
        self.access_token = settings.tradier_access_token
        self.account_id = settings.tradier_account_id
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
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
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        logger.info(f"Making Tradier API request: {method} {url}")
        if params:
            logger.info(f"Request params: {params}")
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            
            logger.info(f"Tradier API response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Tradier API response data keys: {list(data.keys()) if data else 'None'}")
            
            # Check for Tradier API errors
            if "errors" in data:
                error_msg = data["errors"].get("error", "Unknown Tradier API error")
                logger.error(f"Tradier API error: {error_msg}")
                raise TradierAPIError(f"Tradier API error: {error_msg}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Tradier API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                logger.warning("Rate limited by Tradier API, waiting 2 seconds...")
                await asyncio.sleep(2)
                raise
            raise TradierAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Tradier API request error: {str(e)}")
            raise TradierAPIError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Tradier API request: {str(e)}")
            raise TradierAPIError(f"Unexpected error: {str(e)}")
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a symbol."""
        params = {"symbols": symbol}
        data = await self._make_request("GET", "/markets/quotes", params)
        return data.get("quotes", {}).get("quote", {})
    
    async def get_options_chain(self, symbol: str, expiration: str) -> List[Dict[str, Any]]:
        """Get options chain for a symbol and expiration."""
        params = {
            "symbol": symbol,
            "expiration": expiration
        }
        data = await self._make_request("GET", "/markets/options/chains", params)
        
        options = data.get("options", {}).get("option", [])
        if not isinstance(options, list):
            options = [options]
        
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
        
        return [float(s) for s in strikes]
    
    async def get_option_expirations(self, symbol: str) -> List[str]:
        """Get available expirations for a symbol."""
        params = {"symbol": symbol}
        data = await self._make_request("GET", "/markets/options/expirations", params)
        
        expirations = data.get("expirations", {}).get("date", [])
        if not isinstance(expirations, list):
            expirations = [expirations]
        
        return expirations
    
    async def get_account_positions(self) -> List[Dict[str, Any]]:
        """Get account positions."""
        data = await self._make_request("GET", f"/accounts/{self.account_id}/positions")
        
        positions_data = data.get("positions", {})
        # Handle case where positions is "null" string
        if positions_data == "null" or not positions_data:
            return []
        
        positions = positions_data.get("position", [])
        if not isinstance(positions, list):
            positions = [positions]
        
        return positions
    
    async def get_account_orders(self, include_tags: bool = False) -> List[Dict[str, Any]]:
        """Get account orders."""
        params = {"includeTags": str(include_tags).lower()}
        data = await self._make_request("GET", f"/accounts/{self.account_id}/orders", params)
        
        orders = data.get("orders", {}).get("order", [])
        if not isinstance(orders, list):
            orders = [orders]
        
        return orders
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order."""
        data = await self._make_request("POST", f"/accounts/{self.account_id}/orders", order_data)
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
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Making Tradier API request to: /accounts/{self.account_id}/balances")
        data = await self._make_request("GET", f"/accounts/{self.account_id}/balances")
        logger.info(f"Tradier API response: {data}")
        
        balances = data.get("balances", {})
        # Handle case where balances is "null" string
        if balances == "null":
            logger.warning("Tradier returned 'null' for balances")
            return {}
        
        logger.info(f"Extracted balances: {balances}")
        return balances
    
    async def get_account_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get account history."""
        params = {
            "start": start_date,
            "end": end_date
        }
        data = await self._make_request("GET", f"/accounts/{self.account_id}/history", params)
        
        history = data.get("history", {}).get("event", [])
        if not isinstance(history, list):
            history = [history]
        
        return history
    
    async def get_fundamentals_company(self, symbol: str) -> Dict[str, Any]:
        """Get company fundamental data from Tradier API beta endpoint."""
        params = {"symbols": symbol}
        # Only beta endpoint provides fundamentals data
        data = await self._make_request("GET", "/beta/markets/fundamentals/company", params)
        return data
    
    async def get_fundamentals_ratios(self, symbol: str) -> Dict[str, Any]:
        """Get financial ratios from Tradier API beta endpoint."""
        params = {"symbols": symbol}
        # Only beta endpoint provides ratios data
        data = await self._make_request("GET", "/beta/markets/fundamentals/ratios", params)
        return data
    
    async def get_earnings_calendar(self, symbol: str) -> Dict[str, Any]:
        """Get earnings calendar data for a symbol from Tradier API beta endpoint."""
        params = {"symbols": symbol}
        # Only beta endpoint provides earnings calendar data
        data = await self._make_request("GET", "/beta/markets/fundamentals/calendar", params)
        return data
    
    async def get_sp500_constituents(self) -> List[str]:
        """Get current S&P 500 constituents list using API Ninjas."""
        try:
            # Use API Ninjas to get current S&P 500 constituents
            tickers = await self.api_ninjas.get_sp500_tickers()
            
            if tickers and len(tickers) > 400:  # SP500 should have ~500 constituents
                logger.info(f"Found {len(tickers)} SP500 constituents via API Ninjas")
                return tickers
            
            # Fallback to comprehensive list if API Ninjas fails
            logger.warning("API Ninjas failed, using comprehensive SP500 fallback list")
            return self._get_comprehensive_sp500_list()
            
        except Exception as e:
            logger.error(f"Error fetching SP500 constituents from API Ninjas: {e}")
            logger.warning("Using comprehensive SP500 fallback list")
            return self._get_comprehensive_sp500_list()
    
    def _map_morningstar_sector_code(self, sector_code: int) -> str:
        """Map Morningstar sector codes to readable sector names."""
        sector_mapping = {
            -1: "Misc",
            101: "Basic Materials",
            102: "Consumer Cyclical",
            103: "Financial Services",
            104: "Real Estate",
            205: "Consumer Defensive",
            206: "Healthcare",
            207: "Utilities",
            308: "Communication Services",
            309: "Energy",
            310: "Industrials",
            311: "Technology"
        }
        return sector_mapping.get(sector_code, f"Unknown_Sector_{sector_code}")
    
    def _get_comprehensive_sp500_list(self) -> List[str]:
        """Fallback list of major S&P 500 stocks (used when API Ninjas fails)."""
        # This is a minimal fallback list - API Ninjas should provide the full list
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "LLY", "V",
            "UNH", "XOM", "JNJ", "WMT", "JPM", "PG", "MA", "HD", "CVX", "AVGO",
            "ABBV", "PFE", "KO", "BAC", "PEP", "COST", "TMO", "ACN", "DHR", "VZ",
            "MRK", "ABT", "WFC", "CMCSA", "ADBE", "NFLX", "CRM", "PM", "TXN", "NEE",
            "RTX", "HON", "QCOM", "LOW", "UNP", "UPS", "IBM", "MS", "BMY", "CAT",
            "GS", "AMAT", "SPGI", "INTU", "AXP", "GILD", "ISRG", "VRTX", "ADI", "TGT"
        ]


class TradierDataManager:
    """Manages Tradier data synchronization with database."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = TradierClient()
        self.api_ninjas = APINinjasClient()
    
    async def sync_ticker_data(self, symbol: str) -> Ticker:
        """Sync comprehensive ticker data from Tradier API including fundamentals."""
        try:
            # Get quote data from Tradier API
            quote_data = None
            try:
                quote_data = await self.client.get_quote(symbol)
                logger.info(f"Successfully got Tradier quote data for {symbol}")
            except Exception as e:
                logger.warning(f"Tradier quote data failed for {symbol}: {e}")
                quote_data = None
            
            # Get fundamental data (with fallback handling)
            fundamentals_data = None
            ratios_data = None
            try:
                fundamentals_data = await self.client.get_fundamentals_company(symbol)
            except Exception as e:
                logger.warning(f"Failed to get fundamentals data for {symbol}: {e}")
            
            try:
                ratios_data = await self.client.get_fundamentals_ratios(symbol)
            except Exception as e:
                logger.warning(f"Failed to get ratios data for {symbol}: {e}")
            
            # Get or create ticker
            result = await self.db.execute(
                select(Ticker).where(Ticker.symbol == symbol)
            )
            ticker = result.scalar_one_or_none()
            if not ticker:
                ticker = Ticker(symbol=symbol)
                self.db.add(ticker)
            
            # Update comprehensive quote data
            if quote_data:
                # Basic price data
                ticker.current_price = float(quote_data.get("last", 0)) if quote_data.get("last") else None
                ticker.name = quote_data.get("description", ticker.name)
                
                # Volume data
                volume = int(quote_data.get("volume", 0)) if quote_data.get("volume") else None
                if volume:
                    ticker.volume_avg_20d = volume  # Use current volume as approximation
                
                # Calculate volatility from 52-week range
                week_52_high = float(quote_data.get("week_52_high", 0)) if quote_data.get("week_52_high") else None
                week_52_low = float(quote_data.get("week_52_low", 0)) if quote_data.get("week_52_low") else None
                if week_52_high and week_52_low and ticker.current_price:
                    # Calculate 30-day volatility approximation using 52-week range
                    price_range = week_52_high - week_52_low
                    mid_price = (week_52_high + week_52_low) / 2
                    if mid_price > 0:
                        # Approximate volatility as percentage of mid-price
                        ticker.volatility_30d = (price_range / mid_price) * 100
            
            # Extract fundamental data
            if fundamentals_data and isinstance(fundamentals_data, list) and len(fundamentals_data) > 0:
                for item in fundamentals_data:
                    if item.get("type") == "Company" and item.get("tables"):
                        tables = item["tables"]
                        
                        # Company profile
                        if "company_profile" in tables and tables["company_profile"]:
                            profile = tables["company_profile"]
                            # Could extract employee count, contact info, etc.
                        
                        # Asset classification (industry/sector)
                        if "asset_classification" in tables and tables["asset_classification"]:
                            classification = tables["asset_classification"]
                            # Map Morningstar sector codes to readable sector names
                            sector_code = classification.get('morningstar_sector_code')
                            if sector_code:
                                ticker.sector = self._map_morningstar_sector_code(sector_code)
                                logger.info(f"Mapped sector for {symbol}: {ticker.sector}")
                            
                            # Map Morningstar industry codes to readable industry names
                            industry_code = classification.get('morningstar_industry_code')
                            if industry_code:
                                ticker.industry = f"Industry_{industry_code}"
                                logger.info(f"Mapped industry for {symbol}: {ticker.industry}")
                        
                        # Long description
                        if "long_descriptions" in tables and tables["long_descriptions"]:
                            # Could store company description
                            pass
                    
                    elif item.get("type") == "Stock" and item.get("tables"):
                        tables = item["tables"]
                        
                        # Share class profile (market cap, shares outstanding)
                        if "share_class_profile" in tables and tables["share_class_profile"]:
                            profile = tables["share_class_profile"]
                            ticker.market_cap = float(profile.get("market_cap", 0)) if profile.get("market_cap") else None
            
            # If Tradier quote data failed or fundamentals data is not available, try fallbacks
            if not quote_data or not ticker.sector or ticker.sector == "Sector_Unknown" or not ticker.current_price:
                # Try API Ninjas for sector information first
                try:
                    company_info = await self.api_ninjas.get_company_info(symbol)
                    if company_info:
                        if not ticker.name and company_info.get('company_name'):
                            ticker.name = company_info['company_name']
                        
                        if not ticker.sector and company_info.get('sector'):
                            ticker.sector = company_info['sector']
                            logger.info(f"Got sector from API Ninjas for {symbol}: {ticker.sector}")
                        
                        if not ticker.industry and company_info.get('sub_industry'):
                            ticker.industry = company_info['sub_industry']
                            logger.info(f"Got industry from API Ninjas for {symbol}: {ticker.industry}")
                        
                        logger.info(f"Successfully got API Ninjas data for {symbol}")
                        
                except Exception as e:
                    logger.warning(f"Failed to get API Ninjas data for {symbol}: {e}")
                
                # Fallback to yfinance for price and other data
                if not ticker.current_price:
                    try:
                        import yfinance as yf
                        yf_ticker = yf.Ticker(symbol)
                        info = yf_ticker.info
                        
                        # Use yfinance data as primary source if Tradier failed
                        if not ticker.current_price and info.get('currentPrice'):
                            ticker.current_price = float(info['currentPrice'])
                            logger.info(f"Got price from yfinance for {symbol}: ${ticker.current_price}")
                        
                        if not ticker.name and info.get('longName'):
                            ticker.name = info['longName']
                        
                        if not ticker.sector and info.get('sector'):
                            ticker.sector = info['sector']
                        if not ticker.industry and info.get('industry'):
                            ticker.industry = info['industry']
                        
                        if not ticker.market_cap and info.get('marketCap'):
                            ticker.market_cap = float(info['marketCap']) / 1e9  # Convert to billions
                        
                        if not ticker.pe_ratio and info.get('trailingPE'):
                            ticker.pe_ratio = float(info['trailingPE'])
                        
                        if not ticker.volume_avg_20d and info.get('averageVolume'):
                            ticker.volume_avg_20d = int(info['averageVolume'])
                        
                        if not ticker.beta and info.get('beta'):
                            ticker.beta = float(info['beta'])
                            
                        logger.info(f"Successfully got yfinance data for {symbol}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to get yfinance data for {symbol}: {e}")
            
            # Extract ratios data
            if ratios_data and isinstance(ratios_data, list) and len(ratios_data) > 0:
                for item in ratios_data:
                    if item.get("type") == "Stock" and item.get("tables"):
                        tables = item["tables"]
                        
                        # Valuation ratios
                        if "valuation_ratios" in tables and tables["valuation_ratios"]:
                            ratios = tables["valuation_ratios"]
                            ticker.pe_ratio = float(ratios.get("p_e_ratio", 0)) if ratios.get("p_e_ratio") else None
                            ticker.dividend_yield = float(ratios.get("dividend_yield", 0)) if ratios.get("dividend_yield") else None
                        
                        # Alpha/Beta data
                        if "alpha_beta" in tables and tables["alpha_beta"]:
                            alpha_beta = tables["alpha_beta"]
                            # Use 60-month beta if available, otherwise 36-month
                            if "period_60m" in alpha_beta:
                                ticker.beta = float(alpha_beta["period_60m"].get("beta", 0)) if alpha_beta["period_60m"].get("beta") else None
                            elif "period_36m" in alpha_beta:
                                ticker.beta = float(alpha_beta["period_36m"].get("beta", 0)) if alpha_beta["period_36m"].get("beta") else None
            
            # Set active status
            ticker.active = True
            
            # Calculate a comprehensive universe score
            score = 0.0
            
            # Price criteria
            if ticker.current_price and ticker.current_price > 10:  # Prefer stocks > $10
                score += 1.0
            elif ticker.current_price and ticker.current_price > 5:  # Accept stocks > $5
                score += 0.5
            
            # Volume criteria
            if ticker.volume_avg_20d and ticker.volume_avg_20d > 1000000:  # Prefer liquid stocks
                score += 1.0
            elif ticker.volume_avg_20d and ticker.volume_avg_20d > 500000:  # Accept moderately liquid
                score += 0.5
            
            # Volatility criteria (good for options)
            if ticker.volatility_30d and ticker.volatility_30d > 15:  # Prefer volatile stocks
                score += 1.0
            elif ticker.volatility_30d and ticker.volatility_30d > 10:  # Accept moderately volatile
                score += 0.5
            
            # Market cap criteria
            if ticker.market_cap and ticker.market_cap > 10000000000:  # Prefer large caps > $10B
                score += 1.0
            elif ticker.market_cap and ticker.market_cap > 1000000000:  # Accept mid caps > $1B
                score += 0.5
            
            # Beta criteria (prefer stocks with reasonable beta)
            if ticker.beta and 0.5 <= ticker.beta <= 2.0:  # Reasonable beta range
                score += 0.5
            
            # P/E ratio criteria (avoid extremely high P/E)
            if ticker.pe_ratio and ticker.pe_ratio < 50:  # Reasonable P/E
                score += 0.5
            
            ticker.universe_score = score
            ticker.last_analysis_date = datetime.utcnow()
            ticker.updated_at = datetime.utcnow()
            
            # Try to get next earnings date (but don't fail the entire sync if this fails)
            try:
                earnings = await self.sync_earnings_calendar(symbol)
                if earnings:
                    ticker.next_earnings_date = earnings.earnings_date
                    logger.info(f"Updated next earnings date for {symbol}: {earnings.earnings_date}")
            except Exception as e:
                logger.warning(f"Failed to get earnings date for {symbol}: {e}")
                # Continue with the ticker sync even if earnings fails
            
            # Only commit if we have at least basic price data
            if ticker.current_price is not None:
                await self.db.commit()
                logger.info(f"Successfully committed ticker data for {symbol}")
                return ticker
            else:
                logger.warning(f"No price data available for {symbol}, skipping commit")
                await self.db.rollback()
                return None
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error syncing ticker data for {symbol}: {e}")
            raise e
    
    async def sync_earnings_calendar(self, symbol: str) -> Optional[EarningsCalendar]:
        """Sync earnings calendar data for a ticker."""
        try:
            # Get earnings calendar data from Tradier API
            earnings_data = await self.client.get_earnings_calendar(symbol)
            
            if not earnings_data:
                logger.warning(f"No earnings data available for {symbol}")
                return None
            
            # Parse earnings data and find next upcoming earnings
            next_earnings_date = None
            
            # The structure depends on Tradier API response format
            # This is a simplified parser - adjust based on actual API response
            if isinstance(earnings_data, list):
                for item in earnings_data:
                    if item.get("type") == "Earnings" and item.get("tables"):
                        tables = item["tables"]
                        if "earnings_calendar" in tables:
                            calendar = tables["earnings_calendar"]
                            if calendar and isinstance(calendar, list):
                                for earnings in calendar:
                                    earnings_date_str = earnings.get("earnings_date")
                                    if earnings_date_str:
                                        try:
                                            earnings_date = datetime.strptime(earnings_date_str, "%Y-%m-%d")
                                            if earnings_date > datetime.utcnow():
                                                if next_earnings_date is None or earnings_date < next_earnings_date:
                                                    next_earnings_date = earnings_date
                                        except ValueError:
                                            continue
            
            if not next_earnings_date:
                logger.debug(f"No upcoming earnings found for {symbol}")
                return None
            
            # Check if earnings record already exists
            result = await self.db.execute(
                select(EarningsCalendar).where(
                    and_(
                        EarningsCalendar.symbol == symbol,
                        EarningsCalendar.earnings_date == next_earnings_date
                    )
                )
            )
            existing_earnings = result.scalar_one_or_none()
            
            if existing_earnings:
                # Update existing record
                existing_earnings.updated_at = datetime.utcnow()
                await self.db.commit()
                logger.debug(f"Updated existing earnings record for {symbol}: {next_earnings_date}")
                return existing_earnings
            else:
                # Create new earnings record
                earnings_record = EarningsCalendar(
                    symbol=symbol,
                    earnings_date=next_earnings_date,
                    source="tradier",
                    updated_at=datetime.utcnow()
                )
                self.db.add(earnings_record)
                await self.db.commit()
                logger.info(f"Created earnings record for {symbol}: {next_earnings_date}")
                return earnings_record
                
        except Exception as e:
            logger.error(f"Error syncing earnings calendar for {symbol}: {e}")
            # Don't rollback here - let the main transaction handle it
            # This prevents rolling back successful ticker updates
            return None
    
    async def sync_options_data(self, symbol: str, expiration: str) -> List[Option]:
        """Sync options chain data for a symbol and expiration."""
        try:
            logger.info(f"Fetching options chain for {symbol} with expiration {expiration}")
            options_data = await self.client.get_options_chain(symbol, expiration)
            logger.info(f"Received {len(options_data)} options from Tradier API")
            
            if not options_data:
                logger.warning(f"No options data received for {symbol} with expiration {expiration}")
                return []
            
            # Filter for put options only to reduce data size
            put_options_data = [opt for opt in options_data if opt.get("option_type", "").lower() == "put"]
            logger.info(f"Filtered to {len(put_options_data)} put options")
            
            options = []
            for opt_data in put_options_data:
                option = self._parse_option_data(symbol, expiration, opt_data)
                if option:
                    # Upsert option data
                    result = await self.db.execute(
                        select(Option).where(
                            and_(
                                Option.symbol == symbol,
                                Option.expiry == option.expiry,
                                Option.strike == option.strike,
                                Option.option_type == option.option_type
                            )
                        )
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Update existing
                        for key, value in option.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing, key, value)
                        options.append(existing)
                    else:
                        # Create new
                        self.db.add(option)
                        options.append(option)
            
            await self.db.commit()
            return options
            
        except Exception as e:
            await self.db.rollback()
            raise e
    
    def _parse_option_data(self, symbol: str, expiration: str, opt_data: Dict[str, Any]) -> Optional[Option]:
        """Parse option data from Tradier API response."""
        try:
            logger.debug(f"Parsing option data: {opt_data}")
            expiry = datetime.strptime(expiration, "%Y-%m-%d")
            
            # Calculate DTE (days to expiration)
            dte = (expiry - datetime.utcnow()).days
            
            option = Option(
                symbol=symbol,
                expiry=expiry,
                strike=float(opt_data.get("strike", 0)),
                option_type=opt_data.get("option_type", "").lower(),
                bid=float(opt_data.get("bid", 0)) if opt_data.get("bid") else None,
                ask=float(opt_data.get("ask", 0)) if opt_data.get("ask") else None,
                last=float(opt_data.get("last", 0)) if opt_data.get("last") else None,
                delta=float(opt_data.get("delta", 0)) if opt_data.get("delta") else None,
                gamma=float(opt_data.get("gamma", 0)) if opt_data.get("gamma") else None,
                theta=float(opt_data.get("theta", 0)) if opt_data.get("theta") else None,
                vega=float(opt_data.get("vega", 0)) if opt_data.get("vega") else None,
                implied_volatility=float(opt_data.get("implied_volatility", 0)) if opt_data.get("implied_volatility") else None,
                open_interest=int(opt_data.get("open_interest", 0)) if opt_data.get("open_interest") else None,
                volume=int(opt_data.get("volume", 0)) if opt_data.get("volume") else None,
                dte=dte,
                iv_rank=0.5  # Default IV rank
            )
            
            logger.debug(f"Created option: {option.symbol} {option.strike} {option.option_type}")
            return option
            
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse option data for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing option data for {symbol}: {e}")
            return None
    
    async def sync_positions(self) -> List[Position]:
        """Sync account positions with database."""
        try:
            positions_data = await self.client.get_account_positions()
            
            positions = []
            for pos_data in positions_data:
                position = self._parse_position_data(pos_data)
                if position:
                    # Upsert position
                    result = await self.db.execute(
                        select(Position).where(Position.symbol == position.symbol)
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        existing.shares = position.shares
                        existing.avg_price = position.avg_price
                        existing.updated_at = datetime.utcnow()
                        positions.append(existing)
                    else:
                        self.db.add(position)
                        positions.append(position)
            
            await self.db.commit()
            return positions
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _parse_position_data(self, pos_data: Dict[str, Any]) -> Optional[Position]:
        """Parse position data from Tradier API response."""
        try:
            return Position(
                symbol=pos_data.get("symbol", ""),
                shares=int(pos_data.get("quantity", 0)),
                avg_price=float(pos_data.get("cost_basis", 0))
            )
        except (ValueError, KeyError):
            return None
    
    async def place_trade_order(self, order_data: Dict[str, Any]) -> Trade:
        """Place a trade order and record it in database."""
        try:
            # Place order with Tradier
            order_response = await self.client.place_order(order_data)
            
            # Record trade in database
            trade = Trade(
                external_order_id=order_response.get("id"),
                symbol=order_data.get("symbol"),
                contract_symbol=order_data.get("option_symbol"),
                side=order_data.get("side", "buy"),
                option_type=order_data.get("class"),
                quantity=int(order_data.get("quantity", 0)),
                price=float(order_data.get("price", 0)),
                trade_time=datetime.utcnow(),
                status="pending",
                meta_json=order_response
            )
            
            self.db.add(trade)
            self.db.commit()
            
            return trade
            
        except Exception as e:
            self.db.rollback()
            raise e
