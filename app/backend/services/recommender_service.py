"""Recommendation service for generating and managing trade recommendations."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, select

from config import settings
from db.models import Recommendation, InterestingTicker, TickerQuote, Option, Position
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
    
    async def generate_recommendations(self, db: AsyncSession) -> List[Recommendation]:
        """Generate new recommendations."""
        try:
            logger.info("Starting recommendation generation...")
            
            # Get universe of tickers
            tickers = await self._get_universe(db)
            if not tickers:
                logger.warning("No tickers found in universe")
                return []
            
            # Get current positions to avoid duplicates
            current_positions = await self._get_current_positions(db)
            
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
                    
                    logger.info(f"Found {len(options)} options for {ticker.symbol}")
                    
                    # Score each option
                    scored_options = []
                    for option in options:
                        score_data = scoring_engine.score_option(option, current_price)
                        logger.debug(f"Option {option.symbol} {option.strike} scored: {score_data['score']}")
                        if score_data["score"] > 0:
                            scored_options.append((option, score_data))
                    
                    logger.info(f"Scored {len(scored_options)} options for {ticker.symbol}")
                    
                    # Sort by score and take top recommendations
                    scored_options.sort(key=lambda x: x[1]["score"], reverse=True)
                    scored_options = scored_options[:1]  # max_recommendations=1
                    
                    if not scored_options:
                        logger.debug(f"No options passed scoring for {ticker.symbol}")
                        continue
                    
                    # Create recommendation
                    recommendation = await self._create_recommendation(
                        db, ticker, scored_options[0][0]  # Get the option from the tuple
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
    
    async def _get_universe(self, db: AsyncSession) -> List[InterestingTicker]:
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
            result = await db.execute(
                select(InterestingTicker).where(InterestingTicker.active == True)
                .order_by(InterestingTicker.symbol)
                .limit(settings.max_tickers_per_cycle)
            )
            return result.scalars().all()
    
    async def _get_current_positions(self, db: AsyncSession) -> List[str]:
        """Get symbols of current positions."""
        try:
            result = await db.execute(
                select(Position).where(Position.status == "open")
            )
            positions = result.scalars().all()
            
            return [pos.symbol for pos in positions]
        except Exception as e:
            logger.warning(f"Could not query positions table: {e}")
            # Return empty list if table doesn't exist
            return []
    
    async def _get_options_for_ticker(self, db: AsyncSession, ticker: InterestingTicker) -> List[Option]:
        """Get suitable put options for a ticker."""
        # Get current market data
        try:
            tradier_data = TradierDataManager(db)
            await tradier_data.sync_ticker_data(ticker.symbol)
        except Exception as e:
            logger.warning(f"Failed to sync data for {ticker.symbol}: {e}")
            return []
        
        # Check if we have options data in the database
        result = await db.execute(
            select(Option).where(
                and_(
                    Option.symbol == ticker.symbol,
                    Option.option_type == "put"
                )
            )
        )
        options = result.scalars().all()
        
        # If no options in database, try to fetch from Tradier API
        if not options:
            logger.info(f"No options found in database for {ticker.symbol}, fetching from Tradier API")
            try:
                # Get available expirations
                expirations = await tradier_data.client.get_option_expirations(ticker.symbol)
                if expirations:
                    # Use the nearest expiration
                    expiration = expirations[0]
                    logger.info(f"Fetching options for {ticker.symbol} with expiration {expiration}")
                    
                    # Fetch options data
                    options = await tradier_data.sync_options_data(ticker.symbol, expiration)
                    logger.info(f"Fetched {len(options)} options for {ticker.symbol}")
                else:
                    logger.warning(f"No expirations available for {ticker.symbol}")
            except Exception as e:
                logger.error(f"Failed to fetch options from Tradier API for {ticker.symbol}: {e}")
                return []
        
        return options
    
    async def _create_recommendation(
        self, 
        db: AsyncSession, 
        ticker: InterestingTicker, 
        option: Option
    ) -> Optional[Recommendation]:
        """Create a recommendation for an option."""
        try:
            # Calculate score using the scoring engine
            scoring_engine = ScoringEngine(db)
            
            # Get current price from quote data
            quote_result = await db.execute(
                select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
            )
            quote = quote_result.scalar_one_or_none()
            current_price = quote.current_price if quote else 0
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
                        current_price
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
            await db.commit()
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error creating recommendation for {ticker.symbol}: {e}")
            await db.rollback()
            return None
    
    async def dismiss_recommendation(self, db: AsyncSession, recommendation_id: int) -> bool:
        """Dismiss a recommendation."""
        try:
            result = await db.execute(
                select(Recommendation).where(Recommendation.id == recommendation_id)
            )
            recommendation = result.scalar_one_or_none()
            
            if not recommendation:
                return False
            
            recommendation.status = "dismissed"
            recommendation.updated_at = datetime.utcnow()
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error dismissing recommendation {recommendation_id}: {e}")
            await db.rollback()
            return False
    
    async def cleanup_old_recommendations(self, db: AsyncSession, days: int = 7) -> int:
        """Clean up old recommendations."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db.execute(
                select(Recommendation).where(
                    and_(
                        Recommendation.created_at < cutoff_date,
                        Recommendation.status.in_(["proposed", "dismissed"])
                    )
                )
            )
            old_recommendations = result.scalars().all()
            
            count = len(old_recommendations)
            
            for rec in old_recommendations:
                await db.delete(rec)
            
            await db.commit()
            
            logger.info(f"Cleaned up {count} old recommendations")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old recommendations: {e}")
            await db.rollback()
            return 0
