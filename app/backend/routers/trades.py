"""Trades router for managing trade operations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from pydantic import BaseModel

from db.session import get_async_db
from db.models import Trade
from services.trade_executor import TradeExecutor
from services.trading_environment_service import trading_env

router = APIRouter()


class TradeSubmissionRequest(BaseModel):
    """Request model for trade submission."""
    option_symbol: str
    underlying_symbol: str
    strike: float
    expiration: str
    option_type: str
    side: str  # "sell_to_open", "buy_to_close", etc.
    quantity: int
    order_type: str  # "limit", "market"
    price: Optional[float] = None  # Required for limit orders
    duration: str = "day"  # "day", "gtc"


@router.get("/", response_model=List[dict])
async def get_trades(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """Get list of trades with optional filtering."""
    try:
        query = select(Trade)
        
        if status:
            query = query.where(Trade.status == status)
        
        query = query.order_by(desc(Trade.created_at)).offset(offset).limit(limit)
        result = await db.execute(query)
        trades = result.scalars().all()
        
        return [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "option_symbol": trade.option_symbol,
                "action": trade.action,
                "quantity": trade.quantity,
                "price": trade.price,
                "status": trade.status,
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
                "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
                "recommendation_id": trade.recommendation_id
            }
            for trade in trades
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trades: {str(e)}")


@router.get("/{trade_id}", response_model=dict)
async def get_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific trade by ID."""
    try:
        result = await db.execute(select(Trade).where(Trade.id == trade_id))
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "option_symbol": trade.option_symbol,
            "action": trade.action,
            "quantity": trade.quantity,
            "price": trade.price,
            "status": trade.status,
            "created_at": trade.created_at.isoformat() if trade.created_at else None,
            "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
            "recommendation_id": trade.recommendation_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trade: {str(e)}")


@router.post("/submit", response_model=dict)
async def submit_trade(
    trade_request: TradeSubmissionRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Submit a new trade order."""
    try:
        # Get current trading environment
        current_environment = trading_env.current_environment
        
        # Create trade executor with current environment
        trade_executor = TradeExecutor(environment=current_environment)
        
        # Prepare order parameters based on request
        order_params = {
            "class": "option",
            "symbol": trade_request.underlying_symbol,
            "side": trade_request.side,
            "quantity": trade_request.quantity,
            "type": trade_request.order_type,
            "duration": trade_request.duration,
            "option_symbol": trade_request.option_symbol
        }
        
        # Add price for limit orders
        if trade_request.order_type == "limit" and trade_request.price:
            order_params["price"] = trade_request.price
        elif trade_request.order_type == "limit" and not trade_request.price:
            raise HTTPException(status_code=400, detail="Price is required for limit orders")
        
        # Submit the trade
        result = await trade_executor.submit_trade(db, order_params)
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to submit trade")
        
        return {
            "message": "Trade submitted successfully",
            "trade_id": result.get("trade_id"),
            "order_id": result.get("order_id"),
            "environment": current_environment,
            "status": result.get("status", "pending")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit trade: {str(e)}")


@router.post("/execute/{trade_id}")
async def execute_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Execute a pending trade."""
    try:
        result = await db.execute(select(Trade).where(Trade.id == trade_id))
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade.status != "pending":
            raise HTTPException(status_code=400, detail="Trade is not in pending status")
        
        # Execute the trade using the trade executor service
        trade_executor = TradeExecutor()
        result = await trade_executor.execute_trade(trade)
        
        return {"message": "Trade executed successfully", "trade_id": trade_id, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {str(e)}")


@router.delete("/{trade_id}")
async def cancel_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Cancel a pending trade."""
    try:
        result = await db.execute(select(Trade).where(Trade.id == trade_id))
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade.status != "pending":
            raise HTTPException(status_code=400, detail="Trade is not in pending status")
        
        trade.status = "cancelled"
        await db.commit()
        
        return {"message": "Trade cancelled successfully", "trade_id": trade_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel trade: {str(e)}")
