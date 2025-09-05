"""Unified account router for trading account management."""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timedelta
import hashlib

from db.session import get_async_db
from clients.tradier import TradierClient
from services.trading_environment_service import trading_env, TradingEnvironment
from utils.timezone import pacific_now

logger = logging.getLogger(__name__)

router = APIRouter()


def get_session_id(request: Request) -> Optional[str]:
    """Generate a session ID based on client information."""
    try:
        # Create a session ID based on user agent and client IP for browser-based persistence
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else ""
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        
        # Use forwarded IP if available, otherwise use client IP
        ip = forwarded_for if forwarded_for else client_ip
        
        # Create a hash from user agent and IP
        session_data = f"{user_agent}:{ip}"
        session_id = hashlib.md5(session_data.encode()).hexdigest()[:16]
        
        # Check if frontend has an environment preference and sync it
        env_preference = request.headers.get("x-trading-environment")
        if env_preference and env_preference in ["production", "sandbox"]:
            trading_env.set_environment(env_preference, session_id)
        
        return session_id
    except Exception as e:
        logger.warning(f"Could not generate session ID: {e}")
        return None


# Request/Response Models
class EnvironmentSwitchRequest(BaseModel):
    """Request to switch trading environment."""
    environment: TradingEnvironment


class EnvironmentSwitchResponse(BaseModel):
    """Response from environment switch with account details."""
    status: str
    message: str
    environment: TradingEnvironment
    account_info: Dict[str, Any]
    previous_environment: TradingEnvironment
    previous_account: Dict[str, Any]


class AccountStatusResponse(BaseModel):
    """Combined account and environment status."""
    environment: TradingEnvironment
    account_number: str
    account_type: str
    total_value: float
    cash: float
    buying_power: float
    day_trade_buying_power: float
    last_updated: str


class AccountBalancesResponse(BaseModel):
    """Account balances response."""
    account_number: str
    total_value: float
    cash: float
    long_stock_value: float
    short_stock_value: float
    long_option_value: float
    short_option_value: float
    buying_power: float
    day_trade_buying_power: float
    equity: float
    margin_info: Dict[str, Any]
    last_updated: str


class PositionResponse(BaseModel):
    """Position response (equity or option)."""
    symbol: str
    instrument_type: str  # "equity" or "option"
    quantity: float
    cost_basis: float
    current_price: float
    market_value: float
    pnl: float
    pnl_percent: float
    
    # Option-specific fields (null for equity)
    contract_symbol: Optional[str] = None
    option_type: Optional[str] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    side: Optional[str] = None  # "long" or "short"


class OrderResponse(BaseModel):
    """Order response."""
    order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    price: Optional[float]
    status: str
    duration: str
    created_at: str
    filled_quantity: Optional[float] = None
    avg_fill_price: Optional[float] = None


class OrderSubmissionRequest(BaseModel):
    """Order submission request."""
    symbol: str
    side: str  # "buy", "sell", "buy_to_open", "sell_to_open", etc.
    quantity: int
    order_type: str  # "market", "limit"
    price: Optional[float] = None
    duration: str = "day"  # "day", "gtc"
    
    # Option-specific fields
    option_symbol: Optional[str] = None


class ActivityResponse(BaseModel):
    """Activity/history response."""
    date: str
    type: str
    symbol: Optional[str]
    description: str
    quantity: Optional[float]
    price: Optional[float]
    amount: float


class PortfolioResponse(BaseModel):
    """Complete portfolio response."""
    account_status: AccountStatusResponse
    balances: AccountBalancesResponse
    positions: List[PositionResponse]
    recent_orders: List[OrderResponse]


# Endpoints
@router.get("/status", response_model=AccountStatusResponse)
async def get_account_status(request: Request):
    """Get current account and environment status."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        logger.info(f"Getting account status for {current_env} environment (session: {session_id})")
        
        async with TradierClient(environment=current_env) as client:
            balances = await client.get_account_balances()
            
            return AccountStatusResponse(
                environment=current_env,
                account_number=balances.get("account_number", "unknown"),
                account_type=balances.get("account_type", "unknown"),
                total_value=balances.get("total_equity", 0.0),
                cash=balances.get("total_cash", 0.0),
                buying_power=balances.get("margin", {}).get("stock_buying_power", 0.0),
                day_trade_buying_power=balances.get("margin", {}).get("option_buying_power", 0.0),
                last_updated=pacific_now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"Error getting account status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account status: {str(e)}")


@router.post("/environment/switch", response_model=EnvironmentSwitchResponse)
async def switch_environment(env_request: EnvironmentSwitchRequest, request: Request):
    """Switch between live and sandbox environments with explicit account details."""
    try:
        session_id = get_session_id(request)
        # Get current environment info before switching
        current_env = trading_env.get_session_environment(session_id)
        logger.info(f"Switching from {current_env} to {env_request.environment} (session: {session_id})")
        
        # Get current account info before switching
        previous_account = {}
        try:
            async with TradierClient(environment=current_env) as current_client:
                current_balances = await current_client.get_account_balances()
                previous_account = {
                    "environment": current_env,
                    "account_number": current_balances.get("account_number", "unknown"),
                    "account_type": current_balances.get("account_type", "unknown"),
                    "total_value": current_balances.get("total_equity", 0.0),
                    "cash": current_balances.get("total_cash", 0.0)
                }
        except Exception as prev_error:
            logger.warning(f"Could not get previous account info: {prev_error}")
            previous_account = {"environment": current_env, "error": "Could not fetch account info"}
        
        # Test connection and get account info for target environment
        async with TradierClient(environment=env_request.environment) as target_client:
            target_balances = await target_client.get_account_balances()
            target_account = {
                "environment": env_request.environment,
                "account_number": target_balances.get("account_number", "unknown"),
                "account_type": target_balances.get("account_type", "unknown"),
                "total_value": target_balances.get("total_equity", 0.0),
                "cash": target_balances.get("total_cash", 0.0),
                "buying_power": target_balances.get("margin", {}).get("stock_buying_power", 0.0)
            }
        
        # Only switch if target environment is accessible
        trading_env.set_environment(env_request.environment, session_id)
        
        success_message = (
            f"Switched from {current_env} to {env_request.environment}\n"
            f"Previous Account: {previous_account.get('account_number', 'unknown')} "
            f"(${previous_account.get('total_value', 0):,.2f})\n"
            f"New Account: {target_account['account_number']} "
            f"(${target_account['total_value']:,.2f})"
        )
        
        return EnvironmentSwitchResponse(
            status="success",
            message=success_message,
            environment=env_request.environment,
            account_info=target_account,
            previous_environment=current_env,
            previous_account=previous_account
        )
        
    except Exception as e:
        logger.error(f"Error switching to {env_request.environment}: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to switch to {env_request.environment}: {str(e)}"
        )


@router.get("/balances", response_model=AccountBalancesResponse)
async def get_account_balances(request: Request):
    """Get detailed account balances."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        async with TradierClient(environment=current_env) as client:
            balances = await client.get_account_balances()
            
            margin_info = balances.get("margin", {})
            
            return AccountBalancesResponse(
                account_number=balances.get("account_number", "unknown"),
                total_value=balances.get("total_equity", 0.0),
                cash=balances.get("total_cash", 0.0),
                long_stock_value=balances.get("long_market_value", 0.0),
                short_stock_value=balances.get("short_market_value", 0.0),
                long_option_value=balances.get("option_long_value", 0.0),
                short_option_value=balances.get("option_short_value", 0.0),
                buying_power=margin_info.get("stock_buying_power", 0.0),
                day_trade_buying_power=margin_info.get("option_buying_power", 0.0),
                equity=balances.get("equity", 0.0),
                margin_info=margin_info,
                last_updated=pacific_now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"Error getting account balances: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account balances: {str(e)}")


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(request: Request):
    """Get all account positions (equity and options)."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        async with TradierClient(environment=current_env) as client:
            positions = await client.get_account_positions()
            
            position_responses = []
            
            for pos in positions:
                try:
                    # Detect instrument type from symbol if not provided
                    symbol = pos["symbol"]
                    instrument_type = pos.get("instrument")
                    
                    if not instrument_type:
                        # Option symbols are typically longer and contain specific patterns
                        # Example: NKE251003P00070000, SMCI251003P00037000
                        # Equity symbols are typically 1-6 characters: AAPL, MSFT, etc.
                        if len(symbol) > 10 and any(c in symbol for c in ['P', 'C']) and any(c.isdigit() for c in symbol):
                            instrument_type = "option"
                        else:
                            instrument_type = "equity"
                    
                    # Get current quote for the position (with error handling)
                    try:
                        current_quote = await client.get_quote(symbol)
                        current_price = current_quote.get("last", 0.0) if current_quote else 0.0
                    except Exception as quote_error:
                        logger.warning(f"Failed to get quote for {symbol}: {quote_error}")
                        current_price = 0.0
                    
                    quantity = float(pos.get("quantity", 0))
                    cost_basis = float(pos.get("cost_basis", 0))
                    
                    if instrument_type == "equity":
                        # Equity position
                        market_value = current_price * quantity
                        avg_price = cost_basis / quantity if quantity != 0 else 0.0
                        pnl = (current_price - avg_price) * quantity
                        pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                        
                        position_responses.append(PositionResponse(
                            symbol=symbol,
                            instrument_type="equity",
                            quantity=quantity,
                            cost_basis=cost_basis,
                            current_price=current_price,
                            market_value=market_value,
                            pnl=pnl,
                            pnl_percent=pnl_percent
                        ))
                        
                    elif instrument_type == "option":
                        # Option position
                        contracts = abs(quantity)
                        market_value = current_price * contracts * 100  # Options are per-share basis
                        avg_price = cost_basis / (contracts * 100) if contracts != 0 else 0.0
                        pnl = (current_price - avg_price) * contracts * 100
                        pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                        
                        # Extract underlying symbol from option symbol
                        # NKE251003P00070000 -> NKE
                        underlying_symbol = symbol[:3] if len(symbol) > 10 else symbol
                        
                        position_responses.append(PositionResponse(
                            symbol=underlying_symbol,
                            instrument_type="option",
                            quantity=quantity,
                            cost_basis=cost_basis,
                            current_price=current_price,
                            market_value=market_value,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            contract_symbol=symbol,
                            side="long" if quantity > 0 else "short"
                        ))
                        
                except Exception as pos_error:
                    logger.warning(f"Error processing position {pos.get('symbol', 'unknown')}: {pos_error}")
                    continue
            
            return position_responses
            
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(request: Request):
    """Get current orders."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        async with TradierClient(environment=current_env) as client:
            orders = await client.get_account_orders()
            logger.info(f"DEBUG: Orders response type: {type(orders)}, content: {orders}")
            
            # Handle case where orders might be empty or not a list
            if not orders or not isinstance(orders, list):
                logger.info(f"DEBUG: Returning empty list - orders is not a valid list")
                return []
            
            order_responses = []
            
            for order in orders:
                # Skip if order is not a dictionary
                if not isinstance(order, dict):
                    logger.warning(f"Skipping non-dict order: {order}")
                    continue
                    
                try:
                    # Handle nested instrument structure
                    instrument = order.get("instrument", {})
                    if isinstance(instrument, dict):
                        symbol = instrument.get("symbol", "")
                    else:
                        symbol = order.get("symbol", "")
                    
                    order_responses.append(OrderResponse(
                        order_id=str(order.get("id", "")),
                        symbol=symbol,
                        side=order.get("side", ""),
                        quantity=float(order.get("quantity", 0)),
                        order_type=order.get("type", ""),
                        price=float(order.get("price", 0)) if order.get("price") else None,
                        status=order.get("status", ""),
                        duration=order.get("duration", ""),
                        created_at=order.get("create_date", ""),
                        filled_quantity=float(order.get("exec_quantity", 0)) if order.get("exec_quantity") else None,
                        avg_fill_price=float(order.get("avg_price", 0)) if order.get("avg_price") else None
                    ))
                except Exception as order_error:
                    logger.warning(f"Error processing order {order.get('id', 'unknown') if isinstance(order, dict) else 'unknown'}: {order_error}")
                    continue
            
            return order_responses
            
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")


@router.post("/orders", response_model=Dict[str, Any])
async def submit_order(order_request: OrderSubmissionRequest, request: Request):
    """Submit a new order."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        logger.info(f"Submitting order to {current_env} environment: {order_request} (session: {session_id})")
        
        # Prepare order parameters
        order_params = {
            "symbol": order_request.symbol,
            "side": order_request.side,
            "quantity": order_request.quantity,
            "type": order_request.order_type,
            "duration": order_request.duration,
        }
        
        # Add price for limit orders
        if order_request.order_type == "limit":
            if not order_request.price:
                raise HTTPException(status_code=400, detail="Price is required for limit orders")
            order_params["price"] = order_request.price
        
        # Add option-specific parameters
        if order_request.option_symbol:
            order_params["class"] = "option"
            order_params["option_symbol"] = order_request.option_symbol
        else:
            order_params["class"] = "equity"
        
        async with TradierClient(environment=current_env) as client:
            result = await client.place_order(order_params)
            
            if not result or not result.get("id"):
                raise HTTPException(status_code=400, detail="Failed to submit order")
            
            return {
                "status": "success",
                "message": "Order submitted successfully",
                "order_id": str(result["id"]),
                "environment": current_env
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit order: {str(e)}")


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, request: Request):
    """Get specific order details."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        async with TradierClient(environment=current_env) as client:
            order = await client.get_order_status(order_id)
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            
            return OrderResponse(
                order_id=str(order.get("id", "")),
                symbol=order.get("instrument", {}).get("symbol", ""),
                side=order.get("side", ""),
                quantity=float(order.get("quantity", 0)),
                order_type=order.get("type", ""),
                price=float(order.get("price", 0)) if order.get("price") else None,
                status=order.get("status", ""),
                duration=order.get("duration", ""),
                created_at=order.get("create_date", ""),
                filled_quantity=float(order.get("exec_quantity", 0)) if order.get("exec_quantity") else None,
                avg_fill_price=float(order.get("avg_price", 0)) if order.get("avg_price") else None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order: {str(e)}")


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str, request: Request):
    """Cancel an order."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        async with TradierClient(environment=current_env) as client:
            result = await client.cancel_order(order_id)
            
            return {
                "status": "success",
                "message": f"Order {order_id} cancelled successfully",
                "order_id": order_id
            }
            
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@router.get("/activity", response_model=List[ActivityResponse])
async def get_activity(
    request: Request,
    days: int = Query(7, ge=1, le=30, description="Number of days to look back")
):
    """Get account activity/history."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        async with TradierClient(environment=current_env) as client:
            history = await client.get_account_history(start_date_str, end_date_str)
            
            activity_responses = []
            
            for event in history:
                if not isinstance(event, dict):
                    continue
                    
                try:
                    activity_responses.append(ActivityResponse(
                        date=event.get("date", ""),
                        type=event.get("type", "unknown"),
                        symbol=event.get("symbol"),
                        description=event.get("description", ""),
                        quantity=float(event.get("quantity", 0)) if event.get("quantity") else None,
                        price=float(event.get("price", 0)) if event.get("price") else None,
                        amount=float(event.get("amount", 0))
                    ))
                except Exception as activity_error:
                    logger.warning(f"Error processing activity event: {activity_error}")
                    continue
            
            # Sort by date descending
            activity_responses.sort(key=lambda x: x.date, reverse=True)
            
            return activity_responses[:50]  # Limit to 50 most recent
            
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get activity: {str(e)}")


@router.get("/portfolio")
async def get_portfolio(request: Request):
    """Get complete portfolio overview in legacy format for UI compatibility."""
    try:
        # Get all data concurrently for better performance
        status = await get_account_status(request)
        balances = await get_account_balances(request)
        positions = await get_positions(request)
        orders = await get_orders(request)
        
        # Calculate portfolio values from positions (legacy format)
        equity_positions = [p for p in positions if p.instrument_type == "equity"]
        option_positions = [p for p in positions if p.instrument_type == "option"]
        
        equity_value = sum(pos.market_value for pos in equity_positions)
        option_value = sum(pos.market_value for pos in option_positions)
        total_pnl = sum(pos.pnl for pos in positions)
        
        # Calculate P&L percentage
        total_cost_basis = sum(abs(pos.cost_basis) for pos in positions)
        total_pnl_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
        
        # Convert positions to legacy format
        legacy_equity_positions = []
        legacy_option_positions = []
        
        for pos in equity_positions:
            legacy_equity_positions.append({
                "id": 0,
                "symbol": pos.symbol,
                "shares": int(pos.quantity),
                "avg_price": pos.cost_basis / pos.quantity if pos.quantity != 0 else 0.0,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "pnl": pos.pnl,
                "pnl_pct": pos.pnl_percent,
                "updated_at": status.last_updated
            })
        
        for pos in option_positions:
            legacy_option_positions.append({
                "id": 0,
                "symbol": pos.symbol,
                "contract_symbol": pos.contract_symbol,
                "side": pos.side,
                "option_type": pos.option_type or "unknown",
                "quantity": int(abs(pos.quantity)),
                "strike": pos.strike or 0.0,
                "expiry": pos.expiration or "2024-01-01",
                "open_price": pos.cost_basis / (abs(pos.quantity) * 100) if pos.quantity != 0 else 0.0,
                "current_price": pos.current_price,
                "pnl": pos.pnl,
                "pnl_pct": pos.pnl_percent,
                "dte": None,
                "status": "open",
                "updated_at": status.last_updated
            })
        
        # Return legacy format for UI compatibility
        return {
            "cash": balances.cash,
            "equity_value": equity_value,
            "option_value": option_value,
            "total_value": balances.total_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "positions": legacy_equity_positions,
            "option_positions": legacy_option_positions
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio: {str(e)}")

@router.get("/portfolio/full", response_model=PortfolioResponse)
async def get_full_portfolio(request: Request):
    """Get complete portfolio overview in new structured format."""
    try:
        # Get all data concurrently for better performance
        status = await get_account_status(request)
        balances = await get_account_balances(request)
        positions = await get_positions(request)
        orders = await get_orders(request)
        
        return PortfolioResponse(
            account_status=status,
            balances=balances,
            positions=positions,
            recent_orders=orders[:10]  # Last 10 orders
        )
        
    except Exception as e:
        logger.error(f"Error getting full portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get full portfolio: {str(e)}")