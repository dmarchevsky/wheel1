"""Service for enhanced orders view with Tradier API and database sync."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.models import Trade, PositionSnapshot, OptionEvent
from clients.tradier_account import TradierAccountClient
from services.position_reconciliation_service import PositionReconciliationService
from utils.timezone import pacific_now

logger = logging.getLogger(__name__)


class OrdersViewService:
    """Service to provide enhanced orders view with Tradier API and database sync."""
    
    def __init__(self):
        self.production_client = TradierAccountClient(environment="production")
        self.sandbox_client = TradierAccountClient(environment="sandbox")
        self.reconciliation_service = PositionReconciliationService()
    
    async def get_enhanced_orders(
        self, 
        db: AsyncSession, 
        environment: str, 
        days_back: int = 30,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get enhanced orders view with Tradier as master source."""
        try:
            # Choose client based on environment
            client = self.production_client if environment == "production" else self.sandbox_client
            
            # Get orders from Tradier (master source)
            async with client:
                tradier_orders = await client.get_account_orders()
            
            logger.info(f"Raw Tradier orders response: {tradier_orders}")
            logger.info(f"Orders response type: {type(tradier_orders)}")
            
            if not tradier_orders or not isinstance(tradier_orders, list):
                logger.info(f"No orders found from Tradier API - orders: {tradier_orders}")
                return []
            
            # Filter for stocks and options only, and apply date/status filters
            filtered_orders = []
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            logger.info(f"Filtering {len(tradier_orders)} orders with cutoff_date: {cutoff_date}")
            
            for order in tradier_orders:
                if not isinstance(order, dict):
                    continue
                
                try:
                    # Parse order date
                    order_date_str = order.get("create_date", "")
                    order_date = None
                    if order_date_str:
                        # Handle different date formats
                        try:
                            order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
                        except:
                            # Try alternative parsing
                            order_date = datetime.strptime(order_date_str[:19], "%Y-%m-%dT%H:%M:%S")
                        
                        if order_date < cutoff_date:
                            logger.info(f"Skipping order {order.get('id')} - created {order_date} is before cutoff {cutoff_date}")
                            continue
                    
                    # Filter by status if specified
                    if status_filter and order.get("status") != status_filter:
                        continue
                    
                    # Get symbol from instrument
                    instrument = order.get("instrument", {})
                    symbol = ""
                    if isinstance(instrument, dict):
                        symbol = instrument.get("symbol", "")
                    else:
                        symbol = order.get("symbol", "")
                    
                    if not symbol:
                        continue
                    
                    # Filter for stocks and options only
                    if self._is_stock_or_option(order, symbol):
                        filtered_orders.append(order)
                        
                except Exception as order_error:
                    logger.warning(f"Error processing order {order.get('id', 'unknown')}: {order_error}")
                    continue
            
            logger.info(f"Found {len(filtered_orders)} stock/option orders from Tradier")
            
            # Get existing trades from database
            existing_trades = await self._get_existing_trades(db, environment)
            trades_by_order_id = {trade.order_id: trade for trade in existing_trades}
            
            # Process each order and sync with database
            enhanced_orders = []
            sync_stats = {"created": 0, "updated": 0, "errors": 0}
            
            for order in filtered_orders:
                try:
                    enhanced_order = await self._process_order(
                        db, order, trades_by_order_id, environment, sync_stats
                    )
                    if enhanced_order:
                        enhanced_orders.append(enhanced_order)
                        
                except Exception as process_error:
                    logger.error(f"Error processing order {order.get('id', 'unknown')}: {process_error}")
                    sync_stats["errors"] += 1
                    continue
            
            # Commit all database changes
            await db.commit()
            
            logger.info(f"Orders view sync completed: {sync_stats}")
            return enhanced_orders
            
        except Exception as e:
            logger.error(f"Error in get_enhanced_orders: {e}")
            await db.rollback()
            return []
    
    async def get_comprehensive_trading_view(
        self, 
        db: AsyncSession, 
        environment: str, 
        include_positions: bool = True,
        include_reconciliation: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive view of all trading activity including orders, trades, and positions."""
        try:
            logger.info(f"Generating comprehensive trading view for {environment}")
            
            # 1. Get enhanced orders (recent Tradier orders + database sync)
            enhanced_orders = await self.get_enhanced_orders(db, environment, days_back=30)
            
            # 2. Get all database trades for this environment
            db_trades_result = await db.execute(
                select(Trade).where(
                    Trade.environment == environment
                ).order_by(Trade.created_at.desc())
            )
            db_trades = db_trades_result.scalars().all()
            
            # 3. Get current positions if requested
            positions = []
            if include_positions:
                try:
                    client = self.production_client if environment == "production" else self.sandbox_client
                    async with client:
                        positions = await client.get_account_positions()
                except Exception as pos_error:
                    logger.warning(f"Could not fetch positions: {pos_error}")
                    positions = []
            
            # 4. Run position reconciliation if requested
            reconciliation_results = None
            if include_reconciliation:
                try:
                    reconciliation_results = await self.reconciliation_service.run_full_reconciliation(
                        db, environment
                    )
                except Exception as recon_error:
                    logger.warning(f"Reconciliation failed: {recon_error}")
                    reconciliation_results = {"error": str(recon_error)}
            
            # 5. Get option events
            option_events_result = await db.execute(
                select(OptionEvent).where(
                    OptionEvent.environment == environment
                ).order_by(OptionEvent.event_date.desc()).limit(50)
            )
            option_events = option_events_result.scalars().all()
            
            # 6. Build comprehensive response
            response = {
                "environment": environment,
                "timestamp": pacific_now().isoformat(),
                "summary": {
                    "total_orders": len(enhanced_orders),
                    "total_trades": len(db_trades),
                    "total_positions": len(positions),
                    "total_option_events": len(option_events)
                },
                "orders": enhanced_orders,
                "database_trades": [
                    self._format_trade_for_response(trade) for trade in db_trades
                ],
                "current_positions": positions,
                "option_events": [
                    self._format_option_event_for_response(event) for event in option_events
                ],
                "reconciliation": reconciliation_results
            }
            
            # 7. Add trade status breakdown
            status_counts = {}
            for trade in db_trades:
                status = trade.status or "unknown"
                status_counts[status] = status_counts.get(status, 0) + 1
            
            response["summary"]["trade_status_breakdown"] = status_counts
            
            # 8. Add P&L summary
            total_pnl = sum(
                trade.final_pnl for trade in db_trades 
                if trade.final_pnl is not None
            )
            
            response["summary"]["total_realized_pnl"] = total_pnl
            
            logger.info(f"Generated comprehensive view with {len(enhanced_orders)} orders, "
                       f"{len(db_trades)} trades, {len(positions)} positions")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in get_comprehensive_trading_view: {e}")
            return {
                "environment": environment,
                "timestamp": pacific_now().isoformat(),
                "error": str(e),
                "status": "failed"
            }
    
    def _format_trade_for_response(self, trade: Trade) -> Dict[str, Any]:
        """Format trade object for API response."""
        return {
            "id": trade.id,
            "recommendation_id": trade.recommendation_id,
            "symbol": trade.symbol,
            "option_symbol": trade.option_symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "order_id": trade.order_id,
            "status": trade.status,
            "order_type": trade.order_type,
            "duration": trade.duration,
            "class_type": trade.class_type,
            "filled_quantity": trade.filled_quantity,
            "avg_fill_price": trade.avg_fill_price,
            "remaining_quantity": trade.remaining_quantity,
            "environment": trade.environment,
            "strike": trade.strike,
            "expiry": trade.expiry.isoformat() if trade.expiry else None,
            "option_type": trade.option_type,
            "expiration_outcome": trade.expiration_outcome,
            "final_pnl": trade.final_pnl,
            "created_at": trade.created_at.isoformat(),
            "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
            "filled_at": trade.filled_at.isoformat() if trade.filled_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None
        }
    
    def _format_option_event_for_response(self, event: OptionEvent) -> Dict[str, Any]:
        """Format option event object for API response."""
        return {
            "id": event.id,
            "trade_id": event.trade_id,
            "symbol": event.symbol,
            "contract_symbol": event.contract_symbol,
            "event_type": event.event_type,
            "event_date": event.event_date.isoformat(),
            "final_price": event.final_price,
            "final_pnl": event.final_pnl,
            "environment": event.environment,
            "created_at": event.created_at.isoformat()
        }
    
    def _is_stock_or_option(self, order: Dict[str, Any], symbol: str) -> bool:
        """Check if order is for stock or option."""
        try:
            # Check instrument class
            instrument = order.get("instrument", {})
            if isinstance(instrument, dict):
                instrument_class = instrument.get("class", "")
                if instrument_class in ["equity", "option"]:
                    return True
            
            # Fallback: detect from symbol pattern
            if len(symbol) <= 6 and symbol.isalpha():
                return True  # Stock symbol
            elif len(symbol) > 10 and any(c in symbol for c in ['P', 'C']) and any(c.isdigit() for c in symbol):
                return True  # Option symbol
            
            return False
            
        except Exception:
            return False
    
    async def _get_existing_trades(self, db: AsyncSession, environment: str) -> List[Trade]:
        """Get existing trades from database for the environment."""
        try:
            result = await db.execute(
                select(Trade).where(Trade.environment == environment)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting existing trades: {e}")
            return []
    
    async def _process_order(
        self, 
        db: AsyncSession, 
        order: Dict[str, Any], 
        trades_by_order_id: Dict[str, Trade],
        environment: str,
        sync_stats: Dict[str, int]
    ) -> Optional[Dict[str, Any]]:
        """Process single order and sync with database."""
        try:
            order_id = str(order.get("id", ""))
            if not order_id:
                return None
            
            # Extract order details
            instrument = order.get("instrument", {})
            symbol = instrument.get("symbol", "") if isinstance(instrument, dict) else order.get("symbol", "")
            side = order.get("side", "")
            quantity = int(order.get("quantity", 0))
            order_type = order.get("type", "")
            price = float(order.get("price", 0)) if order.get("price") else None
            status = order.get("status", "")
            duration = order.get("duration", "")
            created_at = order.get("create_date", "")
            filled_quantity = int(order.get("exec_quantity", 0)) if order.get("exec_quantity") else None
            avg_fill_price = float(order.get("avg_price", 0)) if order.get("avg_price") else None
            
            # Determine instrument type and parse option details
            instrument_type, option_details = self._parse_instrument_details(symbol, instrument)
            
            # Check if trade exists in database
            existing_trade = trades_by_order_id.get(order_id)
            trade_id = None
            database_synced = False
            
            if existing_trade:
                # Update existing trade with Tradier data (Tradier is master)
                await self._update_existing_trade(existing_trade, order, sync_stats)
                trade_id = existing_trade.id
                database_synced = True
            else:
                # Create new trade record
                new_trade = await self._create_new_trade(db, order, environment, option_details, sync_stats)
                if new_trade:
                    trade_id = new_trade.id
                    database_synced = True
            
            # Calculate additional fields
            total_value = None
            if avg_fill_price and filled_quantity:
                if instrument_type == "option":
                    total_value = avg_fill_price * filled_quantity * 100  # Options are per-share basis
                else:
                    total_value = avg_fill_price * filled_quantity
            
            remaining_quantity = quantity - (filled_quantity or 0)
            
            # Build enhanced order response
            enhanced_order = {
                "order_id": order_id,
                "symbol": option_details.get("underlying_symbol", symbol),
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "price": price,
                "status": status,
                "duration": duration,
                "created_at": created_at,
                "filled_quantity": filled_quantity,
                "avg_fill_price": avg_fill_price,
                "instrument_type": instrument_type,
                "underlying_symbol": option_details.get("underlying_symbol"),
                "option_symbol": symbol if instrument_type == "option" else None,
                "strike": option_details.get("strike"),
                "expiration": option_details.get("expiration"),
                "option_type": option_details.get("option_type"),
                "trade_id": trade_id,
                "database_synced": database_synced,
                "environment": environment,
                "total_value": total_value,
                "remaining_quantity": remaining_quantity,
                "commission": order.get("commission", 0),
                "tradier_data": order
            }
            
            return enhanced_order
            
        except Exception as e:
            logger.error(f"Error processing order {order.get('id', 'unknown')}: {e}")
            return None
    
    def _parse_instrument_details(self, symbol: str, instrument: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Parse instrument details to determine type and extract option info."""
        try:
            # Check instrument class first
            if isinstance(instrument, dict):
                instrument_class = instrument.get("class", "")
                if instrument_class == "option":
                    return "option", self._parse_option_symbol(symbol)
                elif instrument_class == "equity":
                    return "equity", {"underlying_symbol": symbol}
            
            # Fallback: detect from symbol
            if len(symbol) > 10 and any(c in symbol for c in ['P', 'C']) and any(c.isdigit() for c in symbol):
                return "option", self._parse_option_symbol(symbol)
            else:
                return "equity", {"underlying_symbol": symbol}
                
        except Exception:
            return "equity", {"underlying_symbol": symbol}
    
    def _parse_option_symbol(self, symbol: str) -> Dict[str, Any]:
        """Parse option symbol to extract details."""
        try:
            option_details = {"underlying_symbol": None, "strike": None, "expiration": None, "option_type": None}
            
            if len(symbol) > 10:
                # Extract option type (P or C)
                if 'P' in symbol:
                    option_details["option_type"] = 'put'
                    strike_pos = symbol.find('P')
                elif 'C' in symbol:
                    option_details["option_type"] = 'call'
                    strike_pos = symbol.find('C')
                else:
                    return option_details
                
                # Extract underlying symbol (first 1-6 characters)
                underlying_end = 0
                for i, char in enumerate(symbol):
                    if char.isdigit():
                        underlying_end = i
                        break
                
                if underlying_end > 0:
                    option_details["underlying_symbol"] = symbol[:underlying_end]
                
                # Extract strike price
                if strike_pos > 0:
                    strike_str = symbol[strike_pos+1:]
                    if strike_str.isdigit() and len(strike_str) >= 5:
                        option_details["strike"] = float(strike_str) / 1000.0
                    
                    # Extract expiration date (YYMMDD format)
                    date_part = symbol[underlying_end:strike_pos]
                    if len(date_part) == 6 and date_part.isdigit():
                        try:
                            year = 2000 + int(date_part[:2])
                            month = int(date_part[2:4])
                            day = int(date_part[4:6])
                            option_details["expiration"] = f"{year}-{month:02d}-{day:02d}"
                        except ValueError:
                            pass
            
            return option_details
            
        except Exception as e:
            logger.warning(f"Error parsing option symbol {symbol}: {e}")
            return {"underlying_symbol": symbol}
    
    async def _update_existing_trade(self, trade: Trade, order: Dict[str, Any], sync_stats: Dict[str, int]):
        """Update existing trade with Tradier data."""
        try:
            # Update with Tradier data (Tradier is master)
            trade.status = order.get("status", trade.status)
            trade.filled_quantity = int(order.get("exec_quantity", 0)) if order.get("exec_quantity") else trade.filled_quantity
            trade.avg_fill_price = float(order.get("avg_price", 0)) if order.get("avg_price") else trade.avg_fill_price
            trade.remaining_quantity = trade.quantity - (trade.filled_quantity or 0)
            trade.tradier_data = order
            trade.updated_at = pacific_now()
            
            # Set filled timestamp if newly filled
            if trade.status == "filled" and not trade.filled_at and trade.filled_quantity and trade.filled_quantity > 0:
                trade.filled_at = pacific_now()
            
            sync_stats["updated"] += 1
            
        except Exception as e:
            logger.error(f"Error updating trade {trade.id}: {e}")
            sync_stats["errors"] += 1
    
    async def _create_new_trade(
        self, 
        db: AsyncSession, 
        order: Dict[str, Any], 
        environment: str,
        option_details: Dict[str, Any],
        sync_stats: Dict[str, int]
    ) -> Optional[Trade]:
        """Create new trade record from Tradier order."""
        try:
            instrument = order.get("instrument", {})
            symbol = instrument.get("symbol", "") if isinstance(instrument, dict) else order.get("symbol", "")
            
            # Parse creation date
            created_at = pacific_now()
            if order.get("create_date"):
                try:
                    created_at = datetime.fromisoformat(order.get("create_date").replace('Z', '+00:00'))
                except:
                    pass
            
            # Parse filled date
            filled_at = None
            filled_quantity = int(order.get("exec_quantity", 0)) if order.get("exec_quantity") else None
            if order.get("status") == "filled" and filled_quantity and filled_quantity > 0:
                filled_at = created_at  # Use creation date as fallback
            
            # Parse expiry date
            expiry_date = None
            if option_details.get("expiration"):
                try:
                    expiry_date = datetime.strptime(option_details["expiration"], "%Y-%m-%d")
                except:
                    pass
            
            new_trade = Trade(
                symbol=option_details.get("underlying_symbol", symbol),
                option_symbol=symbol if len(symbol) > 10 else None,
                side=order.get("side", ""),
                quantity=int(order.get("quantity", 0)),
                price=float(order.get("price", 0)) if order.get("price") else 0.0,
                order_id=str(order.get("id", "")),
                status=order.get("status", "pending"),
                order_type=order.get("type", ""),
                duration=order.get("duration", ""),
                class_type="option" if len(symbol) > 10 else "equity",
                filled_quantity=filled_quantity,
                avg_fill_price=float(order.get("avg_price", 0)) if order.get("avg_price") else None,
                remaining_quantity=int(order.get("quantity", 0)) - (filled_quantity or 0),
                environment=environment,
                strike=option_details.get("strike"),
                expiry=expiry_date,
                option_type=option_details.get("option_type"),
                tradier_data=order,
                created_at=created_at,
                filled_at=filled_at
            )
            
            db.add(new_trade)
            sync_stats["created"] += 1
            logger.info(f"Created new trade record for Tradier order {order.get('id')}")
            
            return new_trade
            
        except Exception as e:
            logger.error(f"Error creating trade for order {order.get('id', 'unknown')}: {e}")
            sync_stats["errors"] += 1
            return None