"""Export router for exporting data to various formats."""

import io
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
import pandas as pd

from db.session import get_async_db
from db.models import Trade, Recommendation, Position

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transactions.xlsx")
async def export_transactions(
    db: AsyncSession = Depends(get_async_db)
):
    """Export all transactions to Excel format."""
    try:
        # Fetch all trades with related data
        result = await db.execute(select(Trade).order_by(desc(Trade.created_at)))
        trades = result.scalars().all()
        
        if not trades:
            raise HTTPException(status_code=404, detail="No transactions found")
        
        # Prepare data for export
        data = []
        for trade in trades:
            data.append({
                "Trade ID": trade.id,
                "Symbol": trade.symbol,
                "Option Symbol": trade.option_symbol,
                "Action": trade.action,
                "Quantity": trade.quantity,
                "Price": trade.price,
                "Status": trade.status,
                "Created At": trade.created_at.isoformat() if trade.created_at else None,
                "Executed At": trade.executed_at.isoformat() if trade.executed_at else None,
                "Recommendation ID": trade.recommendation_id
            })
        
        # Create DataFrame and export to Excel
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Transactions', index=False)
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trades_{timestamp}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export transactions: {str(e)}")


@router.post("/recommendations.xlsx")
async def export_recommendations(
    db: AsyncSession = Depends(get_async_db)
):
    """Export all recommendations to Excel format."""
    try:
        # Fetch all recommendations
        result = await db.execute(select(Recommendation).order_by(desc(Recommendation.created_at)))
        recommendations = result.scalars().all()
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations found")
        
        # Prepare data for export
        data = []
        for rec in recommendations:
            data.append({
                "Recommendation ID": rec.id,
                "Symbol": rec.symbol,
                "Status": rec.status,
                "Score": rec.score,
                "Annualized Yield (%)": rec.annualized_yield,
                "Proximity Score": rec.proximity_score,
                "Liquidity Score": rec.liquidity_score,
                "Risk Adjustment": rec.risk_adjustment,
                "Qualitative Score": rec.qualitative_score,
                "DTE": rec.dte,
                "Spread (%)": rec.spread_pct,
                "Mid Price": rec.mid_price,
                "Delta": rec.delta,
                "IV Rank": rec.iv_rank,
                "Open Interest": rec.open_interest,
                "Volume": rec.volume,
                "Created At": rec.created_at.isoformat() if rec.created_at else None
            })
        
        # Create DataFrame and export to Excel
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Recommendations', index=False)
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recommendations_{timestamp}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export recommendations: {str(e)}")


@router.post("/positions.xlsx")
async def export_positions(
    db: AsyncSession = Depends(get_async_db)
):
    """Export all positions to Excel format."""
    try:
        # Fetch all positions
        result = await db.execute(select(Position).order_by(desc(Position.created_at)))
        positions = result.scalars().all()
        
        if not positions:
            raise HTTPException(status_code=404, detail="No positions found")
        
        # Prepare data for export
        data = []
        for pos in positions:
            data.append({
                "Position ID": pos.id,
                "Symbol": pos.symbol,
                "Option Symbol": pos.option_symbol,
                "Strategy": pos.strategy,
                "Quantity": pos.quantity,
                "Entry Price": pos.entry_price,
                "Current Price": pos.current_price,
                "Status": pos.status,
                "P&L": pos.pnl,
                "Created At": pos.created_at.isoformat() if pos.created_at else None,
                "Closed At": pos.closed_at.isoformat() if pos.closed_at else None
            })
        
        # Create DataFrame and export to Excel
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Positions', index=False)
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"positions_{timestamp}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export positions: {str(e)}")
