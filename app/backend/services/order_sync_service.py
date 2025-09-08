"""Service to sync order status with Tradier and keep database updated."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import Trade
from clients.tradier_account import TradierAccountClient
from utils.timezone import pacific_now

logger = logging.getLogger(__name__)


class OrderSyncService:
    """Service to sync order status between database and Tradier."""
    
    def __init__(self):
        self.production_client = TradierAccountClient(environment="production")
        self.sandbox_client = TradierAccountClient(environment="sandbox")
    
    async def sync_pending_orders(self, db: AsyncSession, environment: Optional[str] = None) -> Dict[str, int]:
        """Sync all pending orders with Tradier."""
        try:
            # Get all pending orders from database
            query = select(Trade).where(
                and_(
                    Trade.status == "pending",
                    Trade.order_id.is_not(None)
                )
            )
            
            if environment:
                query = query.where(Trade.environment == environment)
            
            result = await db.execute(query)
            pending_trades = result.scalars().all()
            
            logger.info(f"Found {len(pending_trades)} pending orders to sync")
            
            stats = {
                "synced": 0,
                "filled": 0,
                "cancelled": 0,
                "rejected": 0,
                "errors": 0
            }
            
            for trade in pending_trades:
                try:
                    success = await self._sync_single_order(db, trade)
                    if success:
                        stats["synced"] += 1
                        # Check final status for stats
                        if trade.status == "filled":
                            stats["filled"] += 1
                        elif trade.status == "cancelled":
                            stats["cancelled"] += 1
                        elif trade.status == "rejected":
                            stats["rejected"] += 1
                    else:
                        stats["errors"] += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing trade {trade.id} (order {trade.order_id}): {e}")
                    stats["errors"] += 1
            
            await db.commit()
            logger.info(f"Order sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in sync_pending_orders: {e}")
            await db.rollback()
            return {"errors": 1}
    
    async def _sync_single_order(self, db: AsyncSession, trade: Trade) -> bool:
        """Sync a single order with Tradier data."""
        try:
            # Choose client based on environment
            if trade.environment == "production":
                client = self.production_client
            else:
                client = self.sandbox_client
            
            # Get order status from Tradier
            async with client:
                order_data = await client.get_order_status(trade.order_id)
            
            if not order_data:
                logger.warning(f"No order data found for order ID {trade.order_id}")
                return False
            
            # Update trade with Tradier data (Tradier is master)
            old_status = trade.status
            trade.status = order_data.get("status", "unknown")
            trade.updated_at = pacific_now()
            
            # Update fill information - handle different Tradier field names
            filled_qty = (
                order_data.get("exec_quantity") or 
                order_data.get("quantity_executed") or 
                order_data.get("filled_quantity") or 
                0
            )
            
            # Get average fill price - Tradier uses different field names
            avg_price = (
                order_data.get("avg_fill_price") or
                order_data.get("avg_price") or 
                order_data.get("average_price") or
                order_data.get("price_executed") or
                order_data.get("last_fill_price") or
                0.0
            )
            
            if filled_qty and float(filled_qty) > 0:
                trade.filled_quantity = int(float(filled_qty))
                trade.avg_fill_price = float(avg_price) if avg_price else 0.0
                trade.remaining_quantity = trade.quantity - trade.filled_quantity
                
                # Set filled timestamp if newly filled
                if trade.status == "filled" and old_status != "filled":
                    trade.filled_at = pacific_now()
                
                # Update the trade price to reflect actual execution price for filled orders
                if trade.status == "filled" and trade.avg_fill_price > 0:
                    trade.price = trade.avg_fill_price
                    logger.info(f"Updated trade {trade.id} price from {trade.price} to actual fill price {trade.avg_fill_price}")
            
            # Handle partial fills
            elif trade.filled_quantity and trade.filled_quantity > 0:
                trade.remaining_quantity = trade.quantity - trade.filled_quantity
            
            # Store complete Tradier response for audit/debugging
            trade.tradier_data = order_data
            
            logger.info(f"Updated trade {trade.id}: {old_status} -> {trade.status}, filled: {trade.filled_quantity}/{trade.quantity}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing trade {trade.id}: {e}")
            return False
    
    async def sync_order_by_id(self, db: AsyncSession, order_id: str, environment: str) -> bool:
        """Sync a specific order by order ID."""
        try:
            # Find trade in database
            result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.order_id == order_id,
                        Trade.environment == environment
                    )
                )
            )
            trade = result.scalar_one_or_none()
            
            if not trade:
                logger.warning(f"Trade not found for order ID {order_id} in {environment}")
                return False
            
            success = await self._sync_single_order(db, trade)
            if success:
                await db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error syncing order {order_id}: {e}")
            await db.rollback()
            return False
    
    async def cleanup_old_pending_orders(self, db: AsyncSession, days_old: int = 7) -> int:
        """Mark very old pending orders as stale."""
        try:
            cutoff_date = pacific_now() - timedelta(days=days_old)
            
            result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.status == "pending",
                        Trade.created_at < cutoff_date
                    )
                )
            )
            old_trades = result.scalars().all()
            
            count = 0
            for trade in old_trades:
                # Try one final sync before marking as stale
                synced = await self._sync_single_order(db, trade)
                if not synced or trade.status == "pending":
                    trade.status = "stale"
                    trade.updated_at = pacific_now()
                    count += 1
                    logger.warning(f"Marked trade {trade.id} as stale (order {trade.order_id})")
            
            await db.commit()
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old orders: {e}")
            await db.rollback()
            return 0
    
    async def trigger_immediate_sync(self, db: AsyncSession, order_id: str, environment: str) -> bool:
        """Immediately sync a newly submitted order and start monitoring."""
        try:
            logger.info(f"Triggering immediate sync for order {order_id} in {environment}")
            
            # First attempt to sync the order immediately
            success = await self.sync_order_by_id(db, order_id, environment)
            
            if success:
                logger.info(f"Successfully synced new order {order_id}")
            else:
                logger.warning(f"Initial sync failed for order {order_id}, will retry in background")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in immediate sync for order {order_id}: {e}")
            return False
    
    async def get_order_history_from_tradier(self, environment: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get order history directly from Tradier for comparison."""
        try:
            client = self.production_client if environment == "production" else self.sandbox_client
            
            async with client:
                # Get recent orders from Tradier
                orders = await client.get_account_orders()
                return orders or []
                
        except Exception as e:
            logger.error(f"Error getting order history from Tradier: {e}")
            return []
    
    async def reconcile_with_tradier(self, db: AsyncSession, environment: str, days: int = 7) -> Dict[str, Any]:
        """Reconcile database orders with Tradier orders."""
        try:
            # Get orders from both sources
            tradier_orders = await self.get_order_history_from_tradier(environment, days)
            
            cutoff_date = pacific_now() - timedelta(days=days)
            result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.environment == environment,
                        Trade.created_at >= cutoff_date
                    )
                )
            )
            db_trades = result.scalars().all()
            
            # Create lookup sets
            tradier_order_ids = {str(order.get("id")) for order in tradier_orders if order.get("id")}
            db_order_ids = {trade.order_id for trade in db_trades if trade.order_id}
            
            # Find discrepancies
            missing_from_db = tradier_order_ids - db_order_ids
            missing_from_tradier = db_order_ids - tradier_order_ids
            
            reconciliation_report = {
                "tradier_orders_count": len(tradier_orders),
                "db_trades_count": len(db_trades),
                "missing_from_db": list(missing_from_db),
                "missing_from_tradier": list(missing_from_tradier),
                "in_sync_count": len(tradier_order_ids & db_order_ids)
            }
            
            if missing_from_db:
                logger.warning(f"Orders in Tradier but missing from DB: {missing_from_db}")
            
            if missing_from_tradier:
                logger.warning(f"Orders in DB but missing from Tradier: {missing_from_tradier}")
            
            return reconciliation_report
            
        except Exception as e:
            logger.error(f"Error in reconciliation: {e}")
            return {"error": str(e)}