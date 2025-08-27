"""Background worker for scheduled jobs and Telegram bot."""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from config import settings, validate_required_settings
from db.session import SyncSessionLocal, create_tables
from core.scheduler import market_calendar, job_scheduler
from services.recommender_service import RecommenderService
from services.position_service import PositionService
from services.alert_service import AlertService
from services.telegram_service import TelegramService
from services.trade_executor import TradeExecutor
from services.market_data_service import MarketDataService


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Worker:
    """Background worker for scheduled jobs and Telegram bot."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.telegram_service = TelegramService()
        self.recommender_service = RecommenderService()
        self.position_service = PositionService()
        self.alert_service = AlertService()
        self.trade_executor = TradeExecutor()
        self.market_data_service = None  # Will be initialized with DB session
        self.running = False
        self.recommendation_generation_lock = asyncio.Lock()  # Prevent concurrent recommendation generation
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.stop()
    
    async def start(self):
        """Start the worker."""
        logger.info("Starting Wheel Strategy Worker...")
        
        try:
            # Validate settings
            validate_required_settings()
            
            # Create database tables
            create_tables()
            
            # Initialize services
            await self.telegram_service.initialize()
            logger.info("Telegram service initialized")
            
            # Start scheduler
            self.scheduler.start()
            logger.info("Scheduler started")
            
            # Schedule jobs
            await self._schedule_jobs()
            
            # Start Telegram bot polling
            await self.telegram_service.start_polling()
            
            self.running = True
            logger.info("Worker started successfully")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start worker: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the worker."""
        logger.info("Stopping worker...")
        
        try:
            # Stop Telegram bot
            await self.telegram_service.stop()
            
            # Stop scheduler
            if self.scheduler.running:
                self.scheduler.shutdown()
            
            logger.info("Worker stopped")
            
        except Exception as e:
            logger.error(f"Error stopping worker: {e}")
    
    async def trigger_manual_recommendation_generation(self):
        """Trigger manual recommendation generation (called from API)."""
        # Use lock to prevent concurrent recommendation generation
        if self.recommendation_generation_lock.locked():
            logger.info("Recommendation generation already in progress, manual request queued")
            return False, "Recommendation generation already in progress"
            
        async with self.recommendation_generation_lock:
            try:
                logger.info("Running manual recommendation generation...")
                
                # Get database session
                db = SyncSessionLocal()
                try:
                    # Generate recommendations (ignore market hours for manual requests)
                    recommendations = await self.recommender_service.generate_recommendations(db)
                    
                    if recommendations:
                        logger.info(f"Generated {len(recommendations)} recommendations manually")
                        
                        # Send Telegram notifications
                        await self.telegram_service.send_recommendations(recommendations)
                        return True, f"Generated {len(recommendations)} recommendations"
                    else:
                        logger.info("No recommendations generated manually")
                        return True, "No recommendations generated"
                        
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Error in manual recommendation generation: {e}")
                return False, f"Error generating recommendations: {str(e)}"
    
    async def _schedule_jobs(self):
        """Schedule background jobs."""
        # Recommender job - runs every 15 minutes during market hours
        self.scheduler.add_job(
            self._run_recommender_job,
            trigger=IntervalTrigger(minutes=15),
            id="recommender_job",
            name="Generate recommendations",
            coalesce=True,
            max_instances=1,
            timezone=market_calendar.timezone,
            misfire_grace_time=300  # 5 minutes grace time
        )
        
        # Position sync job - runs every 5 minutes during market hours
        self.scheduler.add_job(
            self._run_position_sync_job,
            trigger=IntervalTrigger(minutes=5),
            id="position_sync_job",
            name="Sync positions",
            coalesce=True,
            max_instances=1,
            timezone=market_calendar.timezone
        )
        
        # Alert check job - runs every 10 minutes
        self.scheduler.add_job(
            self._run_alert_check_job,
            trigger=IntervalTrigger(minutes=10),
            id="alert_check_job",
            name="Check alerts",
            coalesce=True,
            max_instances=1,
            timezone=market_calendar.timezone
        )
        
        # Cache cleanup job - runs daily
        self.scheduler.add_job(
            self._run_cache_cleanup_job,
            trigger=IntervalTrigger(days=1),
            id="cache_cleanup_job",
            name="Cleanup cache",
            coalesce=True,
            max_instances=1
        )
        
        # S&P 500 universe update job - runs daily at 6 AM ET
        self.scheduler.add_job(
            self._run_sp500_universe_update_job,
            trigger=IntervalTrigger(days=1),
            id="sp500_universe_update_job",
            name="Update S&P 500 universe",
            coalesce=True,
            max_instances=1,
            timezone=market_calendar.timezone
        )
        
        # Market data refresh job - runs every 2 hours during market hours
        self.scheduler.add_job(
            self._run_market_data_refresh_job,
            trigger=IntervalTrigger(hours=2),
            id="market_data_refresh_job",
            name="Refresh market data",
            coalesce=True,
            max_instances=1,
            timezone=market_calendar.timezone
        )
        
        # Weekly SP500 fundamentals and earnings population job - runs every Friday at 5 PM ET (aftermarket)
        self.scheduler.add_job(
            self._run_weekly_sp500_population_job,
            trigger="cron",
            day_of_week="fri",
            hour=17,
            minute=0,
            id="weekly_sp500_population_job",
            name="Weekly SP500 fundamentals and earnings population",
            coalesce=True,
            max_instances=1,
            timezone=market_calendar.timezone
        )
        
        logger.info("Jobs scheduled successfully")
    
    async def _run_recommender_job(self):
        """Run the recommender job."""
        # Use lock to prevent concurrent recommendation generation
        if self.recommendation_generation_lock.locked():
            logger.info("Recommendation generation already in progress, skipping scheduled job")
            return
            
        async with self.recommendation_generation_lock:
            try:
                # Check if market is open
                if not market_calendar.should_run_recommender():
                    logger.debug("Market closed, skipping recommender job")
                    return
                
                logger.info("Running scheduled recommender job...")
                
                # Get database session
                db = SyncSessionLocal()
                try:
                    # Generate recommendations
                    recommendations = await self.recommender_service.generate_recommendations(db)
                    
                    if recommendations:
                        logger.info(f"Generated {len(recommendations)} recommendations")
                        
                        # Send Telegram notifications
                        await self.telegram_service.send_recommendations(recommendations)
                    else:
                        logger.info("No recommendations generated")
                        
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Error in recommender job: {e}")
    
    async def _run_position_sync_job(self):
        """Run the position sync job."""
        try:
            # Check if market is open
            if not market_calendar.is_market_open():
                logger.debug("Market closed, skipping position sync job")
                return
            
            logger.info("Running position sync job...")
            
            # Get database session
            db = SyncSessionLocal()
            try:
                # Sync positions
                await self.position_service.sync_positions(db)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in position sync job: {e}")
    
    async def _run_alert_check_job(self):
        """Run the alert check job."""
        try:
            logger.debug("Running alert check job...")
            
            # Get database session
            db = SyncSessionLocal()
            try:
                # Check for alerts
                alerts = await self.alert_service.check_alerts(db)
                
                if alerts:
                    logger.info(f"Found {len(alerts)} alerts")
                    
                    # Send Telegram notifications
                    await self.telegram_service.send_alerts(alerts)
                else:
                    logger.debug("No alerts found")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in alert check job: {e}")
    
    async def _run_cache_cleanup_job(self):
        """Run the cache cleanup job."""
        try:
            logger.info("Running cache cleanup job...")
            
            # Get database session
            db = SyncSessionLocal()
            try:
                # Cleanup expired cache entries
                from clients.openai_client import OpenAICacheManager
                cache_manager = OpenAICacheManager(db)
                cleaned_count = cache_manager.cleanup_expired_cache()
                
                logger.info(f"Cleaned up {cleaned_count} expired cache entries")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in cache cleanup job: {e}")
    
    async def _run_sp500_universe_update_job(self):
        """Run the S&P 500 universe update job."""
        try:
            logger.info("Running S&P 500 universe update job...")
            
            # Get database session
            db = SyncSessionLocal()
            try:
                # Initialize market data service
                market_data_service = MarketDataService(db)
                
                # Update S&P 500 universe
                updated_tickers = await market_data_service.update_sp500_universe()
                
                if updated_tickers:
                    logger.info(f"Successfully updated {len(updated_tickers)} S&P 500 tickers")
                    
                    # Send Telegram notification
                    await self.telegram_service.send_message(
                        f"🔄 S&P 500 Universe Updated\n"
                        f"✅ Updated {len(updated_tickers)} tickers\n"
                        f"📊 Active tickers: {len(updated_tickers)}"
                    )
                else:
                    logger.warning("No tickers updated in S&P 500 universe")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in S&P 500 universe update job: {e}")
    
    async def _run_market_data_refresh_job(self):
        """Run the market data refresh job."""
        try:
            # Check if market is open
            if not market_calendar.is_market_open():
                logger.debug("Market closed, skipping market data refresh job")
                return
            
            logger.info("Running market data refresh job...")
            
            # Get database session
            db = SyncSessionLocal()
            try:
                # Initialize market data service
                market_data_service = MarketDataService(db)
                
                # Refresh market data for active tickers
                refreshed_tickers = await market_data_service.refresh_market_data()
                
                if refreshed_tickers:
                    logger.info(f"Refreshed market data for {len(refreshed_tickers)} tickers")
                else:
                    logger.debug("No tickers needed market data refresh")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in market data refresh job: {e}")
    
    async def _run_weekly_sp500_population_job(self):
        """Run the weekly SP500 fundamentals and earnings population job."""
        try:
            logger.info("Running weekly SP500 fundamentals and earnings population job...")
            
            # Get database session
            db = SyncSessionLocal()
            try:
                # Initialize market data service
                market_data_service = MarketDataService(db)
                
                # Populate SP500 fundamentals and earnings
                result = await market_data_service.populate_sp500_fundamentals_and_earnings()
                
                if result["success"]:
                    logger.info(f"✅ Weekly SP500 population completed successfully")
                    logger.info(f"📊 Results: {result['successful_updates']}/{result['total_processed']} successful updates ({result['success_rate']:.1f}%)")
                    
                    # Send Telegram notification with results
                    message = (
                        f"🔄 **Weekly SP500 Population Complete**\n\n"
                        f"✅ **Success Rate**: {result['success_rate']:.1f}%\n"
                        f"📊 **Updated**: {result['successful_updates']}/{result['total_processed']} tickers\n"
                        f"⏰ **Timestamp**: {result['timestamp']}\n\n"
                        f"**Top 10 Successful Updates:**\n"
                    )
                    
                    # Add top 10 successful tickers
                    for i, ticker in enumerate(result['successful_tickers'][:10], 1):
                        message += f"{i}. {ticker}\n"
                    
                    if len(result['successful_tickers']) > 10:
                        message += f"... and {len(result['successful_tickers']) - 10} more\n"
                    
                    await self.telegram_service.send_message(message)
                    
                else:
                    logger.error(f"❌ Weekly SP500 population failed: {result.get('error', 'Unknown error')}")
                    
                    # Send error notification
                    error_message = (
                        f"❌ **Weekly SP500 Population Failed**\n\n"
                        f"**Error**: {result.get('error', 'Unknown error')}\n"
                        f"**Timestamp**: {result['timestamp']}"
                    )
                    await self.telegram_service.send_message(error_message)
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in weekly SP500 population job: {e}")
            
            # Send error notification
            try:
                error_message = (
                    f"❌ **Weekly SP500 Population Job Error**\n\n"
                    f"**Error**: {str(e)}\n"
                    f"**Timestamp**: {datetime.utcnow().isoformat()}"
                )
                await self.telegram_service.send_message(error_message)
            except Exception as notify_error:
                logger.error(f"Failed to send error notification: {notify_error}")


async def main():
    """Main entry point for the worker."""
    worker = Worker()
    await worker.start()


# Global worker instance for API access
_worker_instance = None

def get_worker_instance():
    """Get the global worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = Worker()
    return _worker_instance

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
