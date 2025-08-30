from utils.timezone import pacific_now
"""Alert service for monitoring positions and generating alerts."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from config import settings as env_settings
from services.settings_service import get_setting
from db.models import Position, OptionPosition, Notification, Alert
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AlertService:
    """Service for monitoring positions and generating alerts."""
    
    def __init__(self):
        pass
    
    async def check_alerts(self, db: AsyncSession) -> List[Alert]:
        """Check for alerts and generate notifications."""
        try:
            logger.debug("Checking for alerts...")
            
            alerts = []
            
            # Check profit target alerts
            profit_alerts = await self._check_profit_targets(db)
            alerts.extend(profit_alerts)
            
            # Check time decay alerts
            time_decay_alerts = await self._check_time_decay(db)
            alerts.extend(time_decay_alerts)
            
            # Check delta threshold alerts
            delta_alerts = await self._check_delta_thresholds(db)
            alerts.extend(delta_alerts)
            
            # Check covered call opportunities
            cc_alerts = await self._check_covered_call_opportunities(db)
            alerts.extend(cc_alerts)
            
            # Save alerts to database
            for alert in alerts:
                db.add(alert)
            
            await db.commit()
            
            logger.info(f"Generated {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            await db.rollback()
            return []
    
    async def _check_profit_targets(self, db: AsyncSession) -> List[Alert]:
        """Check for profit target alerts."""
        alerts = []
        
        try:
            # Get option positions
            result = await db.execute(
                select(OptionPosition).where(OptionPosition.status == "open")
            )
            positions = result.scalars().all()
            
            for position in positions:
                try:
                    # Calculate profit percentage
                    if position.entry_price > 0:
                        profit_pct = ((position.current_price - position.entry_price) / position.entry_price) * 100
                        
                        profit_target_pct = await get_setting(db, "profit_target_pct", 70.0)
                        if profit_pct >= profit_target_pct:
                            alert = Alert(
                                type="profit_target",
                                symbol=position.symbol,
                                message=f"Profit target reached: {profit_pct:.1f}% profit on {position.symbol}",
                                data={
                                    "position_id": position.id,
                                    "profit_pct": profit_pct,
                                    "entry_price": position.entry_price,
                                    "current_price": position.current_price
                                },
                                created_at=pacific_now()
                            )
                            alerts.append(alert)
                
                except Exception as e:
                    logger.error(f"Error checking profit target for {position.symbol}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking profit targets: {e}")
        
        return alerts
    
    async def _check_time_decay(self, db: AsyncSession) -> List[Alert]:
        """Check for time decay alerts."""
        alerts = []
        
        try:
            # Get option positions close to expiration
            result = await db.execute(
                select(OptionPosition).where(OptionPosition.status == "open")
            )
            positions = result.scalars().all()
            
            for position in positions:
                try:
                    # TODO: Calculate days to expiration from option data
                    # For now, use a placeholder
                    dte = 30  # Placeholder
                    
                    time_decay_threshold_days = await get_setting(db, "time_decay_threshold_days", 7)
                    if dte <= time_decay_threshold_days:
                        # Check if premium has decayed significantly
                        if position.entry_price > 0:
                            premium_decay = ((position.entry_price - position.current_price) / position.entry_price) * 100
                            
                            time_decay_premium_threshold_pct = await get_setting(db, "time_decay_premium_threshold_pct", 20.0)
                            if premium_decay >= time_decay_premium_threshold_pct:
                                alert = Alert(
                                    type="time_decay",
                                    symbol=position.symbol,
                                    message=f"Time decay alert: {dte} days to expiration, {premium_decay:.1f}% premium decay on {position.symbol}",
                                    data={
                                        "position_id": position.id,
                                        "dte": dte,
                                        "premium_decay": premium_decay
                                    },
                                    created_at=pacific_now()
                                )
                                alerts.append(alert)
                
                except Exception as e:
                    logger.error(f"Error checking time decay for {position.symbol}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking time decay: {e}")
        
        return alerts
    
    async def _check_delta_thresholds(self, db: AsyncSession) -> List[Alert]:
        """Check for delta threshold alerts."""
        alerts = []
        
        try:
            # Get option positions
            result = await db.execute(
                select(OptionPosition).where(OptionPosition.status == "open")
            )
            positions = result.scalars().all()
            
            for position in positions:
                try:
                    # TODO: Get current delta from option data
                    # For now, use a placeholder
                    current_delta = 0.3  # Placeholder
                    
                    delta_threshold_close = await get_setting(db, "delta_threshold_close", 0.45)
                    if current_delta >= delta_threshold_close:
                        alert = Alert(
                            type="delta_threshold",
                            symbol=position.symbol,
                            message=f"Delta threshold alert: {current_delta:.2f} delta on {position.symbol}",
                            data={
                                "position_id": position.id,
                                "current_delta": current_delta,
                                "threshold": delta_threshold_close
                            },
                            created_at=pacific_now()
                        )
                        alerts.append(alert)
                
                except Exception as e:
                    logger.error(f"Error checking delta threshold for {position.symbol}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking delta thresholds: {e}")
        
        return alerts
    
    async def _check_covered_call_opportunities(self, db: AsyncSession) -> List[Alert]:
        """Check for covered call opportunities."""
        alerts = []
        
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
            
            for position in positions:
                try:
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
                        alert = Alert(
                            type="covered_call_opportunity",
                            symbol=position.symbol,
                            message=f"Covered call opportunity: {position.quantity} shares of {position.symbol} available",
                            data={
                                "position_id": position.id,
                                "quantity": position.quantity,
                                "current_price": position.current_price
                            },
                            created_at=pacific_now()
                        )
                        alerts.append(alert)
                
                except Exception as e:
                    logger.error(f"Error checking covered call opportunity for {position.symbol}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking covered call opportunities: {e}")
        
        return alerts
    
    async def get_pending_alerts(self, db: AsyncSession) -> List[Alert]:
        """Get pending alerts that haven't been processed."""
        try:
            alerts = db.query(Alert).filter(
                Alert.status == "pending"
            ).order_by(Alert.created_at.desc()).all()
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting pending alerts: {e}")
            return []
    
    async def mark_alert_processed(self, db: AsyncSession, alert_id: int) -> bool:
        """Mark an alert as processed."""
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            
            if not alert:
                return False
            
            alert.status = "processed"
            alert.processed_at = pacific_now()
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error marking alert {alert_id} as processed: {e}")
            db.rollback()
            return False
    
    async def cleanup_old_alerts(self, db: AsyncSession, days: int = 30) -> int:
        """Clean up old alerts."""
        try:
            cutoff_date = pacific_now() - timedelta(days=days)
            
            old_alerts = db.query(Alert).filter(
                and_(
                    Alert.created_at < cutoff_date,
                    Alert.status.in_(["processed", "dismissed"])
                )
            ).all()
            
            count = len(old_alerts)
            
            for alert in old_alerts:
                db.delete(alert)
            
            db.commit()
            
            logger.info(f"Cleaned up {count} old alerts")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
            db.rollback()
            return 0
