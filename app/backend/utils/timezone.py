"""Timezone utilities for the Wheel Strategy application."""

from datetime import datetime
import pytz

def pacific_now():
    """Get current Pacific time."""
    pacific_tz = pytz.timezone("America/Los_Angeles")
    return datetime.now(pacific_tz)

def pacific_tz():
    """Get Pacific timezone object."""
    return pytz.timezone("America/Los_Angeles")
