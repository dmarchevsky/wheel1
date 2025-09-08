"""Option expiration monitoring service."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import Trade, OptionEvent
from clients.tradier_account import TradierAccountClient
from utils.timezone import pacific_now

logger = logging.getLogger(__name__)


class OptionExpirationService:
    """Service to monitor and handle option expirations."""
    
    def __init__(self):
        self.production_client = TradierAccountClient(environment="production")
        self.sandbox_client = TradierAccountClient(environment="sandbox")
    
    async def monitor_upcoming_expirations(
        self, 
        db: AsyncSession, 
        days_ahead: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Monitor options expiring in the next N days."""
        try:
            end_date = pacific_now() + timedelta(days=days_ahead)
            
            # Get open option trades expiring soon
            result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.class_type == 'option',
                        Trade.status.in_(['filled', 'discovered']),
                        Trade.expiry.is_not(None),
                        Trade.expiry <= end_date,
                        Trade.expiry >= pacific_now()
                    )
                )
            )
            
            expiring_trades = result.scalars().all()
            
            # Group by expiration date
            expirations_by_date = {}
            for trade in expiring_trades:
                expiry_date = trade.expiry.date().isoformat()
                
                if expiry_date not in expirations_by_date:
                    expirations_by_date[expiry_date] = []
                
                days_to_expiry = (trade.expiry.date() - pacific_now().date()).days
                
                expirations_by_date[expiry_date].append({
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "option_symbol": trade.option_symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "strike": trade.strike,
                    "option_type": trade.option_type,
                    "environment": trade.environment,
                    "days_to_expiry": days_to_expiry,
                    "created_at": trade.created_at.isoformat(),
                    "expiry_date": trade.expiry.isoformat()
                })
            
            logger.info(f"Found {len(expiring_trades)} options expiring in next {days_ahead} days")
            
            return expirations_by_date
            
        except Exception as e:
            logger.error(f"Error monitoring upcoming expirations: {e}")
            return {}
    
    async def check_expired_options(
        self, 
        db: AsyncSession, 
        environment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Check for options that have expired and handle them."""
        try:
            today = pacific_now().date()
            
            # Get option trades that should have expired
            query = select(Trade).where(
                and_(
                    Trade.class_type == 'option',
                    Trade.status.in_(['filled', 'discovered']),
                    Trade.expiry.is_not(None),
                    Trade.expiry < pacific_now()
                )
            )
            
            if environment:
                query = query.where(Trade.environment == environment)
            
            result = await db.execute(query)
            expired_trades = result.scalars().all()
            
            handled_expirations = []
            
            for trade in expired_trades:
                try:
                    # Check if this expiration was already handled
                    existing_event = await db.execute(
                        select(OptionEvent).where(
                            and_(
                                OptionEvent.trade_id == trade.id,
                                OptionEvent.event_type == 'expiration'
                            )
                        )
                    )
                    
                    if existing_event.scalar_one_or_none():
                        continue  # Already handled
                    
                    # Check if position still exists in Tradier
                    position_exists = await self._check_position_exists(trade)
                    
                    if position_exists:
                        # Position still exists after expiry - likely assigned/exercised
                        await self._handle_assignment_or_exercise(db, trade)
                        handled_expirations.append({
                            "trade_id": trade.id,
                            "option_symbol": trade.option_symbol,
                            "event": "assignment_or_exercise",
                            "status": "handled"
                        })
                    else:
                        # Position gone - expired
                        await self._handle_expiration(db, trade)
                        handled_expirations.append({
                            "trade_id": trade.id,
                            "option_symbol": trade.option_symbol,
                            "event": "expiration",
                            "status": "handled"
                        })
                        
                except Exception as trade_error:
                    logger.error(f"Error handling expired trade {trade.id}: {trade_error}")
                    handled_expirations.append({
                        "trade_id": trade.id,
                        "option_symbol": trade.option_symbol,
                        "event": "error",
                        "status": "failed",
                        "error": str(trade_error)
                    })
            
            await db.commit()
            logger.info(f"Processed {len(handled_expirations)} expired options")
            
            return handled_expirations
            
        except Exception as e:
            logger.error(f"Error checking expired options: {e}")
            await db.rollback()
            return []
    
    async def _check_position_exists(self, trade: Trade) -> bool:
        """Check if position still exists in Tradier after expiry."""
        try:
            client = self.production_client if trade.environment == "production" else self.sandbox_client
            
            async with client:
                positions = await client.get_account_positions()
            
            # Look for matching position
            for pos in positions:
                if isinstance(pos, dict):
                    contract_symbol = pos.get("contract_symbol") or pos.get("symbol", "")
                    if contract_symbol == trade.option_symbol:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking position existence for {trade.option_symbol}: {e}")
            return False
    
    async def _handle_expiration(self, db: AsyncSession, trade: Trade):
        """Handle option that expired."""
        try:
            # Calculate final P&L
            if trade.side == "sell":
                # Sold option expired worthless - we keep the premium
                final_pnl = (trade.avg_fill_price or trade.price) * trade.filled_quantity * 100
                expiration_outcome = "expired_profitable"
            else:
                # Bought option expired worthless - we lose the premium
                final_pnl = -((trade.avg_fill_price or trade.price) * trade.filled_quantity * 100)
                expiration_outcome = "expired_loss"
            
            # Update trade
            trade.status = "expired"
            trade.expiration_outcome = expiration_outcome
            trade.final_pnl = final_pnl
            trade.closed_at = pacific_now()
            trade.updated_at = pacific_now()
            
            # Create expiration event
            event = OptionEvent(
                trade_id=trade.id,
                symbol=trade.symbol,
                contract_symbol=trade.option_symbol,
                event_type="expiration",
                event_date=trade.expiry,
                final_pnl=final_pnl,
                environment=trade.environment,
                tradier_data={
                    "expiration_type": "natural_expiry",
                    "detection_method": "scheduled_check"
                }
            )
            
            db.add(event)
            logger.info(f"Handled expiration for {trade.option_symbol} - Final P&L: ${final_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling expiration for trade {trade.id}: {e}")
    
    async def _handle_assignment_or_exercise(self, db: AsyncSession, trade: Trade):
        """Handle option that was assigned or exercised."""
        try:
            # For now, we'll mark it as assigned and track it
            # In the future, we could detect the underlying stock position
            
            # Update trade
            trade.status = "assigned"
            trade.expiration_outcome = "assigned" if trade.side == "sell" else "exercised"
            trade.closed_at = pacific_now()
            trade.updated_at = pacific_now()
            
            # We'll estimate P&L later when we can compare with the underlying position
            
            # Create assignment event
            event = OptionEvent(
                trade_id=trade.id,
                symbol=trade.symbol,
                contract_symbol=trade.option_symbol,
                event_type="assignment" if trade.side == "sell" else "exercise",
                event_date=trade.expiry,
                environment=trade.environment,
                tradier_data={
                    "assignment_type": "expiry_assignment",
                    "detection_method": "position_still_exists"
                }
            )
            
            db.add(event)
            logger.info(f"Handled {'assignment' if trade.side == 'sell' else 'exercise'} for {trade.option_symbol}")
            
        except Exception as e:
            logger.error(f"Error handling assignment/exercise for trade {trade.id}: {e}")
    
    async def get_expiration_summary(
        self, 
        db: AsyncSession, 
        environment: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get summary of recent option expirations."""
        try:
            cutoff_date = pacific_now() - timedelta(days=days_back)
            
            # Get recent option events
            query = select(OptionEvent).where(
                and_(
                    OptionEvent.event_date >= cutoff_date,
                    OptionEvent.event_type.in_(['expiration', 'assignment', 'exercise'])
                )
            )
            
            if environment:
                query = query.where(OptionEvent.environment == environment)
            
            result = await db.execute(query)
            events = result.scalars().all()
            
            summary = {
                "period_days": days_back,
                "environment": environment or "all",
                "total_events": len(events),
                "by_type": {},
                "total_pnl": 0.0,
                "events": []
            }
            
            for event in events:
                # Count by type
                if event.event_type not in summary["by_type"]:
                    summary["by_type"][event.event_type] = 0
                summary["by_type"][event.event_type] += 1
                
                # Add to total P&L
                if event.final_pnl:
                    summary["total_pnl"] += event.final_pnl
                
                # Add event details
                summary["events"].append({
                    "event_id": event.id,
                    "trade_id": event.trade_id,
                    "symbol": event.symbol,
                    "contract_symbol": event.contract_symbol,
                    "event_type": event.event_type,
                    "event_date": event.event_date.isoformat(),
                    "final_pnl": event.final_pnl,
                    "environment": event.environment
                })
            
            logger.info(f"Generated expiration summary: {summary['total_events']} events, "
                       f"${summary['total_pnl']:.2f} total P&L")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating expiration summary: {e}")
            return {"error": str(e)}
    
    async def run_daily_expiration_check(
        self, 
        db: AsyncSession, 
        environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run daily expiration monitoring and handling."""
        try:
            logger.info(f"Running daily expiration check for {environment or 'all environments'}")
            
            # Check for expired options
            expired_results = await self.check_expired_options(db, environment)
            
            # Monitor upcoming expirations
            upcoming_expirations = await self.monitor_upcoming_expirations(db, days_ahead=7)
            
            results = {
                "timestamp": pacific_now().isoformat(),
                "environment": environment or "all",
                "expired_options_handled": len(expired_results),
                "upcoming_expirations": {
                    "dates": list(upcoming_expirations.keys()),
                    "total_contracts": sum(len(contracts) for contracts in upcoming_expirations.values())
                },
                "expired_details": expired_results,
                "upcoming_details": upcoming_expirations
            }
            
            logger.info(f"Daily expiration check completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in daily expiration check: {e}")
            return {
                "timestamp": pacific_now().isoformat(),
                "environment": environment or "all",
                "error": str(e),
                "status": "failed"
            }