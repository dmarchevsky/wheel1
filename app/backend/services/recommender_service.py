"""Recommendation service for generating and managing trade recommendations."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from config import settings
from db.models import Recommendation, Ticker, Option, Position
from core.scoring import ScoringEngine
from clients.openai_client import OpenAICacheManager
from clients.tradier import TradierDataManager

logger = logging.getLogger(__name__)


class RecommenderService:
    """Service for generating trade recommendations."""
    
    def __init__(self):
        self.scoring_engine = ScoringEngine()
        self.tradier_data = TradierDataManager()
    
    async def generate_recommendations(self, db: Session) -> List[Recommendation]:
        """Generate new recommendations."""
        try:
            logger.info("Starting recommendation generation...")
            
            # Get universe of tickers
            tickers = await self._get_universe(db)
            if not tickers:
                logger.warning("No tickers found in universe")
                return []
            
            # Get current positions to avoid duplicates
            current_positions = self._get_current_positions(db)
            
            recommendations = []
            
            for ticker in tickers[:settings.max_tickers_per_cycle]:
                try:
                    # Skip if we already have a position
                    if ticker.symbol in current_positions:
                        logger.debug(f"Skipping {ticker.symbol} - already have position")
                        continue
                    
                    # Get options data
                    options = await self._get_options_for_ticker(db, ticker)
                    if not options:
                        logger.debug(f"No suitable options found for {ticker.symbol}")
                        continue
                    
                    # Score options
                    scored_options = self.scoring_engine.get_top_recommendations(
                        options, 
                        max_recommendations=1
                    )
                    
                    if not scored_options:
                        continue
                    
                    # Create recommendation
                    recommendation = await self._create_recommendation(
                        db, ticker, scored_options[0]
                    )
                    
                    if recommendation:
                        recommendations.append(recommendation)
                        logger.info(f"Created recommendation for {ticker.symbol}")
                    
                except Exception as e:
                    logger.error(f"Error processing {ticker.symbol}: {e}")
                    continue
            
            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _get_universe(self, db: Session) -> List[Ticker]:
        """Get universe of tickers to analyze."""
        # Get active tickers
        tickers = db.query(Ticker).filter(
            Ticker.active == True
        ).order_by(Ticker.symbol).all()
        
        # TODO: Implement more sophisticated universe selection
        # For now, return all active tickers
        return tickers
    
    def _get_current_positions(self, db: Session) -> List[str]:
        """Get symbols of current positions."""
        positions = db.query(Position).filter(
            Position.status == "open"
        ).all()
        
        return [pos.symbol for pos in positions]
    
    async def _get_options_for_ticker(self, db: Session, ticker: Ticker) -> List[Option]:
        """Get suitable put options for a ticker."""
        # Get current market data
        try:
            await self.tradier_data.sync_ticker_data(db, ticker.symbol)
        except Exception as e:
            logger.warning(f"Failed to sync data for {ticker.symbol}: {e}")
            return []
        
        # Get put options within our criteria
        options = db.query(Option).filter(
            and_(
                Option.symbol == ticker.symbol,
                Option.option_type == "put",
                Option.dte >= 30,
                Option.dte <= 60,
                Option.delta >= settings.put_delta_min,
                Option.delta <= settings.put_delta_max,
                Option.open_interest >= settings.min_oi,
                Option.volume >= settings.min_volume
            )
        ).all()
        
        return options
    
    async def _create_recommendation(
        self, 
        db: Session, 
        ticker: Ticker, 
        option: Option
    ) -> Optional[Recommendation]:
        """Create a recommendation for an option."""
        try:
            # Calculate score
            score = self.scoring_engine.calculate_score(option)
            
            if score < 0.5:  # Minimum score threshold
                return None
            
            # Get OpenAI analysis if enabled
            analysis = None
            if settings.openai_enabled:
                try:
                    cache_manager = OpenAICacheManager(db)
                    analysis = await cache_manager.get_or_create_analysis(
                        ticker.symbol, 
                        ticker.current_price or 0
                    )
                except Exception as e:
                    logger.warning(f"Failed to get OpenAI analysis for {ticker.symbol}: {e}")
            
            # Create rationale
            rationale = {
                "annualized_yield": self.scoring_engine.calculate_annualized_yield(option),
                "dte": option.dte,
                "delta": option.delta,
                "iv_rank": option.iv_rank,
                "spread_pct": self.scoring_engine.calculate_bid_ask_spread(option),
                "open_interest": option.open_interest,
                "volume": option.volume,
                "liquidity_score": self.scoring_engine.calculate_liquidity_score(option),
                "risk_adjustment": self.scoring_engine.calculate_risk_adjustment(option),
                "qualitative_score": analysis.qualitative_score if analysis else 0.5
            }
            
            # Create recommendation
            recommendation = Recommendation(
                symbol=ticker.symbol,
                option_id=option.id,
                score=score,
                rationale_json=rationale,
                status="proposed",
                created_at=datetime.utcnow()
            )
            
            db.add(recommendation)
            db.commit()
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error creating recommendation for {ticker.symbol}: {e}")
            db.rollback()
            return None
    
    def dismiss_recommendation(self, db: Session, recommendation_id: int) -> bool:
        """Dismiss a recommendation."""
        try:
            recommendation = db.query(Recommendation).filter(
                Recommendation.id == recommendation_id
            ).first()
            
            if not recommendation:
                return False
            
            recommendation.status = "dismissed"
            recommendation.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error dismissing recommendation {recommendation_id}: {e}")
            db.rollback()
            return False
    
    def cleanup_old_recommendations(self, db: Session, days: int = 7) -> int:
        """Clean up old recommendations."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_recommendations = db.query(Recommendation).filter(
                and_(
                    Recommendation.created_at < cutoff_date,
                    Recommendation.status.in_(["proposed", "dismissed"])
                )
            ).all()
            
            count = len(old_recommendations)
            
            for rec in old_recommendations:
                db.delete(rec)
            
            db.commit()
            
            logger.info(f"Cleaned up {count} old recommendations")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old recommendations: {e}")
            db.rollback()
            return 0
