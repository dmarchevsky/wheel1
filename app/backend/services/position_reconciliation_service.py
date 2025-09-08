"""Position reconciliation service for tracking position changes and detecting trades."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from db.models import Trade, PositionSnapshot, OptionEvent
from clients.tradier_account import TradierAccountClient
from utils.timezone import pacific_now

logger = logging.getLogger(__name__)


class PositionReconciliationService:
    """Service to reconcile positions with Tradier API and detect position changes."""
    
    def __init__(self):
        self.production_client = TradierAccountClient(environment="production")
        self.sandbox_client = TradierAccountClient(environment="sandbox")
    
    async def take_position_snapshot(self, db: AsyncSession, environment: str) -> List[PositionSnapshot]:
        """Take a snapshot of current positions from Tradier API."""
        try:
            # Choose client based on environment
            client = self.production_client if environment == "production" else self.sandbox_client
            
            # Get current positions from Tradier
            async with client:
                positions = await client.get_account_positions()
            
            logger.info(f"Retrieved {len(positions)} positions from Tradier API ({environment})")
            
            snapshots = []
            snapshot_time = pacific_now()
            
            for pos in positions:
                if not isinstance(pos, dict):
                    continue
                
                try:
                    # Determine symbol and contract symbol
                    symbol = pos.get("symbol", "")
                    contract_symbol = pos.get("contract_symbol") or pos.get("symbol", "")
                    
                    # Skip if no symbol
                    if not symbol:
                        continue
                    
                    snapshot = PositionSnapshot(
                        symbol=symbol,
                        contract_symbol=contract_symbol,
                        environment=environment,
                        quantity=float(pos.get("quantity", 0)),
                        cost_basis=float(pos.get("cost_basis", 0)) if pos.get("cost_basis") else None,
                        current_price=float(pos.get("current_price", 0)) if pos.get("current_price") else None,
                        market_value=float(pos.get("market_value", 0)) if pos.get("market_value") else None,
                        pnl=float(pos.get("pnl", 0)) if pos.get("pnl") else None,
                        pnl_percent=float(pos.get("pnl_percent", 0)) if pos.get("pnl_percent") else None,
                        snapshot_date=snapshot_time,
                        tradier_data=pos,
                        created_at=snapshot_time
                    )
                    
                    db.add(snapshot)
                    snapshots.append(snapshot)
                    
                except Exception as e:
                    logger.error(f"Error processing position {pos}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Created {len(snapshots)} position snapshots for {environment}")
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Error taking position snapshot for {environment}: {e}")
            await db.rollback()
            return []
    
    async def detect_position_changes(
        self, 
        db: AsyncSession, 
        environment: str, 
        hours_back: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Detect position changes by comparing current and previous snapshots."""
        try:
            # Get current positions snapshot
            current_snapshots = await self.take_position_snapshot(db, environment)
            
            # Get previous snapshot within time window
            cutoff_time = pacific_now() - timedelta(hours=hours_back)
            
            result = await db.execute(
                select(PositionSnapshot).where(
                    and_(
                        PositionSnapshot.environment == environment,
                        PositionSnapshot.snapshot_date >= cutoff_time,
                        PositionSnapshot.snapshot_date < pacific_now() - timedelta(minutes=30)  # At least 30 mins old
                    )
                ).order_by(desc(PositionSnapshot.snapshot_date))
            )
            
            previous_snapshots = result.scalars().all()
            
            if not previous_snapshots:
                logger.info(f"No previous snapshots found for {environment} within {hours_back} hours")
                return {"new_positions": [], "changed_positions": [], "disappeared_positions": []}
            
            # Use most recent previous snapshot
            prev_snapshot_time = previous_snapshots[0].snapshot_date
            prev_positions = [
                snap for snap in previous_snapshots 
                if snap.snapshot_date == prev_snapshot_time
            ]
            
            logger.info(f"Comparing {len(current_snapshots)} current positions vs {len(prev_positions)} previous positions")
            
            # Create lookup dictionaries
            current_by_contract = {snap.contract_symbol: snap for snap in current_snapshots}
            prev_by_contract = {snap.contract_symbol: snap for snap in prev_positions}
            
            changes = {
                "new_positions": [],
                "changed_positions": [],
                "disappeared_positions": []
            }
            
            # Find new positions
            for contract_symbol, current_pos in current_by_contract.items():
                if contract_symbol not in prev_by_contract:
                    changes["new_positions"].append({
                        "contract_symbol": contract_symbol,
                        "symbol": current_pos.symbol,
                        "quantity": current_pos.quantity,
                        "current_snapshot": current_pos,
                        "change_type": "new_position"
                    })
            
            # Find changed positions
            for contract_symbol, current_pos in current_by_contract.items():
                if contract_symbol in prev_by_contract:
                    prev_pos = prev_by_contract[contract_symbol]
                    
                    # Check for quantity changes
                    if abs(current_pos.quantity - prev_pos.quantity) > 0.001:  # Allow for floating point precision
                        changes["changed_positions"].append({
                            "contract_symbol": contract_symbol,
                            "symbol": current_pos.symbol,
                            "quantity_change": current_pos.quantity - prev_pos.quantity,
                            "prev_quantity": prev_pos.quantity,
                            "current_quantity": current_pos.quantity,
                            "current_snapshot": current_pos,
                            "previous_snapshot": prev_pos,
                            "change_type": "quantity_change"
                        })
            
            # Find disappeared positions
            for contract_symbol, prev_pos in prev_by_contract.items():
                if contract_symbol not in current_by_contract:
                    changes["disappeared_positions"].append({
                        "contract_symbol": contract_symbol,
                        "symbol": prev_pos.symbol,
                        "quantity": prev_pos.quantity,
                        "previous_snapshot": prev_pos,
                        "change_type": "disappeared_position"
                    })
            
            logger.info(f"Position changes detected: {len(changes['new_positions'])} new, "
                       f"{len(changes['changed_positions'])} changed, {len(changes['disappeared_positions'])} disappeared")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting position changes for {environment}: {e}")
            return {"new_positions": [], "changed_positions": [], "disappeared_positions": []}
    
    async def create_discovered_trades(
        self, 
        db: AsyncSession, 
        position_changes: Dict[str, List[Dict[str, Any]]], 
        environment: str
    ) -> List[Trade]:
        """Create trade records for positions that don't have matching orders in our database."""
        try:
            discovered_trades = []
            
            # Process new positions - these might be trades we didn't track
            for new_pos in position_changes["new_positions"]:
                trade = await self._create_discovered_trade_from_position(
                    db, new_pos, environment, "discovered_new"
                )
                if trade:
                    discovered_trades.append(trade)
            
            # Process disappeared positions - these might be expired/closed positions
            for disappeared_pos in position_changes["disappeared_positions"]:
                await self._handle_disappeared_position(db, disappeared_pos, environment)
            
            await db.commit()
            logger.info(f"Created {len(discovered_trades)} discovered trades for {environment}")
            
            return discovered_trades
            
        except Exception as e:
            logger.error(f"Error creating discovered trades for {environment}: {e}")
            await db.rollback()
            return []
    
    async def _create_discovered_trade_from_position(
        self, 
        db: AsyncSession, 
        position_info: Dict[str, Any], 
        environment: str,
        discovery_reason: str
    ) -> Optional[Trade]:
        """Create a trade record from a discovered position."""
        try:
            snapshot = position_info["current_snapshot"]
            
            # Check if we already have a trade for this contract
            existing_trade = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.option_symbol == snapshot.contract_symbol,
                        Trade.environment == environment
                    )
                )
            )
            
            if existing_trade.scalar_one_or_none():
                logger.debug(f"Trade already exists for {snapshot.contract_symbol}")
                return None
            
            # Parse option details from contract symbol
            option_details = self._parse_option_symbol(snapshot.contract_symbol)
            
            # Determine side based on position quantity
            side = "sell" if snapshot.quantity < 0 else "buy"
            
            # Create discovered trade
            trade = Trade(
                symbol=snapshot.symbol,
                option_symbol=snapshot.contract_symbol,
                side=side,
                quantity=abs(int(snapshot.quantity)),
                price=abs(snapshot.cost_basis / snapshot.quantity) if snapshot.quantity != 0 else 0.0,
                status="discovered",  # Special status for discovered trades
                order_type="unknown",
                class_type="option" if len(snapshot.contract_symbol) > 10 else "equity",
                filled_quantity=abs(int(snapshot.quantity)),
                avg_fill_price=abs(snapshot.cost_basis / snapshot.quantity) if snapshot.quantity != 0 else None,
                remaining_quantity=0,
                environment=environment,
                strike=option_details.get("strike"),
                expiry=option_details.get("expiry_date"),
                option_type=option_details.get("option_type"),
                created_at=pacific_now(),
                filled_at=pacific_now(),
                tradier_data={
                    "discovery_reason": discovery_reason,
                    "discovered_from_snapshot": snapshot.id if hasattr(snapshot, 'id') else None,
                    "original_position_data": snapshot.tradier_data
                }
            )
            
            db.add(trade)
            logger.info(f"Created discovered trade for {snapshot.contract_symbol} ({discovery_reason})")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error creating discovered trade: {e}")
            return None
    
    async def _handle_disappeared_position(
        self, 
        db: AsyncSession, 
        position_info: Dict[str, Any], 
        environment: str
    ):
        """Handle a position that disappeared (likely expired or closed)."""
        try:
            prev_snapshot = position_info["previous_snapshot"]
            contract_symbol = position_info["contract_symbol"]
            
            # Find matching trade
            result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.option_symbol == contract_symbol,
                        Trade.environment == environment,
                        Trade.status.in_(["filled", "discovered"])
                    )
                )
            )
            
            trade = result.scalar_one_or_none()
            
            if trade:
                # Check if this is likely an expiration
                is_option_expiry = self._is_likely_option_expiration(trade, prev_snapshot)
                
                if is_option_expiry:
                    await self._handle_option_expiration(db, trade, prev_snapshot)
                else:
                    await self._handle_position_close(db, trade, prev_snapshot)
                
            else:
                logger.warning(f"No matching trade found for disappeared position {contract_symbol}")
                
        except Exception as e:
            logger.error(f"Error handling disappeared position: {e}")
    
    def _is_likely_option_expiration(self, trade: Trade, prev_snapshot: PositionSnapshot) -> bool:
        """Check if position disappearance is likely due to option expiration."""
        if not trade.expiry or trade.class_type != "option":
            return False
        
        # Check if we're past expiry date
        expiry_date = trade.expiry.date()
        snapshot_date = prev_snapshot.snapshot_date.date()
        
        return snapshot_date >= expiry_date
    
    async def _handle_option_expiration(
        self, 
        db: AsyncSession, 
        trade: Trade, 
        prev_snapshot: PositionSnapshot
    ):
        """Handle option expiration event."""
        try:
            # Calculate final P&L
            # For sold options: premium received is profit if expires worthless
            # For bought options: premium paid is loss if expires worthless
            if trade.side == "sell":
                # Sold option expired worthless - keep the premium
                final_pnl = (trade.avg_fill_price or trade.price) * trade.filled_quantity * 100
                expiration_outcome = "expired_profitable"
            else:
                # Bought option expired worthless - lose the premium
                final_pnl = -((trade.avg_fill_price or trade.price) * trade.filled_quantity * 100)
                expiration_outcome = "expired_loss"
            
            # Update trade record
            trade.status = "expired"
            trade.expiration_outcome = expiration_outcome
            trade.final_pnl = final_pnl
            trade.closed_at = pacific_now()
            trade.updated_at = pacific_now()
            
            # Create option event record
            event = OptionEvent(
                trade_id=trade.id,
                symbol=trade.symbol,
                contract_symbol=trade.option_symbol,
                event_type="expiration",
                event_date=trade.expiry or pacific_now(),
                final_pnl=final_pnl,
                environment=trade.environment,
                tradier_data={
                    "last_position_snapshot": prev_snapshot.tradier_data,
                    "expiration_detection": "position_disappeared"
                }
            )
            
            db.add(event)
            logger.info(f"Handled option expiration for {trade.option_symbol} - P&L: ${final_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling option expiration: {e}")
    
    async def _handle_position_close(
        self, 
        db: AsyncSession, 
        trade: Trade, 
        prev_snapshot: PositionSnapshot
    ):
        """Handle position that was closed early (not expiration)."""
        try:
            # Use the P&L from the snapshot as the final P&L
            final_pnl = prev_snapshot.pnl or 0.0
            
            # Update trade record
            trade.status = "closed"
            trade.expiration_outcome = "closed_early"
            trade.final_pnl = final_pnl
            trade.closed_at = pacific_now()
            trade.updated_at = pacific_now()
            
            # Create option event record if it's an option
            if trade.class_type == "option":
                event = OptionEvent(
                    trade_id=trade.id,
                    symbol=trade.symbol,
                    contract_symbol=trade.option_symbol,
                    event_type="early_close",
                    event_date=pacific_now(),
                    final_pnl=final_pnl,
                    environment=trade.environment,
                    tradier_data={
                        "last_position_snapshot": prev_snapshot.tradier_data,
                        "close_detection": "position_disappeared"
                    }
                )
                
                db.add(event)
            
            logger.info(f"Handled position close for {trade.option_symbol or trade.symbol} - P&L: ${final_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling position close: {e}")
    
    def _parse_option_symbol(self, symbol: str) -> Dict[str, Any]:
        """Parse option symbol to extract details."""
        try:
            option_details = {"underlying_symbol": None, "strike": None, "expiry_date": None, "option_type": None}
            
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
                
                # Extract underlying symbol (first part before digits)
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
                            option_details["expiry_date"] = datetime(year, month, day, tzinfo=pacific_now().tzinfo)
                        except ValueError:
                            pass
            
            return option_details
            
        except Exception as e:
            logger.warning(f"Error parsing option symbol {symbol}: {e}")
            return {"underlying_symbol": symbol}
    
    async def run_full_reconciliation(
        self, 
        db: AsyncSession, 
        environment: str
    ) -> Dict[str, Any]:
        """Run complete position reconciliation process."""
        try:
            logger.info(f"Starting full position reconciliation for {environment}")
            
            # Step 1: Detect position changes
            changes = await self.detect_position_changes(db, environment)
            
            # Step 2: Create trades for discovered positions
            discovered_trades = await self.create_discovered_trades(db, changes, environment)
            
            # Step 3: Generate summary
            summary = {
                "environment": environment,
                "timestamp": pacific_now().isoformat(),
                "position_changes": {
                    "new_positions": len(changes["new_positions"]),
                    "changed_positions": len(changes["changed_positions"]),
                    "disappeared_positions": len(changes["disappeared_positions"])
                },
                "discovered_trades": len(discovered_trades),
                "details": changes
            }
            
            logger.info(f"Reconciliation completed for {environment}: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in full reconciliation for {environment}: {e}")
            return {
                "environment": environment,
                "timestamp": pacific_now().isoformat(),
                "error": str(e),
                "status": "failed"
            }