"""Trade executor service for executing trades through Tradier."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from config import settings
from db.models import Trade, Recommendation, Position, OptionPosition
from clients.tradier import TradierClient

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Service for executing trades through Tradier."""
    
    def __init__(self):
        self.tradier_client = TradierClient()
    
    async def execute_recommendation(self, db: Session, recommendation_id: int) -> Optional[Trade]:
        """Execute a trade based on a recommendation."""
        try:
            # Get recommendation
            recommendation = db.query(Recommendation).filter(
                Recommendation.id == recommendation_id
            ).first()
            
            if not recommendation:
                logger.error(f"Recommendation {recommendation_id} not found")
                return None
            
            if recommendation.status != "proposed":
                logger.error(f"Recommendation {recommendation_id} is not in proposed status")
                return None
            
            # Execute the trade
            trade = await self._execute_put_sale(db, recommendation)
            
            if trade:
                # Update recommendation status
                recommendation.status = "executed"
                recommendation.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Successfully executed recommendation {recommendation_id}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error executing recommendation {recommendation_id}: {e}")
            db.rollback()
            return None
    
    async def _execute_put_sale(self, db: Session, recommendation: Recommendation) -> Optional[Trade]:
        """Execute a cash-secured put sale."""
        try:
            # Get option details
            option = recommendation.option
            if not option:
                logger.error(f"Option not found for recommendation {recommendation.id}")
                return None
            
            # Prepare order parameters
            order_params = {
                "class": "option",
                "symbol": option.symbol,
                "side": "sell_to_open",
                "quantity": 1,  # 1 contract = 100 shares
                "type": "limit",
                "duration": "day",
                "price": option.bid,  # Use bid price
                "option_symbol": option.option_symbol
            }
            
            # Execute order through Tradier
            order_result = await self.tradier_client.place_order(order_params)
            
            if not order_result or not order_result.get("id"):
                logger.error(f"Failed to place order for {option.symbol}")
                return None
            
            # Create trade record
            trade = Trade(
                recommendation_id=recommendation.id,
                symbol=option.symbol,
                option_symbol=option.option_symbol,
                side="sell_to_open",
                quantity=1,
                price=option.bid,
                order_id=order_result["id"],
                status="pending",
                created_at=datetime.utcnow()
            )
            
            db.add(trade)
            db.commit()
            
            logger.info(f"Created trade record for order {order_result['id']}")
            return trade
            
        except Exception as e:
            logger.error(f"Error executing put sale: {e}")
            return None
    
    async def execute_covered_call(self, db: Session, position_id: int, strike: float, expiry: str) -> Optional[Trade]:
        """Execute a covered call."""
        try:
            # Get position details
            position = db.query(Position).filter(Position.id == position_id).first()
            
            if not position:
                logger.error(f"Position {position_id} not found")
                return None
            
            if position.quantity < 100:
                logger.error(f"Insufficient shares for covered call: {position.quantity}")
                return None
            
            # TODO: Get option data for the specified strike and expiry
            # For now, use placeholder data
            option_symbol = f"{position.symbol}{expiry}C{int(strike * 1000)}"
            
            # Prepare order parameters
            order_params = {
                "class": "option",
                "symbol": position.symbol,
                "side": "sell_to_open",
                "quantity": 1,  # 1 contract = 100 shares
                "type": "limit",
                "duration": "day",
                "price": 1.00,  # Placeholder price
                "option_symbol": option_symbol
            }
            
            # Execute order through Tradier
            order_result = await self.tradier_client.place_order(order_params)
            
            if not order_result or not order_result.get("id"):
                logger.error(f"Failed to place covered call order for {position.symbol}")
                return None
            
            # Create trade record
            trade = Trade(
                symbol=position.symbol,
                option_symbol=option_symbol,
                side="sell_to_open",
                quantity=1,
                price=1.00,  # Placeholder price
                order_id=order_result["id"],
                status="pending",
                created_at=datetime.utcnow()
            )
            
            db.add(trade)
            db.commit()
            
            logger.info(f"Created covered call trade record for order {order_result['id']}")
            return trade
            
        except Exception as e:
            logger.error(f"Error executing covered call: {e}")
            return None
    
    async def close_position(self, db: Session, position_id: int) -> Optional[Trade]:
        """Close an option position."""
        try:
            # Get position details
            position = db.query(OptionPosition).filter(OptionPosition.id == position_id).first()
            
            if not position:
                logger.error(f"Option position {position_id} not found")
                return None
            
            # Determine side based on position type
            side = "buy_to_close" if position.quantity < 0 else "sell_to_close"
            
            # Prepare order parameters
            order_params = {
                "class": "option",
                "symbol": position.symbol,
                "side": side,
                "quantity": abs(position.quantity),
                "type": "market",  # Use market order for closing
                "duration": "day",
                "option_symbol": position.option_symbol
            }
            
            # Execute order through Tradier
            order_result = await self.tradier_client.place_order(order_params)
            
            if not order_result or not order_result.get("id"):
                logger.error(f"Failed to close position {position_id}")
                return None
            
            # Create trade record
            trade = Trade(
                symbol=position.symbol,
                option_symbol=position.option_symbol,
                side=side,
                quantity=abs(position.quantity),
                price=0,  # Market order, price will be filled
                order_id=order_result["id"],
                status="pending",
                created_at=datetime.utcnow()
            )
            
            db.add(trade)
            db.commit()
            
            logger.info(f"Created close position trade record for order {order_result['id']}")
            return trade
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return None
    
    async def check_order_status(self, db: Session, trade_id: int) -> bool:
        """Check the status of a trade order."""
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            
            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False
            
            # Get order status from Tradier
            order_status = await self.tradier_client.get_order_status(trade.order_id)
            
            if not order_status:
                logger.error(f"Failed to get order status for {trade.order_id}")
                return False
            
            # Update trade status
            status = order_status.get("status", "unknown")
            trade.status = status
            
            if status in ["filled", "cancelled", "rejected"]:
                trade.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Updated trade {trade_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking order status for trade {trade_id}: {e}")
            return False
    
    def get_trade_history(self, db: Session, limit: int = 50) -> list:
        """Get trade history."""
        try:
            trades = db.query(Trade).order_by(
                Trade.created_at.desc()
            ).limit(limit).all()
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
