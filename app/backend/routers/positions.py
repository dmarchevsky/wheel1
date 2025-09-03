from utils.timezone import pacific_now
"""Positions router."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from datetime import datetime, timedelta

from db.session import get_async_db
from db.models import Position, OptionPosition, InterestingTicker
from pydantic import BaseModel
from clients.tradier import TradierClient
from config import settings
from services.account_service import AccountService
from services.trading_environment_service import trading_env
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()


class PositionResponse(BaseModel):
    """Position response model."""
    id: int
    symbol: str
    shares: int
    avg_price: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    updated_at: str
    
    class Config:
        from_attributes = True


class OptionPositionResponse(BaseModel):
    """Option position response model."""
    id: int
    symbol: str
    contract_symbol: str
    side: str
    option_type: str
    quantity: int
    strike: float
    expiry: str
    open_price: float
    current_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    dte: Optional[int] = None
    status: str
    updated_at: str
    
    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    """Portfolio response model."""
    cash: float
    equity_value: float
    option_value: float
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    positions: List[PositionResponse]
    option_positions: List[OptionPositionResponse]


class AccountInfoResponse(BaseModel):
    """Account information response model."""
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
    last_updated: str


class ActivityEvent(BaseModel):
    """Account activity event model."""
    date: str
    type: str
    symbol: Optional[str] = None
    description: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: float
    balance: Optional[float] = None


@router.get("/", response_model=List[PositionResponse])
async def get_positions(
    db: AsyncSession = Depends(get_async_db)
):
    """Get all equity positions."""
    result = await db.execute(
        select(Position).order_by(desc(Position.shares))
    )
    positions = result.scalars().all()
    
    result = []
    for pos in positions:
        # TODO: Get current price from market data
        current_price = pos.avg_price  # Placeholder
        
        result.append(PositionResponse(
            id=pos.id,
            symbol=pos.symbol,
            shares=pos.shares,
            avg_price=pos.avg_price,
            current_price=current_price,
            market_value=current_price * pos.shares if current_price else None,
            pnl=(current_price - pos.avg_price) * pos.shares if current_price else None,
            pnl_pct=((current_price - pos.avg_price) / pos.avg_price * 100) if current_price else None,
            updated_at=pos.updated_at.isoformat()
        ))
    
    return result


@router.get("/options", response_model=List[OptionPositionResponse])
async def get_option_positions(
    db: AsyncSession = Depends(get_async_db),
    status: Optional[str] = Query(default="open")
):
    """Get option positions."""
    query = select(OptionPosition)
    
    if status:
        query = query.where(OptionPosition.status == status)
    
    query = query.order_by(desc(OptionPosition.open_time))
    result = await db.execute(query)
    positions = result.scalars().all()
    
    result = []
    for pos in positions:
        # TODO: Get current price from market data
        current_price = pos.open_price  # Placeholder
        
        # Calculate DTE
        from datetime import datetime
        dte = (pos.expiry - pacific_now()).days if pos.expiry else None
        
        result.append(OptionPositionResponse(
            id=pos.id,
            symbol=pos.symbol,
            contract_symbol=pos.contract_symbol,
            side=pos.side,
            option_type=pos.option_type,
            quantity=pos.quantity,
            strike=pos.strike,
            expiry=pos.expiry.isoformat(),
            open_price=pos.open_price,
            current_price=current_price,
            pnl=(current_price - pos.open_price) * pos.quantity if current_price else None,
            pnl_pct=((current_price - pos.open_price) / pos.open_price * 100) if current_price else None,
            dte=dte,
            status=pos.status,
            updated_at=pos.updated_at.isoformat()
        ))
    
    return result


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    db: AsyncSession = Depends(get_async_db)
):
    """Get portfolio summary with real positions from Tradier API."""
    try:
        # Get environment-aware Tradier client
        async with trading_env.get_tradier_client() as tradier_client:
            # Fetch real positions from Tradier API
            tradier_positions = await tradier_client.get_account_positions()
            
            # Get account balances 
            account_service = AccountService()
            account_info = await account_service.get_account_info()
            
            # Separate equity and option positions
            equity_positions = []
            option_positions = []
            
            for pos in tradier_positions:
                if pos.get("instrument", "") == "equity":
                    # Fetch current quote for stock
                    current_quote = await tradier_client.get_quote(pos["symbol"])
                    current_price = current_quote.get("last", 0.0) if current_quote else 0.0
                    
                    equity_positions.append({
                        "symbol": pos["symbol"],
                        "quantity": float(pos.get("quantity", 0)),
                        "cost_basis": float(pos.get("cost_basis", 0)),
                        "current_price": current_price,
                        "date_acquired": pos.get("date_acquired")
                    })
                elif pos.get("instrument", "") == "option":
                    # Fetch current option quote
                    option_quote = await tradier_client.get_quote(pos["symbol"])
                    current_price = option_quote.get("last", 0.0) if option_quote else 0.0
                    
                    option_positions.append({
                        "symbol": pos["symbol"],
                        "underlying": pos.get("underlying", ""),
                        "quantity": float(pos.get("quantity", 0)),
                        "cost_basis": float(pos.get("cost_basis", 0)),
                        "current_price": current_price,
                        "date_acquired": pos.get("date_acquired")
                    })
            
            # Calculate totals with real market values
            equity_value = 0.0
            total_equity_pnl = 0.0
            
            # Build equity position responses
            position_responses = []
            for pos in equity_positions:
                shares = int(pos["quantity"])
                avg_price = pos["cost_basis"] / shares if shares != 0 else 0.0
                current_price = pos["current_price"]
                market_value = current_price * shares
                pnl = (current_price - avg_price) * shares
                pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                
                equity_value += market_value
                total_equity_pnl += pnl
                
                position_responses.append(PositionResponse(
                    id=0,  # Using 0 since these are live positions not from DB
                    symbol=pos["symbol"],
                    shares=shares,
                    avg_price=avg_price,
                    current_price=current_price,
                    market_value=market_value,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    updated_at=pacific_now().isoformat()
                ))
            
            # Calculate option values
            option_value = 0.0
            total_option_pnl = 0.0
            
            # Build option position responses
            option_position_responses = []
            for pos in option_positions:
                quantity = int(pos["quantity"])
                avg_price = pos["cost_basis"] / (quantity * 100) if quantity != 0 else 0.0  # Options are per-share basis
                current_price = pos["current_price"]
                market_value = current_price * quantity * 100  # Options contract value
                pnl = (current_price - avg_price) * quantity * 100
                pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
                
                option_value += market_value
                total_option_pnl += pnl
                
                # Parse option symbol for details (this is a simplified parser)
                option_symbol = pos["symbol"]
                underlying = pos.get("underlying", option_symbol.split()[0] if " " in option_symbol else option_symbol[:6])
                
                option_position_responses.append(OptionPositionResponse(
                    id=0,  # Using 0 since these are live positions not from DB
                    symbol=underlying,
                    contract_symbol=option_symbol,
                    side="long" if quantity > 0 else "short",
                    option_type="unknown",  # Would need to parse from option symbol
                    quantity=abs(quantity),
                    strike=0.0,  # Would need to parse from option symbol
                    expiry="2024-01-01",  # Would need to parse from option symbol
                    open_price=avg_price,
                    current_price=current_price,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    dte=None,
                    status="open",
                    updated_at=pacific_now().isoformat()
                ))
            
            # Use real account values
            cash = account_info["cash"]
            total_value = account_info["total_value"]
            total_pnl = total_equity_pnl + total_option_pnl
            total_pnl_pct = (total_pnl / total_value * 100) if total_value > 0 else 0.0
            
            return PortfolioResponse(
                cash=cash,
                equity_value=equity_value,
                option_value=option_value,
                total_value=total_value,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                positions=position_responses,
                option_positions=option_position_responses
            )
            
    except Exception as e:
        logger.error(f"Error fetching portfolio from Tradier: {e}")
        
        # Return empty data for any environment on error
        return PortfolioResponse(
            cash=0.0,
            equity_value=0.0,
            option_value=0.0,
            total_value=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            positions=[],
            option_positions=[]
        )


@router.get("/symbols/{symbol}")
async def get_position_by_symbol(
    symbol: str,
    db: Session = Depends(get_async_db)
):
    """Get position for a specific symbol."""
    # Get equity position
    equity_position = db.query(Position).filter(
        Position.symbol == symbol.upper()
    ).first()
    
    # Get option positions
    option_positions = db.query(OptionPosition).filter(
        OptionPosition.symbol == symbol.upper(),
        OptionPosition.status == "open"
    ).all()
    
    result = {
        "symbol": symbol.upper(),
        "equity_position": None,
        "option_positions": []
    }
    
    if equity_position:
        current_price = equity_position.avg_price  # Placeholder
        result["equity_position"] = {
            "shares": equity_position.shares,
            "avg_price": equity_position.avg_price,
            "current_price": current_price,
            "market_value": current_price * equity_position.shares if current_price else None,
            "pnl": (current_price - equity_position.avg_price) * equity_position.shares if current_price else None,
            "pnl_pct": ((current_price - equity_position.avg_price) / equity_position.avg_price * 100) if current_price else None
        }
    
    for pos in option_positions:
        current_price = pos.open_price  # Placeholder
        dte = (pos.expiry - pacific_now()).days if pos.expiry else None
        
        result["option_positions"].append({
            "contract_symbol": pos.contract_symbol,
            "side": pos.side,
            "option_type": pos.option_type,
            "quantity": pos.quantity,
            "strike": pos.strike,
            "expiry": pos.expiry.isoformat(),
            "open_price": pos.open_price,
            "current_price": current_price,
            "pnl": (current_price - pos.open_price) * pos.quantity if current_price else None,
            "pnl_pct": ((current_price - pos.open_price) / pos.open_price * 100) if current_price else None,
            "dte": dte
        })
    
    return result


@router.get("/account", response_model=AccountInfoResponse)
async def get_account_info():
    """Get account information from Tradier."""
    try:
        account_service = AccountService()
        account_info = await account_service.get_account_info()
        
        return AccountInfoResponse(**account_info)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch account information: {str(e)}")


@router.get("/activity", response_model=List[ActivityEvent])
async def get_recent_activity(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back for activity")
):
    """Get recent account activity from Tradier API."""
    try:
        async with TradierClient() as tradier_client:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for Tradier API (YYYY-MM-DD)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            logger.info(f"Fetching account activity from {start_date_str} to {end_date_str}")
            
            # Fetch account history from Tradier
            history_events = await tradier_client.get_account_history(start_date_str, end_date_str)
            
            # Process and format the events - filter for trades only
            activity_events = []
            for event in history_events:
                try:
                    # Parse event data from Tradier response
                    event_date = event.get("date", "")
                    event_type = event.get("type", "unknown").lower()
                    description = event.get("description", "").lower()
                    amount = float(event.get("amount", 0))
                    
                    # Filter for stock and option trades only
                    is_trade = (
                        event_type in ["trade", "buy", "sell", "buy_to_open", "sell_to_close", "buy_to_close", "sell_to_open"] or
                        "bought" in description or 
                        "sold" in description or
                        "buy to open" in description or
                        "sell to close" in description or
                        "buy to close" in description or
                        "sell to open" in description or
                        any(keyword in description for keyword in ["stock", "option", "call", "put", "contract"])
                    )
                    
                    # Skip non-trade activities
                    if not is_trade:
                        continue
                    
                    # Extract symbol if present in description
                    symbol = None
                    original_description = event.get("description", "")
                    
                    if "symbol" in event:
                        symbol = event["symbol"]
                    else:
                        # Try to extract symbol from description (improved heuristic for trades)
                        words = original_description.split()
                        for i, word in enumerate(words):
                            # Look for stock symbols (1-6 uppercase letters)
                            if word.isupper() and 1 <= len(word) <= 6 and word.isalpha():
                                symbol = word
                                break
                            # Look for option symbols (longer alphanumeric strings)
                            elif len(word) > 6 and any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
                                symbol = word
                                break
                    
                    # Extract quantity and price if available
                    quantity = event.get("quantity")
                    if quantity is not None:
                        quantity = float(quantity)
                    
                    price = event.get("price")
                    if price is not None:
                        price = float(price)
                    
                    balance = event.get("balance")
                    if balance is not None:
                        balance = float(balance)
                    
                    # Determine trade action for better display
                    trade_type = "trade"
                    if "bought" in description or "buy" in event_type:
                        trade_type = "buy"
                    elif "sold" in description or "sell" in event_type:
                        trade_type = "sell"
                    
                    activity_event = ActivityEvent(
                        date=event_date,
                        type=trade_type,
                        symbol=symbol,
                        description=original_description,  # Keep original case for display
                        quantity=quantity,
                        price=price,
                        amount=amount,
                        balance=balance
                    )
                    
                    activity_events.append(activity_event)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse activity event: {event}. Error: {e}")
                    continue
            
            # Sort by date descending (most recent first)
            activity_events.sort(key=lambda x: x.date, reverse=True)
            
            # Limit to 50 most recent events for performance
            return activity_events[:50]
            
    except Exception as e:
        logger.error(f"Error fetching account activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch account activity: {str(e)}")
