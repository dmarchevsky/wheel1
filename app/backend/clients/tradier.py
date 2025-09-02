from utils.timezone import pacific_now
"""Tradier API client with retry logic and rate limiting."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as env_settings
from services.settings_service import get_setting
from datetime import datetime, timezone
from db.models import Option, InterestingTicker, TickerQuote, Position, OptionPosition, Trade


logger = logging.getLogger(__name__)


class TradierAPIError(Exception):
    """Custom exception for Tradier API errors."""
    pass


class TradierClient:
    """Tradier API client with retry logic and rate limiting."""
    
    def __init__(self):
        self.base_url = env_settings.tradier_base_url
        self.access_token = env_settings.tradier_access_token
        self.account_id = env_settings.tradier_account_id
        
        # Validate required configuration
        if not self.access_token or self.access_token == "REPLACE_ME":
            logger.error("Tradier access token not configured or set to placeholder value")
            raise ValueError("Tradier access token not properly configured")
        
        if not self.account_id or self.account_id == "REPLACE_ME":
            logger.error("Tradier account ID not configured or set to placeholder value")
            raise ValueError("Tradier account ID not properly configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        logger.debug(f"Tradier client initialized with base URL: {self.base_url}")
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
        
        history = data.get("history", {}).get("event", [])
        if not isinstance(history, list):
            history = [history]
        
        return history
    
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
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Tradier API connection with a simple request."""
        try:
            # Try to get account balances as a connection test
            data = await self.get_account_balances()
            return {
                "status": "success",
                "message": "Tradier API connection working",
                "account_id": self.account_id,
                "base_url": self.base_url
            }
        except Exception as e:
            logger.error(f"❌ Tradier API connection test failed: {e}")
            return {
                "status": "error",
                "message": f"Tradier API connection failed: {str(e)}",
                "account_id": self.account_id,
                "base_url": self.base_url
            }
    



class TradierDataManager:
    """Manages Tradier data synchronization with database."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = TradierClient()
    

    
    async def sync_ticker_data(self, symbol: str) -> Dict[str, Any]:
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
                if ratios_data:
                    logger.info(f"Successfully got ratios data for {symbol}")
                else:
                    logger.warning(f"No ratios data returned for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to get ratios data for {symbol}: {e}")
            

            
            # Initialize data dictionary
            ticker_data = {
                "symbol": symbol,
                "current_price": None,
                "name": None,
                "volume_avg_20d": None,
                "volatility_30d": None,
                "market_cap": None,
                "pe_ratio": None,
                "dividend_yield": None,
                "beta": None,
                "universe_score": 0.0
            }
            
            # Update comprehensive quote data
            if quote_data:
                # Basic price data
                ticker_data["current_price"] = float(quote_data.get("last", 0)) if quote_data.get("last") else None
                ticker_data["name"] = quote_data.get("description", ticker_data["name"])
                
                # Volume data
                volume = int(quote_data.get("volume", 0)) if quote_data.get("volume") else None
                if volume:
                    ticker_data["volume_avg_20d"] = volume  # Use current volume as approximation
                
                # Calculate volatility from 52-week range
                week_52_high = float(quote_data.get("week_52_high", 0)) if quote_data.get("week_52_high") else None
                week_52_low = float(quote_data.get("week_52_low", 0)) if quote_data.get("week_52_low") else None
                if week_52_high and week_52_low and ticker_data["current_price"]:
                    # Calculate 30-day volatility approximation using 52-week range
                    price_range = week_52_high - week_52_low
                    mid_price = (week_52_high + week_52_low) / 2
                    if mid_price > 0:
                        # Approximate volatility as percentage of mid-price
                        ticker_data["volatility_30d"] = (price_range / mid_price) * 100
            

            
            # Extract fundamental data
            if fundamentals_data and isinstance(fundamentals_data, list) and len(fundamentals_data) > 0:
                # Handle the nested structure: list -> item -> results -> Company/Stock items
                for top_item in fundamentals_data:
                    # Check if this item has results
                    if "results" in top_item and isinstance(top_item["results"], list):
                        results = top_item["results"]
                        
                        for result in results:
                            if result.get("type") == "Stock" and result.get("tables"):
                                tables = result["tables"]
                                
                                # Share class profile (market cap, shares outstanding)
                                if "share_class_profile" in tables and tables["share_class_profile"]:
                                    profile = tables["share_class_profile"]
                                    market_cap = profile.get("market_cap")
                                    if market_cap:
                                        try:
                                            ticker_data["market_cap"] = float(market_cap)
                                        except (ValueError, TypeError):
                                            pass
            
            # Check if we have essential data from Tradier API
            if not ticker_data["current_price"]:
                logger.warning(f"No price data available for {symbol} from Tradier API")
            
            # Extract ratios data
            if ratios_data and isinstance(ratios_data, list) and len(ratios_data) > 0:
                # Handle the nested structure: list -> item -> results -> Stock items
                for top_item in ratios_data:
                    # Check if this item has results
                    if "results" in top_item and isinstance(top_item["results"], list):
                        results = top_item["results"]
                        
                        for result in results:
                            if result.get("type") == "Stock" and result.get("tables"):
                                tables = result["tables"]
                                
                                # Valuation ratios
                                if "valuation_ratios" in tables and tables["valuation_ratios"]:
                                    ratios = tables["valuation_ratios"]
                                    
                                    if isinstance(ratios, dict):
                                        # Try different P/E ratio field names
                                        p_e_ratio = ratios.get("p_e_ratio") or ratios.get("forward_p_e_ratio")
                                        
                                        if p_e_ratio is not None and p_e_ratio != "":
                                            try:
                                                ticker_data["pe_ratio"] = float(p_e_ratio)
                                            except (ValueError, TypeError):
                                                pass
                                        
                                        # Try different dividend yield field names
                                        dividend_yield = ratios.get("dividend_yield") or ratios.get("total_yield")
                                        
                                        if dividend_yield is not None and dividend_yield != "":
                                            try:
                                                ticker_data["dividend_yield"] = float(dividend_yield)
                                            except (ValueError, TypeError):
                                                pass
                                
                                # Alpha/Beta data
                                if "alpha_beta" in tables and tables["alpha_beta"]:
                                    alpha_beta = tables["alpha_beta"]
                                    
                                    # Use 60-month beta if available, otherwise 36-month, then 48-month
                                    if "period_60m" in alpha_beta:
                                        beta_value = alpha_beta["period_60m"].get("beta")
                                        if beta_value is not None and beta_value != "":
                                            try:
                                                ticker_data["beta"] = float(beta_value)
                                            except (ValueError, TypeError):
                                                pass
                                    elif "period_36m" in alpha_beta:
                                        beta_value = alpha_beta["period_36m"].get("beta")
                                        if beta_value is not None and beta_value != "":
                                            try:
                                                ticker_data["beta"] = float(beta_value)
                                            except (ValueError, TypeError):
                                                pass
                                    elif "period_48m" in alpha_beta:
                                        beta_value = alpha_beta["period_48m"].get("beta")
                                        if beta_value is not None and beta_value != "":
                                            try:
                                                ticker_data["beta"] = float(beta_value)
                                            except (ValueError, TypeError):
                                                pass
            
            # Calculate a comprehensive universe score
            score = 0.0
            
            # Price criteria
            if ticker_data["current_price"] and ticker_data["current_price"] > 10:  # Prefer stocks > $10
                score += 1.0
            elif ticker_data["current_price"] and ticker_data["current_price"] > 5:  # Accept stocks > $5
                score += 0.5
            
            # Volume criteria
            if ticker_data["volume_avg_20d"] and ticker_data["volume_avg_20d"] > 1000000:  # Prefer liquid stocks
                score += 1.0
            elif ticker_data["volume_avg_20d"] and ticker_data["volume_avg_20d"] > 500000:  # Accept moderately liquid
                score += 0.5
            
            # Volatility criteria (good for options)
            if ticker_data["volatility_30d"] and ticker_data["volatility_30d"] > 15:  # Prefer volatile stocks
                score += 1.0
            elif ticker_data["volatility_30d"] and ticker_data["volatility_30d"] > 10:  # Accept moderately volatile
                score += 0.5
            
            # Market cap criteria
            if ticker_data["market_cap"] and ticker_data["market_cap"] > 10000000000:  # Prefer large caps > $10B
                score += 1.0
            elif ticker_data["market_cap"] and ticker_data["market_cap"] > 1000000000:  # Accept mid caps > $1B
                score += 0.5
            
            # Beta criteria (prefer stocks with reasonable beta)
            if ticker_data["beta"] and 0.5 <= ticker_data["beta"] <= 2.0:  # Reasonable beta range
                score += 0.5
            
            # P/E ratio criteria (avoid extremely high P/E)
            if ticker_data["pe_ratio"] and ticker_data["pe_ratio"] < 50:  # Reasonable P/E
                score += 0.5
            
            ticker_data["universe_score"] = score
            

            
            # Return data if we have at least basic price data
            if ticker_data["current_price"] is not None:
                logger.info(f"Successfully collected ticker data for {symbol}")
                return ticker_data
            else:
                logger.warning(f"No price data available for {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Error syncing ticker data for {symbol}: {e}")
            return None
    

    
    async def get_optimal_expiration(self, symbol: str) -> Optional[str]:
        """Get the optimal expiration date that falls within 21-35 days."""
        try:
            expirations = await self.client.get_option_expirations(symbol)
            if not expirations:
                logger.warning(f"No expirations available for {symbol}")
                return None
            
            # Convert expiration dates to datetime objects and calculate DTE
            expiration_dates = []
            for exp_str in expirations:
                try:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                    # Convert to timezone-aware datetime for comparison
                    current_pacific_time = pacific_now()
                    # Assume expiration date is at market close (4 PM Eastern = 1 PM Pacific)
                    exp_date_pacific = exp_date.replace(hour=13, minute=0, second=0, microsecond=0)
                    exp_date_pacific = exp_date_pacific.replace(tzinfo=current_pacific_time.tzinfo)
                    dte = (exp_date_pacific - current_pacific_time).days
                    expiration_dates.append((exp_str, exp_date, dte))
                except ValueError as e:
                    logger.warning(f"Invalid expiration date format: {exp_str}")
                    continue
            
            # Filter for expirations within DTE range
            dte_min = await get_setting(self.db, "dte_min", 21)
            dte_max = await get_setting(self.db, "dte_max", 35)
            
            optimal_expirations = [
                (exp_str, exp_date, dte) for exp_str, exp_date, dte in expiration_dates
                if dte_min <= dte <= dte_max
            ]
            
            if optimal_expirations:
                # Sort by DTE and take the one closest to the middle of the range
                optimal_expirations.sort(key=lambda x: abs(x[2] - (dte_min + dte_max) / 2))
                best_expiration = optimal_expirations[0][0]
                best_dte = optimal_expirations[0][2]
                logger.info(f"Selected optimal expiration for {symbol}: {best_expiration} (DTE: {best_dte})")
                return best_expiration
            else:
                # If no optimal expiration, use the nearest one
                expiration_dates.sort(key=lambda x: x[2])
                nearest_expiration = expiration_dates[0][0]
                nearest_dte = expiration_dates[0][2]
                logger.warning(f"No optimal expiration found for {symbol}, using nearest: {nearest_expiration} (DTE: {nearest_dte})")
                return nearest_expiration
                
        except Exception as e:
            logger.error(f"Error getting optimal expiration for {symbol}: {e}")
            return None

    async def sync_options_data(self, symbol: str, expiration: str) -> List[Option]:
        """Sync options chain data for a symbol and expiration with filtering."""
        try:
            logger.info(f"Fetching options chain for {symbol} with expiration {expiration}")
            options_data = await self.client.get_options_chain(symbol, expiration)
            logger.info(f"Received {len(options_data)} options from Tradier API")
            
            if not options_data:
                logger.warning(f"No options data received for {symbol} with expiration {expiration}")
                return []
            
            # Filter for put options only (wheel strategy focuses on puts)
            put_options_data = [opt for opt in options_data if opt.get("option_type", "").lower() == "put"]
            call_options_data = [opt for opt in options_data if opt.get("option_type", "").lower() == "call"]
            logger.info(f"Found {len(put_options_data)} put options and {len(call_options_data)} call options")
            
            # Calculate put/call ratio directly from raw data (don't store calls)
            put_call_ratio = self._calculate_put_call_ratio_from_raw_data(put_options_data, call_options_data)
            
            # Parse and filter PUT options only (for recommendations)
            filtered_options = []
            for opt_data in put_options_data:
                option = self._parse_option_data(symbol, expiration, opt_data)
                if option and await self._passes_storage_criteria(option):
                    filtered_options.append(option)
            
            logger.info(f"Filtered to {len(filtered_options)} options that meet storage criteria")
            
            # Store filtered options
            options = []
            for option in filtered_options:
                # Upsert option using the Tradier symbol as primary key
                result = await self.db.execute(
                    select(Option).where(Option.symbol == option.symbol)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing option with explicit field updates (using rounded values)
                    existing.bid = option.bid
                    existing.ask = option.ask
                    existing.last = option.last
                    existing.price = option.price
                    existing.delta = option.delta  # Already rounded to 2 decimal places
                    existing.gamma = option.gamma  # Already rounded to 2 decimal places
                    existing.theta = option.theta  # Already rounded to 2 decimal places
                    existing.vega = option.vega    # Already rounded to 2 decimal places
                    existing.implied_volatility = option.implied_volatility
                    existing.open_interest = option.open_interest
                    existing.volume = option.volume
                    existing.dte = option.dte
                    existing.updated_at = pacific_now()
                    options.append(existing)
                else:
                    # Create new
                    self.db.add(option)
                    options.append(option)
            
            await self.db.commit()
            
            # Update put/call ratio in ticker quotes using calculated ratio
            await self._update_put_call_ratio_for_ticker(symbol, put_call_ratio)
            
            return options
            
        except Exception as e:
            await self.db.rollback()
            raise e
    
    def _calculate_put_call_ratio_from_raw_data(self, put_options_data: List[Dict], call_options_data: List[Dict]) -> Optional[float]:
        """Calculate put/call ratio directly from raw API data without storing calls."""
        try:
            # Calculate put/call ratio based on volume from raw data
            put_volume = sum(opt.get('volume', 0) or 0 for opt in put_options_data)
            call_volume = sum(opt.get('volume', 0) or 0 for opt in call_options_data)
            
            if call_volume == 0:
                if put_volume == 0:
                    return None  # No volume data
                return 999.0  # All puts, no calls (JSON-safe large value)
            
            put_call_ratio = put_volume / call_volume
            logger.debug(f"Calculated P/C ratio from raw data: {put_call_ratio:.3f} (put_vol: {put_volume}, call_vol: {call_volume})")
            return put_call_ratio
            
        except Exception as e:
            logger.error(f"Error calculating put/call ratio from raw data: {e}")
            return None

    async def _update_put_call_ratio_for_ticker(self, symbol: str, put_call_ratio: Optional[float] = None) -> None:
        """Update put/call ratio in ticker quotes."""
        try:
            from db.models import TickerQuote
            
            # Use provided ratio or calculate from stored data
            if put_call_ratio is None:
                put_call_ratio = await self._calculate_put_call_ratio(symbol)
            
            if put_call_ratio is not None:
                # Update or create ticker quote with put/call ratio
                quote_result = await self.db.execute(
                    select(TickerQuote).where(TickerQuote.symbol == symbol)
                )
                quote = quote_result.scalar_one_or_none()
                
                if quote:
                    quote.put_call_ratio = put_call_ratio
                    quote.updated_at = pacific_now()
                else:
                    # Create new quote if doesn't exist
                    quote = TickerQuote(
                        symbol=symbol,
                        put_call_ratio=put_call_ratio,
                        updated_at=pacific_now()
                    )
                    self.db.add(quote)
                
                await self.db.commit()
                logger.info(f"✅ Updated put/call ratio for {symbol}: {put_call_ratio:.3f}")
            else:
                logger.debug(f"No put/call ratio calculated for {symbol}")
                
        except Exception as e:
            logger.error(f"Error updating put/call ratio for {symbol}: {e}")
    
    async def _calculate_put_call_ratio(self, symbol: str) -> Optional[float]:
        """Calculate put/call ratio from options data."""
        try:
            # Get recent options data (last 24 hours)
            result = await self.db.execute(
                select(Option).where(
                    and_(
                        Option.underlying_symbol == symbol,
                        Option.updated_at >= pacific_now() - timedelta(hours=24)
                    )
                )
            )
            options = result.scalars().all()
            
            if not options:
                logger.debug(f"No recent options data for {symbol} to calculate put/call ratio")
                return None
            
            # Calculate put/call ratio based on volume
            put_volume = sum(opt.volume or 0 for opt in options if opt.option_type == "put")
            call_volume = sum(opt.volume or 0 for opt in options if opt.option_type == "call")
            
            if call_volume == 0:
                if put_volume == 0:
                    return None  # No volume data
                return 999.0  # All puts, no calls (JSON-safe large value)
            
            put_call_ratio = put_volume / call_volume
            logger.debug(f"Calculated put/call ratio for {symbol}: {put_call_ratio:.3f} (put_vol: {put_volume}, call_vol: {call_volume})")
            return put_call_ratio
            
        except Exception as e:
            logger.error(f"Error calculating put/call ratio for {symbol}: {e}")
            return None

    def _parse_option_data(self, symbol: str, expiration: str, opt_data: Dict[str, Any]) -> Optional[Option]:
        """Parse option data from Tradier API response."""
        try:
            logger.debug(f"Parsing option data: {opt_data}")
            expiry = datetime.strptime(expiration, "%Y-%m-%d")
                        # Assume UTC timezone for expiry
            expiry = expiry.replace(tzinfo=timezone.utc)
            
            # Calculate DTE (days to expiration)
            dte = (expiry - pacific_now()).days
            
            # Extract greeks data from nested structure
            greeks = opt_data.get("greeks", {})
            if not isinstance(greeks, dict):
                greeks = {}
            
            # Extract implied volatility from greeks (try different field names)
            implied_volatility = None
            if greeks.get("mid_iv"):
                implied_volatility = float(greeks.get("mid_iv", 0))
            elif greeks.get("smv_vol"):
                implied_volatility = float(greeks.get("smv_vol", 0))
            
            # Round greeks to 2 decimal places for database storage
            delta_rounded = round(float(greeks.get("delta", 0)), 2) if greeks.get("delta") else None
            gamma_rounded = round(float(greeks.get("gamma", 0)), 2) if greeks.get("gamma") else None
            theta_rounded = round(float(greeks.get("theta", 0)), 2) if greeks.get("theta") else None
            vega_rounded = round(float(greeks.get("vega", 0)), 2) if greeks.get("vega") else None
            
            # Calculate price from bid, ask, last
            bid = float(opt_data.get("bid", 0)) if opt_data.get("bid") else None
            ask = float(opt_data.get("ask", 0)) if opt_data.get("ask") else None
            last = float(opt_data.get("last", 0)) if opt_data.get("last") else None
            
            # Calculate price: prefer mid price (bid+ask)/2, fallback to last, then ask, then bid
            price = None
            if bid is not None and ask is not None:
                price = (bid + ask) / 2
            elif last is not None:
                price = last
            elif ask is not None:
                price = ask
            elif bid is not None:
                price = bid
            
            # Get the Tradier API symbol (e.g., VXX190517P00016000)
            tradier_symbol = opt_data.get("symbol")
            if not tradier_symbol:
                logger.warning(f"No symbol found in option data for {symbol}")
                return None
            
            option = Option(
                symbol=tradier_symbol,  # Use Tradier API symbol as primary key
                underlying_symbol=symbol,  # The underlying stock symbol
                expiry=expiry,
                strike=float(opt_data.get("strike", 0)),
                option_type=opt_data.get("option_type", "").lower(),
                bid=bid,
                ask=ask,
                last=last,
                price=price,  # Calculated price field
                delta=delta_rounded,
                gamma=gamma_rounded,
                theta=theta_rounded,
                vega=vega_rounded,
                implied_volatility=implied_volatility,
                open_interest=int(opt_data.get("open_interest", 0)) if opt_data.get("open_interest") else None,
                volume=int(opt_data.get("volume", 0)) if opt_data.get("volume") else None,
                dte=dte,
                iv_rank=0.5  # Default IV rank
            )
            
            logger.debug(f"Created option: {option.symbol} {option.strike} {option.option_type} - Delta: {option.delta}")
            return option
            
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse option data for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing option data for {symbol}: {e}")
            return None
    
    async def _passes_storage_criteria(self, option: Option) -> bool:
        """Check if option meets storage criteria (delta and DTE)."""
        try:
            # DTE filter: use unified DTE settings for all options
            dte_min = await get_setting(self.db, "dte_min", 21)
            dte_max = await get_setting(self.db, "dte_max", 35)
            
            if option.dte is None or not (dte_min <= option.dte <= dte_max):
                logger.debug(f"Option {option.symbol} {option.strike} failed DTE filter: {option.dte} days (need {dte_min}-{dte_max})")
                return False
            
            # Delta filter: 0.25-0.35 (using put delta settings)
            put_delta_min = await get_setting(self.db, "put_delta_min", 0.25)
            put_delta_max = await get_setting(self.db, "put_delta_max", 0.35)
            
            if option.delta is None or not (put_delta_min <= abs(option.delta) <= put_delta_max):
                logger.debug(f"Option {option.symbol} {option.strike} failed delta filter: {option.delta} (need {put_delta_min}-{put_delta_max})")
                return False
            
            # Basic liquidity filter: require some open interest
            if option.open_interest is not None and option.open_interest < 10:  # Very low threshold for storage
                logger.debug(f"Option {option.symbol} {option.strike} failed OI filter: {option.open_interest}")
                return False
            
            logger.debug(f"Option {option.symbol} {option.strike} passed storage criteria: DTE={option.dte}, Delta={option.delta}")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking storage criteria for {option.symbol} {option.strike}: {e}")
            return False
    
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
                        existing.updated_at = pacific_now()
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
                trade_time=pacific_now(),
                status="pending",
                meta_json=order_response
            )
            
            self.db.add(trade)
            self.db.commit()
            
            return trade
            
        except Exception as e:
            self.db.rollback()
            raise e
