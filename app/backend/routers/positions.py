"""Positions router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from db.session import get_async_db
from db.models import Position, OptionPosition, Ticker
from pydantic import BaseModel
from clients.tradier import TradierClient
from config import settings

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
    db: Session = Depends(get_async_db)
):
    """Get all equity positions."""
    positions = db.query(Position).order_by(desc(Position.shares)).all()
    
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
    db: Session = Depends(get_async_db),
    status: Optional[str] = Query(default="open")
):
    """Get option positions."""
    query = db.query(OptionPosition)
    
    if status:
        query = query.filter(OptionPosition.status == status)
    
    positions = query.order_by(desc(OptionPosition.open_time)).all()
    
    result = []
    for pos in positions:
        # TODO: Get current price from market data
        current_price = pos.open_price  # Placeholder
        
        # Calculate DTE
        from datetime import datetime
        dte = (pos.expiry - datetime.utcnow()).days if pos.expiry else None
        
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
    db: Session = Depends(get_async_db)
):
    """Get portfolio summary."""
    # Get equity positions
    equity_positions = db.query(Position).all()
    
    # Get option positions
    option_positions = db.query(OptionPosition).filter(
        OptionPosition.status == "open"
    ).all()
    
    # Calculate values (placeholder - would need real market data)
    equity_value = sum(pos.shares * pos.avg_price for pos in equity_positions)
    option_value = sum(pos.quantity * pos.open_price for pos in option_positions)
    
    # TODO: Get cash balance from account
    cash = 10000.0  # Placeholder
    
    total_value = cash + equity_value + option_value
    
    # Calculate P&L (placeholder)
    total_pnl = 0.0  # Would need current prices
    total_pnl_pct = 0.0 if total_value == 0 else (total_pnl / total_value * 100)
    
    # Build position responses
    position_responses = []
    for pos in equity_positions:
        current_price = pos.avg_price  # Placeholder
        position_responses.append(PositionResponse(
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
    
    option_position_responses = []
    for pos in option_positions:
        current_price = pos.open_price  # Placeholder
        dte = (pos.expiry - datetime.utcnow()).days if pos.expiry else None
        
        option_position_responses.append(OptionPositionResponse(
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
        dte = (pos.expiry - datetime.utcnow()).days if pos.expiry else None
        
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
        # Create a simple response with basic account info
        return AccountInfoResponse(
            account_number=settings.tradier_account_id,
            total_value=0.0,
            cash=0.0,
            long_stock_value=0.0,
            short_stock_value=0.0,
            long_option_value=0.0,
            short_option_value=0.0,
            buying_power=0.0,
            day_trade_buying_power=0.0,
            equity=0.0,
            last_updated=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch account information: {str(e)}")
