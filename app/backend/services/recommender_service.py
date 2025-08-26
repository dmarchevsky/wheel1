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
from services.universe_service import UniverseService

logger = logging.getLogger(__name__)


class RecommenderService:
    """Service for generating trade recommendations."""
    
    def __init__(self):
        # Services will be initialized with db when needed
        pass
    
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
                    scoring_engine = ScoringEngine(db)
                    # Get current price for the ticker
                    current_price = ticker.current_price or 0
                    
                    # Score each option
                    scored_options = []
                    for option in options:
                        score_data = scoring_engine.score_option(option, current_price)
                        if score_data["score"] > 0:
                            scored_options.append((option, score_data))
                    
                    # Sort by score and take top recommendations
                    scored_options.sort(key=lambda x: x[1]["score"], reverse=True)
                    scored_options = scored_options[:1]  # max_recommendations=1
                    
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
        """Get universe of tickers to analyze using sophisticated filtering."""
        try:
            universe_service = UniverseService(db)
            tickers = await universe_service.get_filtered_universe()
            
            # Apply sector diversification if we have enough tickers
            if len(tickers) > settings.max_tickers_per_cycle:
                tickers = universe_service.optimize_for_diversification(
                    tickers, settings.max_tickers_per_cycle
                )
            
            # Log sector distribution
            sector_dist = universe_service.get_sector_diversification(tickers)
            logger.info(f"Selected universe sector distribution: {sector_dist}")
            
            return tickers
            
        except Exception as e:
            logger.error(f"Error in universe selection: {e}")
            # Fallback to basic selection
            return db.query(Ticker).filter(
                Ticker.active == True
            ).order_by(Ticker.symbol).limit(settings.max_tickers_per_cycle).all()
    
    def _get_current_positions(self, db: Session) -> List[str]:
        """Get symbols of current positions."""
        try:
            positions = db.query(Position).filter(
                Position.status == "open"
            ).all()
            
            return [pos.symbol for pos in positions]
        except Exception as e:
            logger.warning(f"Could not query positions table: {e}")
            # Return empty list if table doesn't exist
            return []
    
    async def _get_options_for_ticker(self, db: Session, ticker: Ticker) -> List[Option]:
        """Get suitable put options for a ticker."""
        # Get current market data
        try:
            tradier_data = TradierDataManager(db)
            await tradier_data.sync_ticker_data(db, ticker.symbol)
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
            # Calculate score using the scoring engine
            scoring_engine = ScoringEngine(db)
            current_price = ticker.current_price or 0
            score_data = scoring_engine.score_option(option, current_price)
            score = score_data["score"]
            
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
            
            # Create rationale using the score data
            rationale = score_data["rationale"]
            rationale.update({
                "dte": option.dte,
                "delta": option.delta,
                "iv_rank": option.iv_rank,
                "open_interest": option.open_interest,
                "volume": option.volume,
                "qualitative_score": analysis.qualitative_score if analysis else 0.5
            })
            
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
