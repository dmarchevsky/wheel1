"""Tradier API client with retry logic and rate limiting."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import Session

from config import settings
from db.models import Option, Ticker, Position, OptionPosition, Trade


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
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for Tradier API errors
            if "errors" in data:
                error_msg = data["errors"].get("error", "Unknown Tradier API error")
                raise TradierAPIError(f"Tradier API error: {error_msg}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                await asyncio.sleep(2)
                raise
            raise TradierAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise TradierAPIError(f"Request error: {str(e)}")
    
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


class TradierDataManager:
    """Manages Tradier data synchronization with database."""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = TradierClient()
    
    async def sync_options_data(self, symbol: str, expiration: str) -> List[Option]:
        """Sync options chain data for a symbol and expiration."""
        try:
            options_data = await self.client.get_options_chain(symbol, expiration)
            
            options = []
            for opt_data in options_data:
                option = self._parse_option_data(symbol, expiration, opt_data)
                if option:
                    # Upsert option data
                    existing = self.db.query(Option).filter(
                        Option.symbol == symbol,
                        Option.expiry == option.expiry,
                        Option.strike == option.strike,
                        Option.option_type == option.option_type
                    ).first()
                    
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
            
            self.db.commit()
            return options
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _parse_option_data(self, symbol: str, expiration: str, opt_data: Dict[str, Any]) -> Optional[Option]:
        """Parse option data from Tradier API response."""
        try:
            expiry = datetime.strptime(expiration, "%Y-%m-%d")
            
            return Option(
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
                volume=int(opt_data.get("volume", 0)) if opt_data.get("volume") else None
            )
        except (ValueError, KeyError) as e:
            # Skip invalid option data
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
                    existing = self.db.query(Position).filter(
                        Position.symbol == position.symbol
                    ).first()
                    
                    if existing:
                        existing.shares = position.shares
                        existing.avg_price = position.avg_price
                        existing.updated_at = datetime.utcnow()
                        positions.append(existing)
                    else:
                        self.db.add(position)
                        positions.append(position)
            
            self.db.commit()
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
