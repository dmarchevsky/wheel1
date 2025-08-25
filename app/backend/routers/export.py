"""Export router for exporting data to various formats."""

import io
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import pandas as pd

from db.session import get_async_db
from db.models import Trade, Recommendation, Position

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transactions.xlsx")
async def export_transactions(
    db: Session = Depends(get_async_db)
):
    """Export all transactions to Excel format."""
    try:
        # Fetch all trades with related data
        trades = db.query(Trade).order_by(desc(Trade.created_at)).all()
        
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
    db: Session = Depends(get_async_db)
):
    """Export all recommendations to Excel format."""
    try:
        # Fetch all recommendations
        recommendations = db.query(Recommendation).order_by(desc(Recommendation.created_at)).all()
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations found")
        
        # Prepare data for export
        data = []
        for rec in recommendations:
            data.append({
                "Recommendation ID": rec.id,
                "Symbol": rec.symbol,
                "Option Symbol": rec.option_symbol,
                "Strategy": rec.strategy,
                "Action": rec.action,
                "Quantity": rec.quantity,
                "Price": rec.price,
                "Status": rec.status,
                "Score": rec.score,
                "Created At": rec.created_at.isoformat() if rec.created_at else None,
                "Expires At": rec.expires_at.isoformat() if rec.expires_at else None
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
    db: Session = Depends(get_async_db)
):
    """Export all positions to Excel format."""
    try:
        # Fetch all positions
        positions = db.query(Position).order_by(desc(Position.created_at)).all()
        
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
