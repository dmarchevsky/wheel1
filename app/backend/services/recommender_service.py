from utils.timezone import pacific_now
"""Recommendation service for generating and managing trade recommendations."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, select

from config import settings as env_settings
from services.settings_service import get_setting
from db.models import Recommendation, InterestingTicker, TickerQuote, Option, Position
from core.scoring import ScoringEngine
from clients.openai_client import OpenAICacheManager
from clients.tradier import TradierDataManager
from services.universe_service import UniverseService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RecommenderService:
    """Service for generating trade recommendations."""
    
    def __init__(self):
        # Services will be initialized with db when needed
        pass
    
    async def generate_recommendations(self, db: AsyncSession, progress_callback=None) -> List[Recommendation]:
        """Generate new recommendations with optimized processing."""
        start_time = pacific_now()
        logger.info("🚀 Starting recommendation generation...")

        
        try:
            # Step 1: Get universe of tickers
            logger.info("🔍 Step 1: Getting universe of tickers...")
            if progress_callback:
                progress_callback({
                    "message": "Getting list of tickers to process...",
                    "current_ticker": None,
                    "total_tickers": 0,
                    "processed_tickers": 0,
                    "recommendations_generated": 0
                })
            
            tickers = await self._get_universe(db)
            if not tickers:
                logger.warning("❌ No tickers found in universe")
                return []
            
            logger.info(f"✅ Found {len(tickers)} tickers in universe")
            
            # Debug: Log first few tickers
            ticker_symbols = [t.symbol for t in tickers[:5]]
            logger.info(f"📊 First 5 tickers in universe: {ticker_symbols}")
            
            # Step 2: Refresh ticker quotes to ensure current prices are available
            logger.info("🔍 Step 2: Refreshing ticker quotes...")
            await self._refresh_ticker_quotes(db, tickers)
            logger.info("✅ Ticker quotes refreshed")
            
            # Step 3: Get current positions to avoid duplicates
            logger.info("🔍 Step 3: Getting current positions...")
            current_positions = await self._get_current_positions(db)
            logger.info(f"📊 Current positions: {current_positions}")
            
            # Step 4: Pre-filter tickers (remove those with existing positions)
            logger.info("🔍 Step 4: Pre-filtering tickers...")
            if progress_callback:
                progress_callback({
                    "message": "Filtering tickers...",
                    "total_tickers": len(tickers),
                    "processed_tickers": 0,
                    "recommendations_generated": 0
                })
            
            filtered_tickers = [ticker for ticker in tickers if ticker.symbol not in current_positions]
            logger.info(f"📊 Filtered to {len(filtered_tickers)} tickers (removed {len(tickers) - len(filtered_tickers)} with existing positions)")
            
            if not filtered_tickers:
                logger.info("❌ No tickers available after filtering")
                return []
            
            # Update progress with final ticker count
            if progress_callback:
                progress_callback({
                    "message": f"Processing {len(filtered_tickers)} tickers...",
                    "total_tickers": len(filtered_tickers),
                    "processed_tickers": 0,
                    "recommendations_generated": 0
                })
            
            # Step 5: Process tickers with optimized approach
            logger.info("🔍 Step 5: Processing tickers...")
            recommendations = []
            processed_count = 0
            skipped_count = 0
            error_count = 0
            
            # Process all tickers
            max_tickers_to_process = len(filtered_tickers)
            
            for i, ticker in enumerate(filtered_tickers[:max_tickers_to_process]):
                processed_count += 1
                logger.info(f"📈 Processing ticker {processed_count}/{min(len(filtered_tickers), max_tickers_to_process)}: {ticker.symbol}")
                
                # Update progress for current ticker
                if progress_callback:
                    progress_callback({
                        "message": f"Processing {ticker.symbol} ({processed_count}/{len(filtered_tickers)})",
                        "current_ticker": ticker.symbol,
                        "total_tickers": len(filtered_tickers),
                        "processed_tickers": processed_count,
                        "recommendations_generated": len(recommendations)
                    })
                
                try:
                    # Get options data (optimized with caching)
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
                    
                    for j, option in enumerate(options):
                        logger.info(f"   📊 Scoring option {j+1}/{len(options)}: {option.symbol} {option.strike} {option.expiry}")
                        
                        # Get current price for scoring
                        quote_result = await db.execute(
                            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                        )
                        quote = quote_result.scalar_one_or_none()
                        current_price = quote.current_price if quote else 0
                        
                        if current_price == 0:
                            logger.warning(f"⚠️  No current price found for {ticker.symbol}, skipping option scoring")
                            continue
                        
                        score_data = await scoring_engine.score_option(option, current_price)
                        score = score_data["score"]
                        
                        logger.info(f"   🎯 Option score: {score:.3f}")
                        
                        if score > 0:
                            scored_options.append((option, score_data))
                            logger.info(f"   ✅ Option passed minimum score threshold")
                        else:
                            logger.info(f"   ❌ Option failed minimum score threshold")
                    
                    logger.info(f"📊 Scored {len(scored_options)} options for {ticker.symbol}")
                    
                    # Sort by score and take top recommendations
                    if scored_options:
                        scored_options.sort(key=lambda x: x[1]["score"], reverse=True)
                        top_options = scored_options[:1]  # Just take the top option
                        
                        logger.info(f"🏆 Top option for {ticker.symbol}:")
                        for k, (option, score_data) in enumerate(top_options):
                            logger.info(f"   {k+1}. {option.symbol} {option.strike} - Score: {score_data['score']:.3f}")
                        
                        # Create recommendation for top option
                        logger.info(f"📝 Creating recommendation for {ticker.symbol}...")
                        recommendation = await self._create_recommendation(
                            db, ticker, top_options[0][0]  # Get the option from the tuple
                        )
                        
                        if recommendation:
                            recommendations.append(recommendation)
                            logger.info(f"✅ Created recommendation for {ticker.symbol} with score {recommendation.score:.3f}")
                            
                            # Update progress when recommendation is created
                            if progress_callback:
                                progress_callback({
                                    "message": f"Created recommendation for {ticker.symbol} ({processed_count}/{len(filtered_tickers)})",
                                    "current_ticker": ticker.symbol,
                                    "total_tickers": len(filtered_tickers),
                                    "processed_tickers": processed_count,
                                    "recommendations_generated": len(recommendations)
                                })
                            
                            # Continue processing all tickers
                            pass
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
            
            # Step 6: Summary
            end_time = pacific_now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("=" * 80)
            logger.info("📊 RECOMMENDATION GENERATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"⏱️  Total duration: {duration:.2f} seconds")
            logger.info(f"📈 Tickers processed: {processed_count}")
            logger.info(f"⏭️  Tickers skipped: {skipped_count}")
            logger.info(f"❌ Errors encountered: {error_count}")
            logger.info(f"🎯 Recommendations created: {len(recommendations)}")
            logger.info(f"⚡ Average time per ticker: {duration/processed_count:.2f}s" if processed_count > 0 else "N/A")
            logger.info("=" * 80)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error in recommendation generation: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return []
    


    async def _get_universe(self, db: AsyncSession, fast_mode: bool = False) -> List[InterestingTicker]:
        """Get universe of tickers to analyze using top universe score filtering."""
        logger.info("🔍 Getting universe of tickers...")
        
        try:
            # Get the top universe score setting
            top_universe_score = await get_setting(db, "top_universe_score", 50)
            logger.info(f"📊 Using top {top_universe_score} tickers by universe score")
            
            # First, let's check how many active tickers we have
            result = await db.execute(
                select(InterestingTicker).where(InterestingTicker.active == True)
            )
            all_active_tickers = result.scalars().all()
            logger.info(f"📊 Total active tickers in database: {len(all_active_tickers)}")
            
            # Get top tickers by universe score
            result = await db.execute(
                select(InterestingTicker).where(
                    and_(
                        InterestingTicker.active == True,
                        InterestingTicker.universe_score.isnot(None)
                    )
                ).order_by(InterestingTicker.universe_score.desc())
                .limit(top_universe_score)
            )
            top_scored_tickers = result.scalars().all()
            logger.info(f"📊 Found {len(top_scored_tickers)} tickers with universe scores")
            
            # Apply price filter to universe
            max_ticker_price = await get_setting(db, "max_ticker_price", 500.0)
            logger.info(f"📊 Applying price filter: max ticker price (current + 5%) <= ${max_ticker_price}")
            
            price_filtered_tickers = []
            for ticker in top_scored_tickers:
                try:
                    # Get current price from TickerQuote
                    quote_result = await db.execute(
                        select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                    )
                    quote = quote_result.scalar_one_or_none()
                    if quote and quote.current_price:
                        # Apply 5% buffer as specified in requirements
                        price_with_buffer = quote.current_price * 1.05
                        if price_with_buffer <= max_ticker_price:
                            price_filtered_tickers.append(ticker)
                            logger.debug(f"✅ {ticker.symbol}: ${quote.current_price} (${price_with_buffer:.2f} with buffer) <= ${max_ticker_price}")
                        else:
                            logger.debug(f"❌ {ticker.symbol}: ${quote.current_price} (${price_with_buffer:.2f} with buffer) > ${max_ticker_price}")
                    else:
                        # If no current price available, skip this ticker
                        logger.debug(f"⚠️  {ticker.symbol}: No current price available, skipping")
                        continue
                except Exception as e:
                    logger.warning(f"⚠️  Error checking price for {ticker.symbol}: {e}")
                    continue
            
            logger.info(f"📊 Price filter: {len(price_filtered_tickers)}/{len(top_scored_tickers)} tickers passed (removed {len(top_scored_tickers) - len(price_filtered_tickers)} above price limit)")
            top_scored_tickers = price_filtered_tickers
            
            if len(top_scored_tickers) >= 10:  # If we have enough scored tickers
                tickers = top_scored_tickers
                logger.info(f"✅ Using top {len(tickers)} tickers by universe score")
                
                # Log score distribution
                if tickers:
                    scores = [t.universe_score for t in tickers if t.universe_score is not None]
                    if scores:
                        max_score = max(scores)
                        min_score = min(scores)
                        avg_score = sum(scores) / len(scores)
                        logger.info(f"📊 Score range: {min_score:.3f} - {max_score:.3f}, avg: {avg_score:.3f}")
            else:
                logger.warning(f"⚠️  Only {len(top_scored_tickers)} tickers have universe scores! Falling back to UniverseService...")
                # Fallback to UniverseService for sophisticated filtering
                universe_service = UniverseService(db)
                tickers = await universe_service.get_filtered_universe()
                logger.info(f"📊 UniverseService returned {len(tickers)} tickers")
                
                # Apply price filter to UniverseService results
                max_ticker_price = await get_setting(db, "max_ticker_price", 500.0)
                price_filtered_tickers = []
                for ticker in tickers:
                    try:
                        quote_result = await db.execute(
                            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                        )
                        quote = quote_result.scalar_one_or_none()
                        if quote and quote.current_price:
                            price_with_buffer = quote.current_price * 1.05
                            if price_with_buffer <= max_ticker_price:
                                price_filtered_tickers.append(ticker)
                        else:
                            continue
                    except Exception as e:
                        logger.warning(f"⚠️  Error checking price for {ticker.symbol}: {e}")
                        continue
                
                tickers = price_filtered_tickers
                logger.info(f"📊 Applied price filter to UniverseService results: {len(tickers)} tickers remaining")
                
                if len(tickers) == 0:
                    logger.warning("⚠️  UniverseService returned 0 tickers after price filtering! Falling back to basic selection...")
                    # Final fallback to basic selection
                    result = await db.execute(
                        select(InterestingTicker).where(InterestingTicker.active == True)
                        .order_by(InterestingTicker.symbol)
                        .limit(top_universe_score)
                    )
                    fallback_tickers = result.scalars().all()
                    
                    # Apply price filter to fallback selection too
                    price_filtered_fallback = []
                    for ticker in fallback_tickers:
                        try:
                            quote_result = await db.execute(
                                select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                            )
                            quote = quote_result.scalar_one_or_none()
                            if quote and quote.current_price:
                                price_with_buffer = quote.current_price * 1.05
                                if price_with_buffer <= max_ticker_price:
                                    price_filtered_fallback.append(ticker)
                            else:
                                continue
                        except Exception as e:
                            logger.warning(f"⚠️  Error checking price for {ticker.symbol}: {e}")
                            continue
                    
                    tickers = price_filtered_fallback
                    logger.info(f"📊 Fallback selection returned {len(tickers)} tickers after price filtering")
            
            # Log sector distribution for final universe
            if tickers:
                sector_counts = {}
                for ticker in tickers:
                    sector = ticker.sector or "Unknown"
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
                logger.info(f"📊 Final universe sector distribution: {sector_counts}")
            
            return tickers
            
        except Exception as e:
            logger.error(f"❌ Error in universe selection: {e}")
            logger.info("🔄 Falling back to basic selection...")
            
            try:
                # Get the top universe score setting for fallback
                top_universe_score = await get_setting(db, "top_universe_score", 50)
                
                # Fallback to basic selection with score limit
                result = await db.execute(
                    select(InterestingTicker).where(InterestingTicker.active == True)
                    .order_by(InterestingTicker.symbol)
                    .limit(top_universe_score)
                )
                fallback_tickers = result.scalars().all()
                
                # Apply price filter even in exception fallback
                max_ticker_price = await get_setting(db, "max_ticker_price", 500.0)
                price_filtered_fallback = []
                for ticker in fallback_tickers:
                    try:
                        quote_result = await db.execute(
                            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                        )
                        quote = quote_result.scalar_one_or_none()
                        if quote and quote.current_price:
                            price_with_buffer = quote.current_price * 1.05
                            if price_with_buffer <= max_ticker_price:
                                price_filtered_fallback.append(ticker)
                        else:
                            continue
                    except Exception as price_error:
                        logger.warning(f"⚠️  Error checking price for {ticker.symbol}: {price_error}")
                        continue
                
                logger.info(f"📊 Exception fallback selection returned {len(price_filtered_fallback)} tickers after price filtering")
                return price_filtered_fallback
            except Exception as fallback_error:
                logger.error(f"❌ Error in fallback selection: {fallback_error}")
                return []
    
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
        """Get suitable put options for a ticker with optimized caching."""
        logger.info(f"🔍 Getting options for {ticker.symbol}...")
        
        # Step 1: Check if we have recent options data in the database first
        logger.info(f"🔍 Step 1: Checking database for existing options...")
        # Get volume and OI thresholds
        min_volume = await get_setting(db, "min_volume", 200)
        min_oi = await get_setting(db, "min_oi", 500)
        
        result = await db.execute(
            select(Option).where(
                and_(
                    Option.symbol == ticker.symbol,
                    Option.option_type == "put",
                    Option.updated_at >= pacific_now() - timedelta(hours=1),  # Only use data from last hour
                    # DTE filter: use unified DTE settings
                    Option.dte >= await get_setting(db, "dte_min", 21),
                    Option.dte <= await get_setting(db, "dte_max", 35),
                    # Delta filter: use database settings (absolute value for puts)
                    Option.delta >= -await get_setting(db, "put_delta_max", 0.35),  # Negative for puts
                    Option.delta <= -await get_setting(db, "put_delta_min", 0.25),   # Negative for puts
                    # Volume and OI filters - apply at database level for efficiency
                    Option.volume.isnot(None),
                    Option.volume >= min_volume,
                    Option.open_interest.isnot(None),
                    Option.open_interest >= min_oi
                )
            )
        )
        options = result.scalars().all()
        logger.info(f"📊 Found {len(options)} recent options in database for {ticker.symbol} (filtered by DTE, delta, volume≥{min_volume}, OI≥{min_oi})")
        
        # Step 2: If no recent options, sync market data and fetch from API
        if not options:
            logger.info(f"🔄 No recent options found for {ticker.symbol}, fetching fresh data...")
            try:
                tradier_data = TradierDataManager(db)
                
                # Sync market data (this is usually fast)
                logger.info(f"📊 Syncing market data for {ticker.symbol}...")
                await tradier_data.sync_ticker_data(ticker.symbol)
                
                # Get optimal expiration (21-35 days)
                logger.info(f"📅 Getting optimal expiration for {ticker.symbol}...")
                expiration = await tradier_data.get_optimal_expiration(ticker.symbol)
                if expiration:
                    logger.info(f"📅 Using optimal expiration {expiration} for {ticker.symbol}")
                    
                    # Fetch options data
                    logger.info(f"📊 Fetching options data for {ticker.symbol}...")
                    options = await tradier_data.sync_options_data(ticker.symbol, expiration)
                    logger.info(f"✅ Fetched {len(options)} options for {ticker.symbol}")
                else:
                    logger.warning(f"⚠️  No optimal expiration available for {ticker.symbol}")
            except Exception as e:
                logger.error(f"❌ Failed to fetch options for {ticker.symbol}: {e}")
                return []
        
        # Step 3: Filter and log options details (only if we have options)
        if options:
            logger.info(f"📊 Options summary for {ticker.symbol}:")
            for i, option in enumerate(options[:3]):  # Show first 3 options to reduce log noise
                logger.info(f"   {i+1}. Strike: ${option.strike}, Expiry: {option.expiry}, DTE: {option.dte}")
                delta_str = f"{option.delta:.3f}" if option.delta is not None else "N/A"
                iv_str = f"{option.implied_volatility:.1f}%" if option.implied_volatility is not None else "N/A"
                logger.info(f"      Delta: {delta_str}, IV: {iv_str}, OI: {option.open_interest}")
        
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
            
            score_data = await scoring_engine.score_option(option, current_price)
            score = score_data["score"]
            
            logger.info(f"🎯 Calculated score for {ticker.symbol}: {score:.3f}")
            logger.info(f"📊 Score breakdown: {score_data.get('rationale', {})}")
            
            # Get minimum score threshold from settings
            min_score_threshold = await get_setting(db, "min_score_threshold", 0.5)
            
            if score < min_score_threshold:
                logger.info(f"❌ Score {score:.3f} below minimum threshold ({min_score_threshold}) for {ticker.symbol}")
                return None
            
            # Step 2: Get OpenAI analysis if enabled
            analysis = None
            if env_settings.openai_enabled:
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
                "delta": option.delta,
                "iv_rank": option.iv_rank,
                "open_interest": option.open_interest,
                "volume": option.volume,
                "qualitative_score": analysis.qualitative_score if analysis else 0.5,
                "probability_of_profit_black_scholes": rationale.get("probability_of_profit_black_scholes"),
                "probability_of_profit_monte_carlo": rationale.get("probability_of_profit_monte_carlo")
            })
            
            logger.info(f"📊 Final rationale for {ticker.symbol}: {rationale}")
            
            # Step 4: Create recommendation
            logger.info(f"💾 Step 4: Saving recommendation to database for {ticker.symbol}...")
            recommendation = Recommendation(
                symbol=ticker.symbol,
                option_symbol=option.symbol,  # References options.symbol
                score=score,
                rationale_json=rationale,  # Keep for backward compatibility
                # Populate expanded fields
                annualized_yield=rationale.get("annualized_yield"),
                proximity_score=rationale.get("proximity_score"),
                liquidity_score=rationale.get("liquidity_score"),
                risk_adjustment=rationale.get("risk_adjustment"),
                qualitative_score=rationale.get("qualitative_score"),
                dte=(option.expiry - pacific_now()).days,  # Calculate DTE directly
                spread_pct=rationale.get("spread_pct"),
                mid_price=rationale.get("mid_price"),
                delta=option.delta,  # Use option delta directly
                iv_rank=option.iv_rank,  # Use option iv_rank directly
                open_interest=option.open_interest,  # Use option data directly
                volume=option.volume,  # Use option volume directly
                probability_of_profit_black_scholes=rationale.get("probability_of_profit_black_scholes"),
                probability_of_profit_monte_carlo=rationale.get("probability_of_profit_monte_carlo"),
                option_side=option.option_type,  # Set option_side from the option's type
                status="proposed",
                created_at=pacific_now()
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
    
    async def _refresh_ticker_quotes(self, db: AsyncSession, tickers: List[InterestingTicker]) -> None:
        """Refresh ticker quotes to ensure current prices are available for scoring."""
        logger.info(f"🔄 Refreshing ticker quotes for {len(tickers)} tickers...")
        
        try:
            from clients.tradier import TradierDataManager
            
            # Initialize Tradier client
            tradier_client = TradierDataManager(db)
            
            # Get current prices for all tickers
            for ticker in tickers:
                try:
                    logger.info(f"📊 Getting current price for {ticker.symbol}...")
                    
                    # Get quote data from Tradier
                    quote_data = await tradier_client.client.get_quote(ticker.symbol)
                    
                    if quote_data and quote_data.get("last"):
                        # Check if quote exists
                        quote_result = await db.execute(
                            select(TickerQuote).where(TickerQuote.symbol == ticker.symbol)
                        )
                        quote = quote_result.scalar_one_or_none()
                        
                        current_price = float(quote_data["last"])
                        volume = int(quote_data.get("volume", 0)) if quote_data.get("volume") else None
                        
                        if not quote:
                            # Create new quote
                            quote = TickerQuote(
                                symbol=ticker.symbol,
                                current_price=current_price,
                                volume_avg_20d=volume,
                                volatility_30d=None,  # Will be calculated later if needed
                                updated_at=pacific_now()
                            )
                            db.add(quote)
                            logger.info(f"✅ Created new quote for {ticker.symbol}: ${current_price}")
                        else:
                            # Update existing quote
                            quote.current_price = current_price
                            quote.volume_avg_20d = volume
                            quote.updated_at = pacific_now()
                            logger.info(f"✅ Updated quote for {ticker.symbol}: ${current_price}")
                    else:
                        logger.warning(f"⚠️  No price data available for {ticker.symbol}")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Error getting price for {ticker.symbol}: {e}")
                    continue
            
            # Commit all changes
            await db.commit()
            logger.info(f"✅ Successfully refreshed ticker quotes for {len(tickers)} tickers")
                
        except Exception as e:
            logger.error(f"❌ Error refreshing ticker quotes: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            await db.rollback()
    
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
            recommendation.updated_at = pacific_now()
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error dismissing recommendation {recommendation_id}: {e}")
            await db.rollback()
            return False
    
    async def generate_recommendations_for_ticker(self, db: AsyncSession, symbol: str) -> List[Recommendation]:
        """Generate recommendations for a specific ticker."""
        try:
            logger.info(f"🎯 Generating recommendations for specific ticker: {symbol}")
            
            # Get the ticker from the universe
            ticker_result = await db.execute(
                select(InterestingTicker).where(InterestingTicker.symbol == symbol.upper())
            )
            ticker = ticker_result.scalar_one_or_none()
            
            if not ticker:
                logger.warning(f"❌ Ticker {symbol} not found in universe")
                return []
            
            # Check if ticker already has active recommendations
            existing_recommendations = await db.execute(
                select(Recommendation).where(
                    and_(
                        Recommendation.symbol == symbol.upper(),
                        Recommendation.status == "proposed"
                    )
                )
            )
            existing = existing_recommendations.scalars().all()
            
            if existing:
                logger.info(f"📊 Ticker {symbol} already has {len(existing)} active recommendations")
                return existing
            
            # Refresh ticker quote to ensure current price is available
            await self._refresh_ticker_quotes(db, [ticker])
            
            # Get current positions to avoid duplicates
            current_positions = await self._get_current_positions(db)
            if symbol.upper() in current_positions:
                logger.info(f"📊 Ticker {symbol} already has an active position, skipping")
                return []
            
            # Get options for the ticker
            options = await self._get_options_for_ticker(db, ticker)
            if not options:
                logger.warning(f"⚠️  No options found for {symbol}")
                return []
            
            # Generate recommendations using the existing scoring logic
            recommendations = []
            scoring_engine = ScoringEngine()
            
            for option in options:
                try:
                    # Get current price for scoring
                    quote_result = await db.execute(
                        select(TickerQuote).where(TickerQuote.symbol == option.underlying_ticker)
                    )
                    quote = quote_result.scalar_one_or_none()
                    current_price = quote.current_price if quote else 0
                    
                    if current_price == 0:
                        logger.warning(f"⚠️  No current price found for {option.underlying_ticker}, skipping option")
                        continue
                    
                    # Score the option
                    score_result = await scoring_engine.score_option(option, current_price)
                    
                    if score_result and score_result.get("score", 0) > 0:
                        # Create recommendation
                        recommendation = Recommendation(
                            symbol=option.symbol,
                            underlying_ticker=option.underlying_ticker,
                            option_symbol=option.option_symbol,
                            option_type=option.option_type,
                            strike=option.strike,
                            expiry=option.expiry,
                            dte=option.dte,
                            contract_price=option.price,
                            current_price=option.underlying_price,
                            volume=option.volume,
                            open_interest=option.open_interest,
                            put_call_ratio=option.put_call_ratio,
                            score=score_result["score"],
                            rationale_json=score_result.get("rationale", {}),
                            status="proposed",
                            created_at=pacific_now()
                        )
                        
                        # Add expanded fields if available
                        if "annualized_yield" in score_result:
                            recommendation.annualized_yield = score_result["annualized_yield"]
                        if "proximity_score" in score_result:
                            recommendation.proximity_score = score_result["proximity_score"]
                        if "liquidity_score" in score_result:
                            recommendation.liquidity_score = score_result["liquidity_score"]
                        if "risk_adjustment" in score_result:
                            recommendation.risk_adjustment = score_result["risk_adjustment"]
                        if "qualitative_score" in score_result:
                            recommendation.qualitative_score = score_result["qualitative_score"]
                        
                        db.add(recommendation)
                        recommendations.append(recommendation)
                        
                except Exception as e:
                    logger.warning(f"⚠️  Error scoring option {option.option_symbol}: {e}")
                    continue
            
            if recommendations:
                await db.commit()
                logger.info(f"✅ Generated {len(recommendations)} recommendations for {symbol}")
            else:
                logger.info(f"📊 No recommendations generated for {symbol} (no options met criteria)")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendations for {symbol}: {e}")
            await db.rollback()
            return []
    
    async def cleanup_old_recommendations(self, db: AsyncSession, days: int = 7) -> int:
        """Clean up old recommendations."""
        try:
            cutoff_date = pacific_now() - timedelta(days=days)
            
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
