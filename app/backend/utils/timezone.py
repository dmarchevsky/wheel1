"""Timezone utilities for Pacific timezone handling."""

import pytz
from datetime import datetime
from typing import Optional
from config import settings

# Pacific timezone
PACIFIC_TZ = pytz.timezone("America/Los_Angeles")


def now_pacific() -> datetime:
    """Get current datetime in Pacific timezone."""
    return datetime.now(PACIFIC_TZ)


def utc_to_pacific(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to Pacific timezone."""
    if utc_dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = pytz.UTC.localize(utc_dt)
    return utc_dt.astimezone(PACIFIC_TZ)


def pacific_to_utc(pacific_dt: datetime) -> datetime:
    """Convert Pacific datetime to UTC."""
    if pacific_dt.tzinfo is None:
        # Assume Pacific if no timezone info
        pacific_dt = PACIFIC_TZ.localize(pacific_dt)
    return pacific_dt.astimezone(pytz.UTC)


def format_pacific_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format datetime in Pacific timezone."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = pytz.UTC.localize(dt)
    pacific_dt = dt.astimezone(PACIFIC_TZ)
    return pacific_dt.strftime(format_str)


def parse_pacific_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse datetime string as Pacific timezone."""
    dt = datetime.strptime(dt_str, format_str)
    return PACIFIC_TZ.localize(dt)


def is_pacific_timezone(dt: datetime) -> bool:
    """Check if datetime is in Pacific timezone."""
    return dt.tzinfo == PACIFIC_TZ


def ensure_pacific_timezone(dt: datetime) -> datetime:
    """Ensure datetime is in Pacific timezone, converting if necessary."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = pytz.UTC.localize(dt)
    
    if dt.tzinfo == PACIFIC_TZ:
        return dt
    
    return dt.astimezone(PACIFIC_TZ)
