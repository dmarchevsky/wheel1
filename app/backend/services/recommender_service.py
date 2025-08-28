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
    
    async def generate_recommendations(self, db: AsyncSession, fast_mode: bool = True) -> List[Recommendation]:
        """Generate new recommendations."""
        start_time = datetime.utcnow()
        logger.info(f"🚀 Starting recommendation generation (fast_mode={fast_mode})...")
        logger.info(f"📊 Max tickers per cycle: {settings.max_tickers_per_cycle}")
        logger.info(f"📊 Max recommendations: {settings.max_recommendations}")
        
        try:
            # Step 1: Get universe of tickers
            logger.info("🔍 Step 1: Getting universe of tickers...")
            tickers = await self._get_universe(db, fast_mode=fast_mode)
            if not tickers:
                logger.warning("❌ No tickers found in universe")
                return []
            
            logger.info(f"✅ Found {len(tickers)} tickers in universe")
            
            # Step 2: Get current positions to avoid duplicates
            logger.info("🔍 Step 2: Getting current positions...")
            current_positions = await self._get_current_positions(db)
            logger.info(f"📊 Current positions: {current_positions}")
            
            # Step 3: Process each ticker
            logger.info("🔍 Step 3: Processing tickers for recommendations...")
            recommendations = []
            processed_count = 0
            skipped_count = 0
            error_count = 0
            
            for ticker in tickers[:settings.max_tickers_per_cycle]:
                processed_count += 1
                logger.info(f"📈 Processing ticker {processed_count}/{min(len(tickers), settings.max_tickers_per_cycle)}: {ticker.symbol}")
                logger.info(f"   📊 Ticker details: sector={ticker.sector}, market_cap=${ticker.market_cap}, pe_ratio={ticker.pe_ratio}")
                
                try:
                    # Skip if we already have a position
                    if ticker.symbol in current_positions:
                        logger.info(f"⏭️  Skipping {ticker.symbol} - already have position")
                        skipped_count += 1
                        continue
                    
                    # Get options data
                    logger.info(f"🔍 Getting options data for {ticker.symbol}...")
                    options = await self._get_options_for_ticker(db, ticker)
                    if not options:
                        logger.info(f"❌ No suitable options found for {ticker.symbol}")
                        skipped_count += 1
                        continue
                    
                    logger.info(f"✅ Found {len(options)} options for {ticker.symbol}")
                    
                    # Score each option
                    logger.info(f"🎯 Scoring options for {ticker.symbol}...")
                    scored_options = []
                    scoring_engine = ScoringEngine(db)
                    
                    for i, option in enumerate(options):
                        logger.info(f"   📊 Scoring option {i+1}/{len(options)}: {option.symbol} {option.strike} {option.expiry}")
                        
                        # Get current price for scoring
                        quote_result = await db.execute(
                            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                        )
                        quote = quote_result.scalar_one_or_none()
                        current_price = quote.current_price if quote else 0
                        
                        if current_price == 0:
                            logger.warning(f"⚠️  No current price found for {ticker.symbol}, skipping option scoring")
                            continue
                        
                        score_data = scoring_engine.score_option(option, current_price)
                        score = score_data["score"]
                        
                        logger.info(f"   🎯 Option score: {score:.3f}")
                        logger.info(f"   📊 Score breakdown: {score_data.get('rationale', {})}")
                        
                        if score > 0:
                            scored_options.append((option, score_data))
                            logger.info(f"   ✅ Option passed minimum score threshold")
                        else:
                            logger.info(f"   ❌ Option failed minimum score threshold")
                    
                    logger.info(f"📊 Scored {len(scored_options)} options for {ticker.symbol}")
                    
                    # Sort by score and take top recommendations
                    if scored_options:
                        scored_options.sort(key=lambda x: x[1]["score"], reverse=True)
                        top_options = scored_options[:settings.max_recommendations]
                        
                        logger.info(f"🏆 Top {len(top_options)} options for {ticker.symbol}:")
                        for i, (option, score_data) in enumerate(top_options):
                            logger.info(f"   {i+1}. {option.symbol} {option.strike} - Score: {score_data['score']:.3f}")
                        
                        # Create recommendation for top option
                        logger.info(f"📝 Creating recommendation for {ticker.symbol}...")
                        recommendation = await self._create_recommendation(
                            db, ticker, top_options[0][0]  # Get the option from the tuple
                        )
                        
                        if recommendation:
                            recommendations.append(recommendation)
                            logger.info(f"✅ Created recommendation for {ticker.symbol} with score {recommendation.score:.3f}")
                        else:
                            logger.warning(f"❌ Failed to create recommendation for {ticker.symbol}")
                    else:
                        logger.info(f"❌ No options passed scoring for {ticker.symbol}")
                        skipped_count += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Error processing {ticker.symbol}: {e}")
                    import traceback
                    logger.error(f"📋 Traceback: {traceback.format_exc()}")
                    continue
            
            # Step 4: Summary
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("=" * 80)
            logger.info("📊 RECOMMENDATION GENERATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"⏱️  Total duration: {duration:.2f} seconds")
            logger.info(f"📈 Tickers processed: {processed_count}")
            logger.info(f"⏭️  Tickers skipped: {skipped_count}")
            logger.info(f"❌ Errors encountered: {error_count}")
            logger.info(f"✅ Recommendations created: {len(recommendations)}")
            logger.info(f"📊 Success rate: {(len(recommendations) / max(processed_count, 1)) * 100:.1f}%")
            
            if recommendations:
                logger.info("🏆 Top recommendations:")
                for i, rec in enumerate(recommendations[:5]):
                    logger.info(f"   {i+1}. {rec.symbol} - Score: {rec.score:.3f}")
            
            logger.info("=" * 80)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return []
    
    async def _get_universe(self, db: AsyncSession, fast_mode: bool = True) -> List[InterestingTicker]:
        """Get universe of tickers to analyze using sophisticated filtering."""
        logger.info(f"🔍 Getting universe of tickers (fast_mode={fast_mode})...")
        
        try:
            universe_service = UniverseService(db)
            logger.info("📊 Using UniverseService for sophisticated filtering...")
            
            tickers = await universe_service.get_filtered_universe(fast_mode=fast_mode)
            logger.info(f"📊 UniverseService returned {len(tickers)} tickers")
            
            # Apply sector diversification if we have enough tickers
            if len(tickers) > settings.max_tickers_per_cycle:
                logger.info(f"🔄 Applying sector diversification (reducing from {len(tickers)} to {settings.max_tickers_per_cycle})...")
                tickers = universe_service.optimize_for_diversification(
                    tickers, settings.max_tickers_per_cycle
                )
                logger.info(f"✅ Diversification complete, {len(tickers)} tickers remaining")
            
            # Log sector distribution
            sector_dist = universe_service.get_sector_diversification(tickers)
            logger.info(f"📊 Final universe sector distribution: {sector_dist}")
            
            return tickers
            
        except Exception as e:
            logger.error(f"❌ Error in universe selection: {e}")
            logger.info("🔄 Falling back to basic selection...")
            
            # Fallback to basic selection
            result = await db.execute(
                select(InterestingTicker).where(InterestingTicker.active == True)
                .order_by(InterestingTicker.symbol)
                .limit(settings.max_tickers_per_cycle)
            )
            fallback_tickers = result.scalars().all()
            logger.info(f"📊 Fallback selection returned {len(fallback_tickers)} tickers")
            return fallback_tickers
    
    async def _get_current_positions(self, db: AsyncSession) -> List[str]:
        """Get symbols of current positions."""
        logger.info("🔍 Getting current positions...")
        
        try:
            result = await db.execute(
                select(Position).where(Position.status == "open")
            )
            positions = result.scalars().all()
            
            position_symbols = [pos.symbol for pos in positions]
            logger.info(f"📊 Found {len(position_symbols)} current positions: {position_symbols}")
            
            return position_symbols
        except Exception as e:
            logger.warning(f"⚠️  Could not query positions table: {e}")
            logger.info("📊 Returning empty positions list")
            # Return empty list if table doesn't exist
            return []
    
    async def _get_options_for_ticker(self, db: AsyncSession, ticker: InterestingTicker) -> List[Option]:
        """Get suitable put options for a ticker."""
        logger.info(f"🔍 Getting options for {ticker.symbol}...")
        
        # Step 1: Get current market data
        logger.info(f"📊 Step 1: Syncing market data for {ticker.symbol}...")
        try:
            tradier_data = TradierDataManager(db)
            await tradier_data.sync_ticker_data(ticker.symbol)
            logger.info(f"✅ Market data synced for {ticker.symbol}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to sync data for {ticker.symbol}: {e}")
            return []
        
        # Step 2: Check if we have options data in the database
        logger.info(f"🔍 Step 2: Checking database for existing options...")
        result = await db.execute(
            select(Option).where(
                and_(
                    Option.symbol == ticker.symbol,
                    Option.option_type == "put"
                )
            )
        )
        options = result.scalars().all()
        logger.info(f"📊 Found {len(options)} options in database for {ticker.symbol}")
        
        # Step 3: If no options in database, try to fetch from Tradier API
        if not options:
            logger.info(f"🔄 No options found in database for {ticker.symbol}, fetching from Tradier API...")
            try:
                # Get available expirations
                logger.info(f"📅 Getting available expirations for {ticker.symbol}...")
                expirations = await tradier_data.client.get_option_expirations(ticker.symbol)
                if expirations:
                    # Use the nearest expiration
                    expiration = expirations[0]
                    logger.info(f"📅 Using expiration {expiration} for {ticker.symbol}")
                    
                    # Fetch options data
                    logger.info(f"📊 Fetching options data for {ticker.symbol}...")
                    options = await tradier_data.sync_options_data(ticker.symbol, expiration)
                    logger.info(f"✅ Fetched {len(options)} options for {ticker.symbol}")
                else:
                    logger.warning(f"⚠️  No expirations available for {ticker.symbol}")
            except Exception as e:
                logger.error(f"❌ Failed to fetch options from Tradier API for {ticker.symbol}: {e}")
                return []
        
        # Step 4: Filter and log options details
        if options:
            logger.info(f"📊 Options summary for {ticker.symbol}:")
            for i, option in enumerate(options[:5]):  # Show first 5 options
                logger.info(f"   {i+1}. Strike: ${option.strike}, Expiry: {option.expiry}, DTE: {option.dte}")
                logger.info(f"      Delta: {option.delta:.3f}, IV: {option.implied_volatility:.1f}%, OI: {option.open_interest}")
        
        return options
    
    async def _create_recommendation(
        self, 
        db: AsyncSession, 
        ticker: InterestingTicker, 
        option: Option
    ) -> Optional[Recommendation]:
        """Create a recommendation for an option."""
        logger.info(f"📝 Creating recommendation for {ticker.symbol}...")
        
        try:
            # Step 1: Calculate score using the scoring engine
            logger.info(f"🎯 Step 1: Calculating score for {ticker.symbol}...")
            scoring_engine = ScoringEngine(db)
            
            # Get current price from quote data
            quote_result = await db.execute(
                select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
            )
            quote = quote_result.scalar_one_or_none()
            current_price = quote.current_price if quote else 0
            
            if current_price == 0:
                logger.warning(f"⚠️  No current price found for {ticker.symbol}, cannot create recommendation")
                return None
            
            logger.info(f"📊 Current price for {ticker.symbol}: ${current_price}")
            
            score_data = scoring_engine.score_option(option, current_price)
            score = score_data["score"]
            
            logger.info(f"🎯 Calculated score for {ticker.symbol}: {score:.3f}")
            logger.info(f"📊 Score breakdown: {score_data.get('rationale', {})}")
            
            if score < 0.5:  # Minimum score threshold
                logger.info(f"❌ Score {score:.3f} below minimum threshold (0.5) for {ticker.symbol}")
                return None
            
            # Step 2: Get OpenAI analysis if enabled
            analysis = None
            if settings.openai_enabled:
                logger.info(f"🤖 Step 2: Getting OpenAI analysis for {ticker.symbol}...")
                try:
                    cache_manager = OpenAICacheManager(db)
                    analysis = await cache_manager.get_or_create_analysis(
                        ticker.symbol, 
                        current_price
                    )
                    logger.info(f"✅ OpenAI analysis completed for {ticker.symbol}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to get OpenAI analysis for {ticker.symbol}: {e}")
            else:
                logger.info(f"🤖 OpenAI analysis disabled, skipping for {ticker.symbol}")
            
            # Step 3: Create rationale using the score data
            logger.info(f"📝 Step 3: Creating rationale for {ticker.symbol}...")
            rationale = score_data["rationale"]
            rationale.update({
                "dte": option.dte,
                "delta": option.delta,
                "iv_rank": option.iv_rank,
                "open_interest": option.open_interest,
                "volume": option.volume,
                "qualitative_score": analysis.qualitative_score if analysis else 0.5
            })
            
            logger.info(f"📊 Final rationale for {ticker.symbol}: {rationale}")
            
            # Step 4: Create recommendation
            logger.info(f"💾 Step 4: Saving recommendation to database for {ticker.symbol}...")
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
            
            logger.info(f"✅ Successfully created recommendation for {ticker.symbol} with score {score:.3f}")
            return recommendation
            
        except Exception as e:
            logger.error(f"❌ Error creating recommendation for {ticker.symbol}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
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
