"""Unified Tradier API client using split data and account clients."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from utils.timezone import pacific_now
from services.settings_service import get_setting
from datetime import datetime, timezone
from db.models import Option, InterestingTicker, TickerQuote, Position, OptionPosition, Trade
from .tradier_data import TradierDataClient, TradierAPIError
from .tradier_account import TradierAccountClient


logger = logging.getLogger(__name__)


class TradierClient:
    """Unified Tradier API client using split data and account clients."""
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the unified client.
        
        Args:
            environment: "production" or "sandbox" for account operations
        """
        self.environment = environment
        self.data_client = TradierDataClient()  # Always use production for data
        self.account_client = TradierAccountClient(environment)
        
        logger.debug(f"Tradier unified client initialized for {environment} environment")
    
    async def __aenter__(self):
        await self.data_client.__aenter__()
        await self.account_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.data_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.account_client.__aexit__(exc_type, exc_val, exc_tb)
    
    # Data operations (always use production data endpoints)
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a symbol."""
        return await self.data_client.get_quote(symbol)
    
    async def get_options_chain(self, symbol: str, expiration: str) -> List[Dict[str, Any]]:
        """Get options chain for a symbol and expiration."""
        return await self.data_client.get_options_chain(symbol, expiration)
    
    async def get_option_strikes(self, symbol: str, expiration: str) -> List[float]:
        """Get available strikes for a symbol and expiration."""
        return await self.data_client.get_option_strikes(symbol, expiration)
    
    async def get_option_expirations(self, symbol: str) -> List[str]:
        """Get available expirations for a symbol."""
        return await self.data_client.get_option_expirations(symbol)
    
    async def get_fundamentals_company(self, symbol: str) -> Dict[str, Any]:
        """Get company fundamental data from Tradier API beta endpoint."""
        return await self.data_client.get_fundamentals_company(symbol)
    
    async def get_fundamentals_ratios(self, symbol: str) -> Dict[str, Any]:
        """Get financial ratios from Tradier API beta endpoint."""
        return await self.data_client.get_fundamentals_ratios(symbol)
    
    # Account operations (use environment-specific endpoints)
    async def get_account_positions(self) -> List[Dict[str, Any]]:
        """Get account positions."""
        return await self.account_client.get_account_positions()
    
    async def get_account_orders(self, include_tags: bool = False) -> List[Dict[str, Any]]:
        """Get account orders."""
        return await self.account_client.get_account_orders(include_tags)
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order."""
        return await self.account_client.place_order(order_data)
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        return await self.account_client.get_order_status(order_id)
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        return await self.account_client.cancel_order(order_id)
    
    async def get_account_balances(self) -> Dict[str, Any]:
        """Get account balances."""
        return await self.account_client.get_account_balances()
    
    async def get_account_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get account history."""
        return await self.account_client.get_account_history(start_date, end_date)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Tradier API connection with a simple request."""
        return await self.account_client.test_connection()
    
    # Properties for backward compatibility
    @property
    def base_url(self) -> str:
        """Get base URL for account operations."""
        return self.account_client.base_url
    
    @property
    def account_id(self) -> str:
        """Get account ID."""
        return self.account_client.account_id
    



class TradierDataManager:
    """Manages Tradier data synchronization with database."""
    
    def __init__(self, db: AsyncSession, environment: str = "production"):
        self.db = db
        self.environment = environment
        self.client = TradierClient(environment)
    

    
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
            
            # Update IV ranks with historical volatility after storing options
            await self._update_iv_ranks_with_historical_volatility(symbol, options)
            
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
                iv_rank=self._calculate_iv_rank(implied_volatility, symbol) if implied_volatility else 50.0
            )
            
            logger.debug(f"Created option: {option.symbol} {option.strike} {option.option_type} - Delta: {option.delta}")
            return option
            
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse option data for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing option data for {symbol}: {e}")
            return None
    
    def _calculate_iv_rank(self, implied_volatility: float, symbol: str = None) -> float:
        """Calculate simplified IV rank based on current IV value and historical volatility."""
        from core.scoring import ScoringEngine
        
        # Create a temporary scoring engine instance for IV rank calculation
        # Note: We don't have database access here, so pass None for db
        scoring_engine = ScoringEngine(None)
        
        # Try to get historical volatility from database if symbol provided
        historical_volatility = None
        if symbol and self.db:
            try:
                from db.models import TickerQuote
                from sqlalchemy import select
                
                # Get the ticker's historical volatility asynchronously would require async context
                # For now, we'll use the simplified calculation without historical volatility
                # TODO: Consider refactoring to make this async or pass HV as parameter
                pass
            except Exception:
                pass
        
        return scoring_engine.calculate_simplified_iv_rank(implied_volatility, historical_volatility)
    
    async def _update_iv_ranks_with_historical_volatility(self, symbol: str, options: List[Option]) -> None:
        """Update IV ranks for options using the ticker's historical volatility."""
        try:
            from db.models import TickerQuote
            from core.scoring import ScoringEngine
            
            # Get the ticker's historical volatility
            result = await self.db.execute(
                select(TickerQuote).where(TickerQuote.symbol == symbol)
            )
            quote = result.scalar_one_or_none()
            
            if quote and quote.volatility_30d:
                scoring_engine = ScoringEngine(None)
                
                # Update IV rank for each option using historical volatility
                for option in options:
                    if option.implied_volatility:
                        # Calculate better IV rank using historical volatility
                        new_iv_rank = scoring_engine.calculate_simplified_iv_rank(
                            option.implied_volatility, 
                            quote.volatility_30d
                        )
                        option.iv_rank = new_iv_rank
                        logger.debug(f"Updated IV rank for {option.symbol}: {new_iv_rank:.1f} "
                                   f"(IV: {option.implied_volatility*100:.1f}%, HV: {quote.volatility_30d:.1f}%)")
                
                # Commit the IV rank updates
                await self.db.commit()
                logger.info(f"Updated IV ranks for {len(options)} options using HV={quote.volatility_30d:.1f}%")
            else:
                logger.debug(f"No historical volatility available for {symbol}, keeping simplified IV ranks")
                
        except Exception as e:
            logger.warning(f"Failed to update IV ranks with historical volatility for {symbol}: {e}")
    
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
            
            # Basic liquidity filters: require minimum volume and open interest for storage
            min_volume_storage = await get_setting(self.db, "min_volume", 200)
            min_oi_storage = await get_setting(self.db, "min_oi", 500)
            
            # Use lower thresholds for storage than for recommendation scoring
            # This allows us to store more options while still filtering most junk
            storage_volume_threshold = max(50, min_volume_storage // 4)  # 25% of recommendation threshold, min 50
            storage_oi_threshold = max(100, min_oi_storage // 5)  # 20% of recommendation threshold, min 100
            
            if not option.volume or option.volume < storage_volume_threshold:
                logger.debug(f"Option {option.symbol} {option.strike} failed volume filter: {option.volume} (need ≥{storage_volume_threshold})")
                return False
                
            if not option.open_interest or option.open_interest < storage_oi_threshold:
                logger.debug(f"Option {option.symbol} {option.strike} failed OI filter: {option.open_interest} (need ≥{storage_oi_threshold})")
                return False
            
            logger.debug(f"Option {option.symbol} {option.strike} passed storage criteria: DTE={option.dte}, Delta={option.delta}, Volume={option.volume}, OI={option.open_interest}")
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
