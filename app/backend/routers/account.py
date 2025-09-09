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
from services.order_sync_service import OrderSyncService
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


class TradeInfo(BaseModel):
    """Trade information for positions."""
    trade_id: int
    order_id: str
    side: str
    quantity: int
    price: float
    status: str
    order_type: Optional[str] = None
    filled_quantity: Optional[int] = None
    avg_fill_price: Optional[float] = None
    environment: Optional[str] = None
    created_at: str
    filled_at: Optional[str] = None


class PositionResponse(BaseModel):
    """Position response (equity or option)."""
    symbol: str
    name: Optional[str] = None  # Company name from InterestingTicker
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
    
    # Recommendation tracking
    recommendation_id: Optional[int] = None


class EnhancedPositionResponse(BaseModel):
    """Enhanced position response with trade history."""
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
    
    # Recommendation tracking
    recommendation_id: Optional[int] = None
    
    # Trade history for this position
    opening_trades: List[TradeInfo] = []
    closing_trades: List[TradeInfo] = []
    total_trades: int = 0
    
    # Enhanced metrics from trades
    total_premium_collected: Optional[float] = None  # For options positions
    days_held: Optional[int] = None
    original_entry_date: Optional[str] = None
    average_entry_price: Optional[float] = None


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


class EnhancedOrderResponse(BaseModel):
    """Enhanced order response with trade data and complete information."""
    # Tradier API data (master source)
    order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float]
    status: str
    duration: str
    created_at: str
    filled_quantity: Optional[int] = None
    avg_fill_price: Optional[float] = None
    
    # Enhanced fields
    instrument_type: str  # "equity" or "option"
    underlying_symbol: Optional[str] = None  # For options
    option_symbol: Optional[str] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None  # "put" or "call"
    
    # Database sync info
    trade_id: Optional[int] = None
    database_synced: bool = False
    environment: str
    
    # Financial calculations
    total_value: Optional[float] = None  # quantity * avg_fill_price
    remaining_quantity: Optional[int] = None
    commission: Optional[float] = None
    
    # Complete Tradier data for audit
    tradier_data: Optional[Dict[str, Any]] = None


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
    
    # Recommendation tracking
    recommendation_id: Optional[int] = None


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
async def get_positions(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Get all account positions (equity and options)."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        async with TradierClient(environment=current_env) as client:
            positions = await client.get_account_positions()
            
            # Get recommendation IDs from trades for position linking
            from db.models import Trade, InterestingTicker
            from sqlalchemy import select, and_
            
            # Query all trades to get recommendation mappings
            trade_query = select(Trade.symbol, Trade.option_symbol, Trade.recommendation_id).where(
                and_(
                    Trade.environment == current_env,
                    Trade.recommendation_id.is_not(None)
                )
            ).distinct()
            
            result = await db.execute(trade_query)
            trades_with_recommendations = result.fetchall()
            
            # Create lookup for recommendation IDs
            recommendation_lookup = {}
            for trade in trades_with_recommendations:
                # For options, use option_symbol; for equity, use symbol
                key = trade.option_symbol if trade.option_symbol else trade.symbol
                if key:
                    recommendation_lookup[key] = trade.recommendation_id
            
            # Get company names from InterestingTicker table
            ticker_query = select(InterestingTicker.symbol, InterestingTicker.name)
            ticker_result = await db.execute(ticker_query)
            ticker_names = ticker_result.fetchall()
            
            # Create lookup for company names
            name_lookup = {}
            for ticker in ticker_names:
                if ticker.symbol and ticker.name:
                    name_lookup[ticker.symbol] = ticker.name
            
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
                        
                        # Look for recommendation_id and company name
                        recommendation_id = recommendation_lookup.get(symbol)
                        company_name = name_lookup.get(symbol)
                        
                        position_responses.append(PositionResponse(
                            symbol=symbol,
                            name=company_name,
                            instrument_type="equity",
                            quantity=quantity,
                            cost_basis=cost_basis,
                            current_price=current_price,
                            market_value=market_value,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            recommendation_id=recommendation_id
                        ))
                        
                    elif instrument_type == "option":
                        # Option position - handle shorts correctly
                        contracts = abs(quantity)
                        is_short = quantity < 0
                        
                        # Market value calculation
                        market_value = current_price * contracts * 100
                        
                        # For short positions, market value should be negative (liability)
                        if is_short:
                            market_value = -market_value
                        
                        # P&L calculation for options
                        # For short positions: P&L = cost_basis - current_market_value
                        # For long positions: P&L = current_market_value - cost_basis
                        if is_short:
                            # Short: P&L = Premium received - Current option value
                            # For short positions: P&L = abs(cost_basis) - abs(market_value)
                            premium_received = abs(cost_basis)  # $39
                            current_option_value = abs(market_value)  # $43
                            pnl = premium_received - current_option_value  # $39 - $43 = -$4
                        else:
                            # Long: we paid premium, now own market_value
                            pnl = market_value - cost_basis
                        
                        # P&L percentage calculation
                        if cost_basis != 0:
                            pnl_percent = (pnl / abs(cost_basis)) * 100
                        else:
                            pnl_percent = 0.0
                        
                        # Parse option details from symbol
                        underlying_symbol = symbol
                        option_type = None
                        strike = None
                        expiration = None
                        
                        if len(symbol) > 10:
                            try:
                                # Find LAST P or C position (to avoid symbols like INTC)
                                put_pos = symbol.rfind('P')
                                call_pos = symbol.rfind('C')
                                
                                strike_pos = None
                                if put_pos > call_pos and put_pos > 0:
                                    option_type = 'put'
                                    strike_pos = put_pos
                                elif call_pos > put_pos and call_pos > 0:
                                    option_type = 'call'
                                    strike_pos = call_pos
                                
                                if strike_pos and strike_pos >= 6:
                                    # Extract underlying symbol (everything before date)
                                    # Date is 6 chars before P/C position
                                    underlying_symbol = symbol[:strike_pos-6]
                                    
                                    strike_str = symbol[strike_pos+1:]
                                    if strike_str.isdigit() and len(strike_str) >= 5:
                                        strike = float(strike_str) / 1000.0
                                    
                                    # Extract expiration date (YYMMDD format)
                                    date_part = symbol[strike_pos-6:strike_pos]
                                    if len(date_part) == 6 and date_part.isdigit():
                                        year = 2000 + int(date_part[:2])
                                        month = int(date_part[2:4])
                                        day = int(date_part[4:6])
                                        expiration = f"{year}-{month:02d}-{day:02d}"
                            except Exception:
                                pass  # Use defaults if parsing fails
                        
                        # Look for recommendation_id using the full option symbol
                        recommendation_id = recommendation_lookup.get(symbol)
                        
                        # Get company name for the underlying symbol
                        company_name = name_lookup.get(underlying_symbol)
                        
                        position_responses.append(PositionResponse(
                            symbol=underlying_symbol,
                            name=company_name,
                            instrument_type="option",
                            quantity=quantity,
                            cost_basis=cost_basis,
                            current_price=current_price,
                            market_value=market_value,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            contract_symbol=symbol,
                            option_type=option_type,
                            strike=strike,
                            expiration=expiration,
                            side="long" if quantity > 0 else "short",
                            recommendation_id=recommendation_id
                        ))
                        
                except Exception as pos_error:
                    logger.warning(f"Error processing position {pos.get('symbol', 'unknown')}: {pos_error}")
                    continue
            
            return position_responses
            
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@router.get("/positions/enhanced", response_model=List[EnhancedPositionResponse])
async def get_enhanced_positions(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Get all account positions with associated trade history."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        # Get positions from Tradier (live data)
        async with TradierClient(environment=current_env) as client:
            positions = await client.get_account_positions()
        
        # Get trade data from database
        from db.models import Trade
        from sqlalchemy import desc, and_, or_, select
        
        trade_query = select(Trade).where(
            and_(
                Trade.environment == current_env,
                Trade.status == "filled"  # Only filled trades affect positions
            )
        ).order_by(desc(Trade.filled_at))
        
        result = await db.execute(trade_query)
        trades = result.scalars().all()
        
        # Group trades by symbol/contract
        trades_by_symbol = {}
        for trade in trades:
            # Use option_symbol for options, symbol for equities
            key = trade.option_symbol if trade.option_symbol else trade.symbol
            if key not in trades_by_symbol:
                trades_by_symbol[key] = []
            trades_by_symbol[key].append(trade)
        
        enhanced_positions = []
        
        for pos in positions:
            try:
                symbol = pos["symbol"]
                instrument_type = pos.get("instrument", "equity")
                
                # Detect instrument type if not provided
                if not instrument_type or instrument_type == "equity":
                    if len(symbol) > 10 and any(c in symbol for c in ['P', 'C']) and any(c.isdigit() for c in symbol):
                        instrument_type = "option"
                    else:
                        instrument_type = "equity"
                
                # Get current quote
                try:
                    current_quote = await client.get_quote(symbol)
                    current_price = current_quote.get("last", 0.0) if current_quote else 0.0
                except Exception as quote_error:
                    logger.warning(f"Failed to get quote for {symbol}: {quote_error}")
                    current_price = 0.0
                
                quantity = float(pos.get("quantity", 0))
                cost_basis = float(pos.get("cost_basis", 0))
                
                # Get related trades for this position
                position_trades = trades_by_symbol.get(symbol, [])
                
                # Separate opening and closing trades
                opening_trades = []
                closing_trades = []
                
                for trade in position_trades:
                    trade_info = TradeInfo(
                        trade_id=trade.id,
                        order_id=trade.order_id,
                        side=trade.side,
                        quantity=trade.quantity,
                        price=trade.price,
                        status=trade.status,
                        order_type=trade.order_type,
                        filled_quantity=trade.filled_quantity,
                        avg_fill_price=trade.avg_fill_price,
                        environment=trade.environment,
                        created_at=trade.created_at.isoformat(),
                        filled_at=trade.filled_at.isoformat() if trade.filled_at else None
                    )
                    
                    # Classify as opening or closing trade
                    if trade.side in ["buy", "buy_to_open", "sell_to_open"]:
                        opening_trades.append(trade_info)
                    else:  # buy_to_close, sell_to_close, sell
                        closing_trades.append(trade_info)
                
                # Calculate enhanced metrics
                total_premium_collected = None
                days_held = None
                original_entry_date = None
                average_entry_price = None
                
                if opening_trades:
                    # Find earliest trade
                    earliest_trade = min(position_trades, key=lambda t: t.created_at if t.created_at else pacific_now())
                    original_entry_date = earliest_trade.created_at.isoformat()
                    
                    # Calculate days held
                    days_held = (pacific_now() - earliest_trade.created_at).days
                    
                    # Calculate average entry price for opening trades
                    total_quantity = sum(t.filled_quantity or t.quantity for t in position_trades if t.side in ["buy", "buy_to_open", "sell_to_open"])
                    if total_quantity > 0:
                        weighted_price = sum((t.avg_fill_price or t.price) * (t.filled_quantity or t.quantity) 
                                           for t in position_trades if t.side in ["buy", "buy_to_open", "sell_to_open"])
                        average_entry_price = weighted_price / total_quantity
                    
                    # For options, calculate total premium collected (for short positions)
                    if instrument_type == "option":
                        premium_trades = [t for t in position_trades if t.side == "sell_to_open"]
                        if premium_trades:
                            total_premium_collected = sum((t.avg_fill_price or t.price) * (t.filled_quantity or t.quantity) 
                                                        for t in premium_trades)
                
                # Calculate P&L
                if instrument_type == "equity":
                    market_value = current_price * quantity
                    avg_price = cost_basis / quantity if quantity != 0 else 0.0
                    pnl = (current_price - avg_price) * quantity
                    pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                    
                    enhanced_positions.append(EnhancedPositionResponse(
                        symbol=symbol,
                        instrument_type="equity",
                        quantity=quantity,
                        cost_basis=cost_basis,
                        current_price=current_price,
                        market_value=market_value,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        opening_trades=opening_trades,
                        closing_trades=closing_trades,
                        total_trades=len(position_trades),
                        days_held=days_held,
                        original_entry_date=original_entry_date,
                        average_entry_price=average_entry_price
                    ))
                    
                elif instrument_type == "option":
                    contracts = abs(quantity)
                    market_value = current_price * contracts * 100
                    avg_price = cost_basis / (contracts * 100) if contracts != 0 else 0.0
                    pnl = (current_price - avg_price) * contracts * 100
                    pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                    
                    # Parse option details from symbol
                    underlying_symbol = symbol
                    option_type = None
                    strike = None
                    expiration = None
                    
                    if len(symbol) > 10:
                        try:
                            # Find LAST P or C position (to avoid symbols like INTC)
                            put_pos = symbol.rfind('P')
                            call_pos = symbol.rfind('C')
                            
                            strike_pos = None
                            if put_pos > call_pos and put_pos > 0:
                                option_type = 'put'
                                strike_pos = put_pos
                            elif call_pos > put_pos and call_pos > 0:
                                option_type = 'call'
                                strike_pos = call_pos
                            
                            if strike_pos and strike_pos >= 6:
                                # Extract underlying symbol (everything before date)
                                # Date is 6 chars before P/C position
                                underlying_symbol = symbol[:strike_pos-6]
                                
                                strike_str = symbol[strike_pos+1:]
                                if strike_str.isdigit() and len(strike_str) >= 5:
                                    strike = float(strike_str) / 1000.0
                                
                                # Extract expiration date (YYMMDD format)
                                date_part = symbol[strike_pos-6:strike_pos]
                                if len(date_part) == 6 and date_part.isdigit():
                                    year = 2000 + int(date_part[:2])
                                    month = int(date_part[2:4])
                                    day = int(date_part[4:6])
                                    expiration = f"{year}-{month:02d}-{day:02d}"
                        except Exception:
                            pass  # Use defaults if parsing fails
                    
                    enhanced_positions.append(EnhancedPositionResponse(
                        symbol=underlying_symbol,
                        instrument_type="option",
                        quantity=quantity,
                        cost_basis=cost_basis,
                        current_price=current_price,
                        market_value=market_value,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        contract_symbol=symbol,
                        option_type=option_type,
                        strike=strike,
                        expiration=expiration,
                        side="long" if quantity > 0 else "short",
                        opening_trades=opening_trades,
                        closing_trades=closing_trades,
                        total_trades=len(position_trades),
                        total_premium_collected=total_premium_collected,
                        days_held=days_held,
                        original_entry_date=original_entry_date,
                        average_entry_price=average_entry_price
                    ))
                    
            except Exception as pos_error:
                logger.warning(f"Error processing enhanced position {pos.get('symbol', 'unknown')}: {pos_error}")
                continue
        
        return enhanced_positions
        
    except Exception as e:
        logger.error(f"Error getting enhanced positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced positions: {str(e)}")


@router.get("/positions/summary")
async def get_positions_summary(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Get positions summary with key trade metrics."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        # Get positions from Tradier
        async with TradierClient(environment=current_env) as client:
            positions = await client.get_account_positions()
        
        # Get trade statistics
        from db.models import Trade
        from sqlalchemy import func, desc, case
        
        # Get trade counts and metrics per symbol
        trade_stats_query = select(
            Trade.symbol,
            Trade.option_symbol,
            func.count(Trade.id).label('total_trades'),
            func.sum(Trade.filled_quantity).label('total_quantity'),
            func.avg(Trade.avg_fill_price).label('avg_price'),
            func.min(Trade.created_at).label('first_trade'),
            func.max(Trade.filled_at).label('last_trade'),
            func.sum(
                case(
                    (Trade.side == 'sell_to_open', Trade.avg_fill_price * Trade.filled_quantity),
                    else_=0
                )
            ).label('premium_collected')
        ).where(
            and_(
                Trade.environment == current_env,
                Trade.status == "filled"
            )
        ).group_by(Trade.symbol, Trade.option_symbol)
        
        result = await db.execute(trade_stats_query)
        trade_stats = result.all()
        
        # Create lookup dict for trade stats
        stats_lookup = {}
        for stat in trade_stats:
            key = stat.option_symbol if stat.option_symbol else stat.symbol
            stats_lookup[key] = {
                'total_trades': stat.total_trades,
                'total_quantity': stat.total_quantity,
                'avg_price': stat.avg_price,
                'first_trade': stat.first_trade.isoformat() if stat.first_trade else None,
                'last_trade': stat.last_trade.isoformat() if stat.last_trade else None,
                'premium_collected': float(stat.premium_collected) if stat.premium_collected else 0.0,
                'days_held': (pacific_now() - stat.first_trade).days if stat.first_trade else None
            }
        
        summary_positions = []
        
        for pos in positions:
            try:
                symbol = pos["symbol"]
                quantity = float(pos.get("quantity", 0))
                cost_basis = float(pos.get("cost_basis", 0))
                
                # Get current quote
                try:
                    current_quote = await client.get_quote(symbol)
                    current_price = current_quote.get("last", 0.0) if current_quote else 0.0
                except Exception:
                    current_price = 0.0
                
                # Get trade stats for this position
                trade_info = stats_lookup.get(symbol, {})
                
                # Determine instrument type
                instrument_type = "option" if (len(symbol) > 10 and any(c in symbol for c in ['P', 'C'])) else "equity"
                
                # Calculate basic metrics
                if instrument_type == "equity":
                    market_value = current_price * quantity
                    avg_price = cost_basis / quantity if quantity != 0 else 0.0
                    pnl = (current_price - avg_price) * quantity
                    pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                else:
                    contracts = abs(quantity)
                    market_value = current_price * contracts * 100
                    avg_price = cost_basis / (contracts * 100) if contracts != 0 else 0.0
                    pnl = (current_price - avg_price) * contracts * 100
                    pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                
                position_summary = {
                    "symbol": symbol,
                    "instrument_type": instrument_type,
                    "quantity": quantity,
                    "cost_basis": cost_basis,
                    "current_price": current_price,
                    "market_value": market_value,
                    "pnl": pnl,
                    "pnl_percent": pnl_percent,
                    "trade_metrics": trade_info
                }
                
                summary_positions.append(position_summary)
                
            except Exception as pos_error:
                logger.warning(f"Error processing position summary {pos.get('symbol', 'unknown')}: {pos_error}")
                continue
        
        # Calculate portfolio totals
        total_market_value = sum(p["market_value"] for p in summary_positions)
        total_pnl = sum(p["pnl"] for p in summary_positions)
        total_trades = sum(p["trade_metrics"].get("total_trades", 0) for p in summary_positions)
        total_premium_collected = sum(p["trade_metrics"].get("premium_collected", 0) for p in summary_positions)
        
        return {
            "positions": summary_positions,
            "totals": {
                "total_positions": len(summary_positions),
                "total_market_value": total_market_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": (total_pnl / (total_market_value - total_pnl) * 100) if (total_market_value - total_pnl) > 0 else 0.0,
                "total_trades": total_trades,
                "total_premium_collected": total_premium_collected
            },
            "environment": current_env
        }
        
    except Exception as e:
        logger.error(f"Error getting positions summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get positions summary: {str(e)}")


@router.get("/orders")
async def get_orders(
    request: Request, 
    db: AsyncSession = Depends(get_async_db),
    days_back: int = Query(30, ge=1, le=90, description="Days back to fetch orders"),
    status_filter: Optional[str] = Query(None, description="Filter by order status")
):
    """Get enhanced orders view with Tradier API as master source, fallback to database for Sandbox."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from services.orders_view_service import OrdersViewService
        
        orders_service = OrdersViewService()
        enhanced_orders = await orders_service.get_enhanced_orders(
            db=db,
            environment=current_env,
            days_back=days_back,
            status_filter=status_filter
        )
        
        # Fallback for Sandbox API limitation: if no orders from Tradier, get from database
        if not enhanced_orders and current_env == "sandbox":
            logger.info("No orders from Tradier API (Sandbox limitation), falling back to database trades")
            
            from db.models import Trade
            from sqlalchemy import desc, select, and_
            from datetime import timedelta
            
            # Get recent trades from database
            cutoff_date = pacific_now() - timedelta(days=days_back)
            query = select(Trade).where(
                and_(
                    Trade.environment == current_env,
                    Trade.created_at >= cutoff_date
                )
            )
            
            if status_filter:
                query = query.where(Trade.status == status_filter)
            
            query = query.order_by(desc(Trade.created_at))
            result = await db.execute(query)
            trades = result.scalars().all()
            
            # Convert trades to order format for UI compatibility
            enhanced_orders = []
            for trade in trades:
                enhanced_order = {
                    "order_id": trade.order_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "order_type": trade.order_type or "unknown",
                    "price": trade.price,
                    "status": trade.status,
                    "duration": trade.duration or "day",
                    "created_at": trade.created_at.isoformat() if trade.created_at else "",
                    "filled_quantity": trade.filled_quantity,
                    "avg_fill_price": trade.avg_fill_price,
                    "instrument_type": trade.class_type or "equity",
                    "underlying_symbol": trade.symbol,
                    "option_symbol": trade.option_symbol,
                    "strike": trade.strike,
                    "expiration": trade.expiry.isoformat() if trade.expiry else None,
                    "option_type": trade.option_type,
                    "trade_id": trade.id,
                    "database_synced": True,
                    "environment": trade.environment,
                    "total_value": (trade.avg_fill_price or trade.price) * trade.quantity if trade.avg_fill_price or trade.price else None,
                    "remaining_quantity": trade.remaining_quantity,
                    "commission": 0,
                    "tradier_data": trade.tradier_data
                }
                enhanced_orders.append(enhanced_order)
            
            logger.info(f"Fallback: returning {len(enhanced_orders)} orders from database")
        
        return enhanced_orders
            
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")


@router.get("/trading/comprehensive")
async def get_comprehensive_trading_view(
    request: Request, 
    db: AsyncSession = Depends(get_async_db),
    include_positions: bool = Query(True, description="Include current positions"),
    include_reconciliation: bool = Query(True, description="Run position reconciliation")
):
    """Get comprehensive view of all trading activity including orders, trades, positions, and reconciliation."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from services.orders_view_service import OrdersViewService
        
        orders_service = OrdersViewService()
        comprehensive_view = await orders_service.get_comprehensive_trading_view(
            db=db,
            environment=current_env,
            include_positions=include_positions,
            include_reconciliation=include_reconciliation
        )
        
        return comprehensive_view
        
    except Exception as e:
        logger.error(f"Error getting comprehensive trading view: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get comprehensive trading view: {str(e)}")


@router.post("/positions/reconcile")
async def reconcile_positions(
    request: Request, 
    db: AsyncSession = Depends(get_async_db)
):
    """Run position reconciliation to detect position changes and create missing trade records."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from services.position_reconciliation_service import PositionReconciliationService
        
        reconciliation_service = PositionReconciliationService()
        results = await reconciliation_service.run_full_reconciliation(db, current_env)
        
        return results
        
    except Exception as e:
        logger.error(f"Error running position reconciliation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run position reconciliation: {str(e)}")


@router.post("/options/check-expirations")
async def check_option_expirations(
    request: Request, 
    db: AsyncSession = Depends(get_async_db)
):
    """Check for expired options and handle them."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from services.option_expiration_service import OptionExpirationService
        
        expiration_service = OptionExpirationService()
        results = await expiration_service.run_daily_expiration_check(db, current_env)
        
        return results
        
    except Exception as e:
        logger.error(f"Error checking option expirations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check option expirations: {str(e)}")


@router.get("/options/expiration-summary")
async def get_expiration_summary(
    request: Request, 
    db: AsyncSession = Depends(get_async_db),
    days_back: int = Query(30, ge=1, le=90, description="Days back to include in summary")
):
    """Get summary of option expirations and events."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from services.option_expiration_service import OptionExpirationService
        
        expiration_service = OptionExpirationService()
        summary = await expiration_service.get_expiration_summary(db, current_env, days_back)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting expiration summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get expiration summary: {str(e)}")


@router.get("/options/upcoming-expirations")
async def get_upcoming_expirations(
    request: Request, 
    db: AsyncSession = Depends(get_async_db),
    days_ahead: int = Query(7, ge=1, le=30, description="Days ahead to look for expirations")
):
    """Get upcoming option expirations."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from services.option_expiration_service import OptionExpirationService
        
        expiration_service = OptionExpirationService()
        upcoming = await expiration_service.monitor_upcoming_expirations(db, days_ahead)
        
        return {
            "environment": current_env,
            "days_ahead": days_ahead,
            "upcoming_expirations": upcoming
        }
        
    except Exception as e:
        logger.error(f"Error getting upcoming expirations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get upcoming expirations: {str(e)}")


@router.post("/orders", response_model=Dict[str, Any])
async def submit_order(order_request: OrderSubmissionRequest, request: Request, db: AsyncSession = Depends(get_async_db)):
    """Submit a new order and store details in database."""
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
        class_type = "equity"
        if order_request.option_symbol:
            order_params["class"] = "option"
            order_params["option_symbol"] = order_request.option_symbol
            class_type = "option"
        else:
            order_params["class"] = "equity"
        
        async with TradierClient(environment=current_env) as client:
            result = await client.place_order(order_params)
            
            if not result or not result.get("id"):
                raise HTTPException(status_code=400, detail="Failed to submit order")
            
            # Extract option details if this is an option order
            strike_price = None
            expiry_date = None
            option_type = None
            
            if order_request.option_symbol:
                try:
                    # Parse option symbol to extract details
                    # Format: SYMBOL + YYMMDD + P/C + STRIKE(8 digits)
                    # Example: MRNA251003P00022000 = MRNA + 25/10/03 + P + $22.00
                    option_sym = order_request.option_symbol
                    
                    if len(option_sym) >= 15:  # Minimum length for valid option symbol
                        # Find the LAST position of P or C (option type indicator)
                        # This avoids confusion with symbols like INTC that contain C
                        put_pos = option_sym.rfind('P')
                        call_pos = option_sym.rfind('C')
                        
                        # Determine option type and position - use the rightmost P/C
                        if put_pos > call_pos and put_pos > 0:
                            option_type = 'put'
                            type_pos = put_pos
                        elif call_pos > put_pos and call_pos > 0:
                            option_type = 'call'
                            type_pos = call_pos
                        else:
                            raise ValueError("Could not find option type (P/C)")
                        
                        # Extract underlying symbol (everything before date)
                        # Date should be 6 chars before the P/C
                        if type_pos >= 6:
                            underlying = option_sym[:type_pos-6]
                            date_str = option_sym[type_pos-6:type_pos]
                            strike_str = option_sym[type_pos+1:]
                            
                            # Parse expiry date (YYMMDD format)
                            if len(date_str) == 6 and date_str.isdigit():
                                year = int('20' + date_str[:2])  # Convert YY to 20YY
                                month = int(date_str[2:4])
                                day = int(date_str[4:6])
                                
                                from datetime import datetime
                                expiry_date = datetime(year, month, day)
                                logger.info(f"Parsed expiry date: {expiry_date} from {date_str}")
                            
                            # Parse strike price (8 digits, divide by 1000)
                            if len(strike_str) == 8 and strike_str.isdigit():
                                strike_price = float(strike_str) / 1000.0
                                logger.info(f"Parsed strike price: ${strike_price} from {strike_str}")
                            
                            logger.info(f"Parsed option: {underlying} {option_type} ${strike_price} exp {expiry_date}")
                        else:
                            logger.warning(f"Option symbol too short before type indicator: {option_sym}")
                            
                except Exception as parse_error:
                    logger.warning(f"Could not parse option symbol {order_request.option_symbol}: {parse_error}")
            
            # Store order details in database
            from db.models import Trade
            trade = Trade(
                recommendation_id=order_request.recommendation_id,
                symbol=order_request.symbol,
                option_symbol=order_request.option_symbol,
                side=order_request.side,
                quantity=order_request.quantity,
                price=order_request.price or 0.0,
                order_id=str(result["id"]),
                status="pending",
                order_type=order_request.order_type,
                duration=order_request.duration,
                class_type=class_type,
                environment=current_env,
                remaining_quantity=order_request.quantity,  # Initially, all quantity is remaining
                strike=strike_price,
                expiry=expiry_date,
                option_type=option_type,
                tradier_data=result,  # Store complete Tradier response
                created_at=pacific_now()
            )
            
            db.add(trade)
            await db.commit()
            
            logger.info(f"Order submitted and stored in database: {result['id']} (trade_id: {trade.id})")
            
            # Trigger immediate order sync to start monitoring
            try:
                from services.order_sync_service import OrderSyncService
                order_sync = OrderSyncService()
                await order_sync.trigger_immediate_sync(db, str(result["id"]), current_env)
            except Exception as sync_error:
                logger.warning(f"Failed to trigger immediate sync for order {result['id']}: {sync_error}")
                # Don't fail the order submission if sync fails
            
            return {
                "status": "success",
                "message": "Order submitted successfully",
                "order_id": str(result["id"]),
                "trade_id": trade.id,
                "environment": current_env
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        await db.rollback()
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


@router.post("/orders/sync")
async def sync_orders(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Sync pending orders with Tradier to ensure database is up to date."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        sync_service = OrderSyncService()
        stats = await sync_service.sync_pending_orders(db, environment=current_env)
        
        return {
            "status": "success",
            "message": f"Order sync completed for {current_env} environment",
            "environment": current_env,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error syncing orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync orders: {str(e)}")


@router.post("/orders/{order_id}/sync")
async def sync_specific_order(order_id: str, request: Request, db: AsyncSession = Depends(get_async_db)):
    """Sync a specific order with Tradier."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        sync_service = OrderSyncService()
        success = await sync_service.sync_order_by_id(db, order_id, current_env)
        
        if success:
            return {
                "status": "success",
                "message": f"Order {order_id} synced successfully",
                "order_id": order_id,
                "environment": current_env
            }
        else:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found or could not be synced")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync order: {str(e)}")


@router.get("/orders/reconcile")
async def reconcile_orders(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Reconcile database orders with Tradier orders to identify discrepancies."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        sync_service = OrderSyncService()
        report = await sync_service.reconcile_with_tradier(db, current_env)
        
        return {
            "status": "success",
            "environment": current_env,
            "reconciliation_report": report
        }
        
    except Exception as e:
        logger.error(f"Error reconciling orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reconcile orders: {str(e)}")


@router.get("/trades")
async def get_trades(
    request: Request, 
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """Get trade history from database."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from db.models import Trade
        from sqlalchemy import desc, select
        
        query = select(Trade).where(Trade.environment == current_env)
        
        if status:
            query = query.where(Trade.status == status)
        
        query = query.order_by(desc(Trade.created_at)).limit(limit)
        
        result = await db.execute(query)
        trades = result.scalars().all()
        
        trade_list = []
        for trade in trades:
            trade_dict = {
                "id": trade.id,
                "order_id": trade.order_id,
                "symbol": trade.symbol,
                "option_symbol": trade.option_symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "status": trade.status,
                "order_type": trade.order_type,
                "duration": trade.duration,
                "class_type": trade.class_type,
                "filled_quantity": trade.filled_quantity,
                "avg_fill_price": trade.avg_fill_price,
                "remaining_quantity": trade.remaining_quantity,
                "environment": trade.environment,
                "strike": trade.strike,
                "expiry": trade.expiry.isoformat() if trade.expiry else None,
                "option_type": trade.option_type,
                "created_at": trade.created_at.isoformat(),
                "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
                "filled_at": trade.filled_at.isoformat() if trade.filled_at else None
            }
            trade_list.append(trade_dict)
        
        return {
            "trades": trade_list,
            "environment": current_env,
            "total_count": len(trade_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trades: {str(e)}")


@router.post("/trades/{trade_id}/link-recommendation/{recommendation_id}")
async def link_trade_to_recommendation(
    trade_id: int, 
    recommendation_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_async_db)
):
    """Link an existing trade to a recommendation."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from db.models import Trade, Recommendation
        from sqlalchemy import select, and_
        
        # Get the trade
        trade_result = await db.execute(
            select(Trade).where(
                and_(Trade.id == trade_id, Trade.environment == current_env)
            )
        )
        trade = trade_result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        # Get the recommendation to verify it exists
        rec_result = await db.execute(
            select(Recommendation).where(Recommendation.id == recommendation_id)
        )
        recommendation = rec_result.scalar_one_or_none()
        
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        # Update the trade
        trade.recommendation_id = recommendation_id
        trade.updated_at = pacific_now()
        
        await db.commit()
        
        logger.info(f"Linked trade {trade_id} to recommendation {recommendation_id}")
        
        return {
            "status": "success",
            "message": f"Trade {trade_id} successfully linked to recommendation {recommendation_id}",
            "trade_id": trade_id,
            "recommendation_id": recommendation_id,
            "environment": current_env
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking trade to recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to link trade: {str(e)}")


@router.post("/trades/fix-expiry-dates")
async def fix_expiry_dates(
    request: Request, 
    db: AsyncSession = Depends(get_async_db)
):
    """Fix expiry dates for existing trades with null expiry."""
    try:
        session_id = get_session_id(request)
        current_env = trading_env.get_session_environment(session_id)
        
        from db.models import Trade
        from sqlalchemy import select, and_
        from datetime import datetime
        
        # Get all trades with null expiry but have option_symbol
        result = await db.execute(
            select(Trade).where(
                and_(
                    Trade.environment == current_env,
                    Trade.expiry.is_(None),
                    Trade.option_symbol.is_not(None)
                )
            )
        )
        trades = result.scalars().all()
        
        updated_count = 0
        
        for trade in trades:
            try:
                if trade.option_symbol and len(trade.option_symbol) >= 15:
                    # Parse option symbol to extract expiry date
                    option_sym = trade.option_symbol
                    
                    # Find LAST P or C position (to avoid symbols like INTC)
                    put_pos = option_sym.rfind('P')
                    call_pos = option_sym.rfind('C')
                    
                    type_pos = None
                    if put_pos > call_pos and put_pos > 0:
                        type_pos = put_pos
                    elif call_pos > put_pos and call_pos > 0:
                        type_pos = call_pos
                    
                    if type_pos and type_pos >= 6:
                        # Extract date string (6 chars before P/C)
                        date_str = option_sym[type_pos-6:type_pos]
                        
                        if len(date_str) == 6 and date_str.isdigit():
                            year = int('20' + date_str[:2])
                            month = int(date_str[2:4])
                            day = int(date_str[4:6])
                            
                            expiry_date = datetime(year, month, day)
                            trade.expiry = expiry_date
                            trade.updated_at = pacific_now()
                            updated_count += 1
                            
                            logger.info(f"Updated trade {trade.id}: {trade.option_symbol} -> expiry {expiry_date}")
                            
            except Exception as trade_error:
                logger.warning(f"Failed to parse expiry for trade {trade.id} ({trade.option_symbol}): {trade_error}")
                continue
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Updated expiry dates for {updated_count} trades",
            "updated_count": updated_count,
            "environment": current_env
        }
        
    except Exception as e:
        logger.error(f"Error fixing expiry dates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fix expiry dates: {str(e)}")


@router.get("/debug/parse-option/{option_symbol}")
async def debug_option_parsing(option_symbol: str):
    """Debug option symbol parsing."""
    try:
        from datetime import datetime
        
        result = {
            "option_symbol": option_symbol,
            "length": len(option_symbol),
            "parsed": {}
        }
        
        if len(option_symbol) >= 15:
            # Find LAST P or C position (to avoid symbols like INTC)
            put_pos = option_symbol.rfind('P')
            call_pos = option_symbol.rfind('C')
            
            result["put_pos"] = put_pos
            result["call_pos"] = call_pos
            
            type_pos = None
            option_type = None
            if put_pos > call_pos and put_pos > 0:
                option_type = 'put'
                type_pos = put_pos
            elif call_pos > put_pos and call_pos > 0:
                option_type = 'call'
                type_pos = call_pos
            
            result["parsed"]["option_type"] = option_type
            result["parsed"]["type_pos"] = type_pos
            
            if type_pos and type_pos >= 6:
                underlying = option_symbol[:type_pos-6]
                date_str = option_symbol[type_pos-6:type_pos]
                strike_str = option_symbol[type_pos+1:]
                
                result["parsed"]["underlying"] = underlying
                result["parsed"]["date_str"] = date_str
                result["parsed"]["strike_str"] = strike_str
                
                # Parse date
                if len(date_str) == 6 and date_str.isdigit():
                    year = int('20' + date_str[:2])
                    month = int(date_str[2:4])
                    day = int(date_str[4:6])
                    
                    expiry_date = datetime(year, month, day)
                    result["parsed"]["expiry_date"] = expiry_date.isoformat()
                    result["parsed"]["year"] = year
                    result["parsed"]["month"] = month  
                    result["parsed"]["day"] = day
                
                # Parse strike
                if len(strike_str) == 8 and strike_str.isdigit():
                    strike_price = float(strike_str) / 1000.0
                    result["parsed"]["strike_price"] = strike_price
        
        return result
        
    except Exception as e:
        return {"error": str(e), "option_symbol": option_symbol}

