"""Trades router for managing trade operations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.session import get_async_db
from db.models import Trade
from services.trade_executor import TradeExecutor

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_trades(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_async_db)
):
    """Get list of trades with optional filtering."""
    try:
        query = db.query(Trade)
        
        if status:
            query = query.filter(Trade.status == status)
        
        trades = query.order_by(desc(Trade.created_at)).offset(offset).limit(limit).all()
        
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
    db: Session = Depends(get_async_db)
):
    """Get a specific trade by ID."""
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
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


@router.post("/execute/{trade_id}")
async def execute_trade(
    trade_id: int,
    db: Session = Depends(get_async_db)
):
    """Execute a pending trade."""
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
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
    db: Session = Depends(get_async_db)
):
    """Cancel a pending trade."""
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade.status != "pending":
            raise HTTPException(status_code=400, detail="Trade is not in pending status")
        
        trade.status = "cancelled"
        db.commit()
        
        return {"message": "Trade cancelled successfully", "trade_id": trade_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel trade: {str(e)}")
