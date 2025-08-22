"""Market calendar and scheduler logic."""

import pytz
from datetime import datetime, timedelta
from typing import Optional, List
import pandas_market_calendars as mcal


class MarketCalendar:
    """Market calendar for US equity markets."""
    
    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = pytz.timezone(timezone)
        self.calendar = mcal.get_calendar('NYSE')
    
    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """Check if market is currently open."""
        if dt is None:
            dt = datetime.now(self.timezone)
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        
        return self.calendar.is_open(dt)
    
    def is_market_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is during market hours (9:30 AM - 4:00 PM ET)."""
        if dt is None:
            dt = datetime.now(self.timezone)
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        
        # Check if it's a trading day
        if not self.calendar.is_open(dt):
            return False
        
        # Check if it's during market hours (9:30 AM - 4:00 PM ET)
        market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = dt.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= dt <= market_close
    
    def get_next_market_open(self, dt: Optional[datetime] = None) -> datetime:
        """Get the next market open time."""
        if dt is None:
            dt = datetime.now(self.timezone)
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        
        # Get next trading day
        next_trading_day = self.calendar.next_trading_day(dt)
        
        # Market opens at 9:30 AM ET
        market_open = next_trading_day.replace(hour=9, minute=30, second=0, microsecond=0)
        return market_open
    
    def get_next_market_close(self, dt: Optional[datetime] = None) -> datetime:
        """Get the next market close time."""
        if dt is None:
            dt = datetime.now(self.timezone)
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        
        if self.is_market_open(dt):
            # Market closes at 4:00 PM ET today
            market_close = dt.replace(hour=16, minute=0, second=0, microsecond=0)
            if dt < market_close:
                return market_close
        
        # Get next trading day close
        next_trading_day = self.calendar.next_trading_day(dt)
        market_close = next_trading_day.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_close
    
    def get_trading_days(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Get list of trading days between start and end dates."""
        if start_date.tzinfo is None:
            start_date = self.timezone.localize(start_date)
        if end_date.tzinfo is None:
            end_date = self.timezone.localize(end_date)
        
        schedule = self.calendar.schedule(start_date=start_date, end_date=end_date)
        return schedule.index.tolist()
    
    def get_days_to_expiry(self, expiry_date: datetime) -> int:
        """Get number of trading days to expiry."""
        now = datetime.now(self.timezone)
        if expiry_date.tzinfo is None:
            expiry_date = self.timezone.localize(expiry_date)
        
        trading_days = self.get_trading_days(now, expiry_date)
        return len(trading_days)
    
    def should_run_recommender(self, dt: Optional[datetime] = None) -> bool:
        """Check if recommender should run based on market conditions."""
        if dt is None:
            dt = datetime.now(self.timezone)
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        
        # Only run during market hours
        if not self.is_market_hours(dt):
            return False
        
        # Check if it's a trading day
        if not self.is_market_open(dt):
            return False
        
        return True
    
    def get_next_recommender_run(self, dt: Optional[datetime] = None) -> datetime:
        """Get the next time the recommender should run."""
        if dt is None:
            dt = datetime.now(self.timezone)
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        
        # If market is closed, wait for next market open
        if not self.is_market_open(dt):
            return self.get_next_market_open(dt)
        
        # If outside market hours, wait for market open
        if not self.is_market_hours(dt):
            market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
            if dt.date() == market_open.date():
                return market_open
            else:
                return self.get_next_market_open(dt)
        
        # During market hours, run every 15 minutes
        # Round down to nearest 15-minute interval
        minutes = dt.minute - (dt.minute % 15)
        next_run = dt.replace(minute=minutes, second=0, microsecond=0)
        
        # If we're past this interval, move to next
        if next_run <= dt:
            next_run += timedelta(minutes=15)
        
        return next_run


class JobScheduler:
    """Job scheduler for market-aware task execution."""
    
    def __init__(self, market_calendar: MarketCalendar):
        self.market_calendar = market_calendar
    
    def get_recommender_schedule(self) -> dict:
        """Get schedule configuration for recommender job."""
        return {
            'trigger': 'interval',
            'minutes': 15,
            'timezone': self.market_calendar.timezone,
            'coalesce': True,
            'max_instances': 1
        }
    
    def get_position_sync_schedule(self) -> dict:
        """Get schedule configuration for position sync job."""
        return {
            'trigger': 'interval',
            'minutes': 5,
            'timezone': self.market_calendar.timezone,
            'coalesce': True,
            'max_instances': 1
        }
    
    def get_alert_check_schedule(self) -> dict:
        """Get schedule configuration for alert check job."""
        return {
            'trigger': 'interval',
            'minutes': 10,
            'timezone': self.market_calendar.timezone,
            'coalesce': True,
            'max_instances': 1
        }
    
    def should_execute_job(self, job_name: str, dt: Optional[datetime] = None) -> bool:
        """Check if a job should execute based on market conditions."""
        if dt is None:
            dt = datetime.now(self.market_calendar.timezone)
        
        # Different jobs have different execution criteria
        if job_name == "recommender":
            return self.market_calendar.should_run_recommender(dt)
        elif job_name == "position_sync":
            # Position sync can run during market hours or shortly after
            return self.market_calendar.is_market_open(dt)
        elif job_name == "alert_check":
            # Alert check can run anytime
            return True
        else:
            return False
    
    def get_job_execution_time(self, job_name: str, dt: Optional[datetime] = None) -> datetime:
        """Get the next execution time for a job."""
        if dt is None:
            dt = datetime.now(self.market_calendar.timezone)
        
        if job_name == "recommender":
            return self.market_calendar.get_next_recommender_run(dt)
        elif job_name == "position_sync":
            # Run every 5 minutes during market hours
            minutes = dt.minute - (dt.minute % 5)
            next_run = dt.replace(minute=minutes, second=0, microsecond=0)
            if next_run <= dt:
                next_run += timedelta(minutes=5)
            return next_run
        elif job_name == "alert_check":
            # Run every 10 minutes
            minutes = dt.minute - (dt.minute % 10)
            next_run = dt.replace(minute=minutes, second=0, microsecond=0)
            if next_run <= dt:
                next_run += timedelta(minutes=10)
            return next_run
        else:
            return dt + timedelta(minutes=1)


# Global market calendar instance
market_calendar = MarketCalendar()
job_scheduler = JobScheduler(market_calendar)
