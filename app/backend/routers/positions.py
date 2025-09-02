from utils.timezone import pacific_now
"""Positions router."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from datetime import datetime

from db.session import get_async_db
from db.models import Position, OptionPosition, InterestingTicker
from pydantic import BaseModel
from clients.tradier import TradierClient
from config import settings
from services.account_service import AccountService
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
        # Get real positions from Tradier
        async with TradierClient() as tradier_client:
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
        # Fallback to placeholder data with warning message
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
