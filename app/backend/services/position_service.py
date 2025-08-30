from utils.timezone import pacific_now
"""Position service for managing portfolio positions."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from config import settings
from db.models import Position, OptionPosition, InterestingTicker
from clients.tradier import TradierClient
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PositionService:
    """Service for managing portfolio positions."""
    
    def __init__(self):
        self.tradier_client = TradierClient()
    
    async def sync_positions(self, db: AsyncSession) -> bool:
        """Sync positions from Tradier."""
        try:
            logger.info("Starting position sync...")
            
            # Get positions from Tradier
            tradier_positions = await self.tradier_client.get_positions()
            
            if not tradier_positions:
                logger.warning("No positions returned from Tradier")
                return False
            
            # Process equity positions
            equity_positions = tradier_positions.get("equity", [])
            await self._sync_equity_positions(db, equity_positions)
            
            # Process option positions
            option_positions = tradier_positions.get("option", [])
            await self._sync_option_positions(db, option_positions)
            
            logger.info("Position sync completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")
            return False
    
    async def _sync_equity_positions(self, db: AsyncSession, positions: List[Dict[str, Any]]):
        """Sync equity positions."""
        for pos_data in positions:
            try:
                symbol = pos_data.get("symbol")
                if not symbol:
                    continue
                
                # Check if position already exists
                result = await db.execute(
                    select(Position).where(
                        and_(
                            Position.symbol == symbol,
                            Position.status == "open"
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                
                quantity = int(pos_data.get("quantity", 0))
                
                if quantity > 0:
                    # Active position
                    if existing:
                        # Update existing position
                        existing.quantity = quantity
                        existing.current_price = float(pos_data.get("last_price", 0))
                        existing.market_value = float(pos_data.get("market_value", 0))
                        existing.updated_at = pacific_now()
                    else:
                        # Create new position
                        position = Position(
                            symbol=symbol,
                            quantity=quantity,
                            entry_price=float(pos_data.get("cost_basis", 0)),
                            current_price=float(pos_data.get("last_price", 0)),
                            market_value=float(pos_data.get("market_value", 0)),
                            status="open",
                            created_at=pacific_now()
                        )
                        db.add(position)
                else:
                    # Position closed
                    if existing:
                        existing.status = "closed"
                        existing.closed_at = pacific_now()
                        existing.updated_at = pacific_now()
                
            except Exception as e:
                logger.error(f"Error processing equity position {pos_data}: {e}")
                continue
        
        await db.commit()
    
    async def _sync_option_positions(self, db: AsyncSession, positions: List[Dict[str, Any]]):
        """Sync option positions."""
        for pos_data in positions:
            try:
                symbol = pos_data.get("symbol")
                option_symbol = pos_data.get("option_symbol")
                
                if not symbol or not option_symbol:
                    continue
                
                # Check if position already exists
                result = await db.execute(
                    select(OptionPosition).where(
                        and_(
                            OptionPosition.option_symbol == option_symbol,
                            OptionPosition.status == "open"
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                
                quantity = int(pos_data.get("quantity", 0))
                
                if quantity != 0:
                    # Active position
                    if existing:
                        # Update existing position
                        existing.quantity = quantity
                        existing.current_price = float(pos_data.get("last_price", 0))
                        existing.market_value = float(pos_data.get("market_value", 0))
                        existing.updated_at = pacific_now()
                    else:
                        # Create new position
                        position = OptionPosition(
                            symbol=symbol,
                            option_symbol=option_symbol,
                            quantity=quantity,
                            entry_price=float(pos_data.get("cost_basis", 0)),
                            current_price=float(pos_data.get("last_price", 0)),
                            market_value=float(pos_data.get("market_value", 0)),
                            status="open",
                            created_at=pacific_now()
                        )
                        db.add(position)
                else:
                    # Position closed
                    if existing:
                        existing.status = "closed"
                        existing.closed_at = pacific_now()
                        existing.updated_at = pacific_now()
                
            except Exception as e:
                logger.error(f"Error processing option position {pos_data}: {e}")
                continue
        
        await db.commit()
    
    async def get_portfolio_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """Get portfolio summary."""
        try:
            # Get equity positions
            result = await db.execute(
                select(Position).where(Position.status == "open")
            )
            equity_positions = result.scalars().all()
            
            # Get option positions
            result = await db.execute(
                select(OptionPosition).where(OptionPosition.status == "open")
            )
            option_positions = result.scalars().all()
            
            # Calculate totals
            total_equity_value = sum(pos.market_value for pos in equity_positions)
            total_option_value = sum(pos.market_value for pos in option_positions)
            total_value = total_equity_value + total_option_value
            
            # Calculate P&L
            total_equity_pnl = sum(
                (pos.current_price - pos.entry_price) * pos.quantity 
                for pos in equity_positions
            )
            
            total_option_pnl = sum(
                (pos.current_price - pos.entry_price) * pos.quantity 
                for pos in option_positions
            )
            
            total_pnl = total_equity_pnl + total_option_pnl
            
            return {
                "total_value": total_value,
                "equity_value": total_equity_value,
                "option_value": total_option_value,
                "total_pnl": total_pnl,
                "equity_pnl": total_equity_pnl,
                "option_pnl": total_option_pnl,
                "position_count": len(equity_positions) + len(option_positions),
                "equity_count": len(equity_positions),
                "option_count": len(option_positions)
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                "total_value": 0,
                "equity_value": 0,
                "option_value": 0,
                "total_pnl": 0,
                "equity_pnl": 0,
                "option_pnl": 0,
                "position_count": 0,
                "equity_count": 0,
                "option_count": 0
            }
    
    async def get_covered_call_opportunities(self, db: AsyncSession) -> List[Position]:
        """Get equity positions suitable for covered calls."""
        try:
            # Get equity positions with sufficient shares
            result = await db.execute(
                select(Position).where(
                    and_(
                        Position.status == "open",
                        Position.quantity >= 100  # Minimum for covered call
                    )
                )
            )
            positions = result.scalars().all()
            
            opportunities = []
            
            for position in positions:
                # Check if we already have an option position for this symbol
                result = await db.execute(
                    select(OptionPosition).where(
                        and_(
                            OptionPosition.symbol == position.symbol,
                            OptionPosition.status == "open"
                        )
                    )
                )
                existing_option = result.scalar_one_or_none()
                
                if not existing_option:
                    opportunities.append(position)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error getting covered call opportunities: {e}")
            return []
    
    async def get_rolling_opportunities(self, db: AsyncSession) -> List[OptionPosition]:
        """Get option positions that need rolling."""
        try:
            # Get option positions that are close to expiration or have high delta
            positions = db.query(OptionPosition).filter(
                OptionPosition.status == "open"
            ).all()
            
            rolling_opportunities = []
            
            for position in positions:
                # TODO: Implement rolling logic based on:
                # - Days to expiration
                # - Delta threshold
                # - Profit target
                # - Time decay
                pass
            
            return rolling_opportunities
            
        except Exception as e:
            logger.error(f"Error getting rolling opportunities: {e}")
            return []
