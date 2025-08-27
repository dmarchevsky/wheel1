"""Database models for the Wheel Strategy application."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class User(Base):
    """User model for Telegram integration."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    notifications = relationship("Notification", back_populates="user")


class Setting(Base):
    """Global application settings."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterestingTicker(Base):
    """Fundamental ticker information - infrequently updated (weekly)."""
    __tablename__ = "interesting_tickers"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    market_cap = Column(Float, nullable=True)  # Market capitalization in billions
    beta = Column(Float, nullable=True)  # Beta vs S&P 500
    pe_ratio = Column(Float, nullable=True)  # P/E ratio
    dividend_yield = Column(Float, nullable=True)  # Dividend yield percentage
    next_earnings_date = Column(DateTime, nullable=True)  # Next upcoming earnings date
    active = Column(Boolean, default=True)  # Whether ticker is active for analysis
    universe_score = Column(Float, nullable=True)  # Composite score for universe selection
    last_analysis_date = Column(DateTime, nullable=True)  # Last time universe score was calculated
    source = Column(String, default="sp500")  # 'sp500', 'manual', etc.
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    quotes = relationship("TickerQuote", back_populates="ticker")
    options = relationship("Option", back_populates="ticker")
    recommendations = relationship("Recommendation", back_populates="ticker")
    positions = relationship("Position", back_populates="ticker")


class TickerQuote(Base):
    """Frequently changing ticker market data - real-time updates."""
    __tablename__ = "ticker_quotes"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    current_price = Column(Float, nullable=True)
    volume_avg_20d = Column(Float, nullable=True)  # 20-day average volume
    volatility_30d = Column(Float, nullable=True)  # 30-day historical volatility
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="quotes")
    
    # Composite unique constraint - one quote per symbol
    __table_args__ = (
        Index('idx_symbol_unique', 'symbol', unique=True),
    )


class Option(Base):
    """Options chain data."""
    __tablename__ = "options"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    expiry = Column(DateTime, nullable=False)
    strike = Column(Float, nullable=False)
    option_type = Column(String, nullable=False)  # 'put' or 'call'
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    last = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    iv_rank = Column(Float, nullable=True)  # Implied volatility rank
    dte = Column(Integer, nullable=True)  # Days to expiration
    open_interest = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="options")
    recommendations = relationship("Recommendation", back_populates="option")
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_symbol_expiry_strike_type', 'symbol', 'expiry', 'strike', 'option_type', unique=True),
    )


class Recommendation(Base):
    """Cash-secured put recommendations."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    option_id = Column(Integer, ForeignKey("options.id"), nullable=True)
    rationale_json = Column(JSONB, nullable=True)  # Scoring breakdown
    score = Column(Float, nullable=False)
    status = Column(String, default="proposed")  # proposed, executed, dismissed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="recommendations")
    option = relationship("Option", back_populates="recommendations")
    trades = relationship("Trade", back_populates="recommendation")


class Position(Base):
    """Equity positions."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    shares = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="positions")


class OptionPosition(Base):
    """Options positions."""
    __tablename__ = "option_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    contract_symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # 'short' or 'long'
    option_type = Column(String, nullable=False)  # 'put' or 'call'
    quantity = Column(Integer, nullable=False)
    strike = Column(Float, nullable=False)
    expiry = Column(DateTime, nullable=False)
    open_price = Column(Float, nullable=False)
    open_time = Column(DateTime, nullable=False)
    status = Column(String, default="open")  # 'open' or 'closed'
    underlying_cost_basis = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    """Trade history."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    symbol = Column(String, nullable=False)
    option_symbol = Column(String, nullable=True)
    side = Column(String, nullable=False)  # 'sell_to_open', 'buy_to_close', etc.
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    order_id = Column(String, nullable=True)  # External order ID from broker
    status = Column(String, default="pending")  # 'pending', 'filled', 'cancelled', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="trades")
    
    # Indexes
    __table_args__ = (
        Index('idx_trades_symbol_time', 'symbol', 'created_at'),
        Index('idx_trades_status_time', 'status', 'created_at'),
    )


class Notification(Base):
    """Telegram notifications."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel = Column(String, default="telegram")  # 'telegram'
    payload_json = Column(JSONB, nullable=False)  # Notification content
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # 'pending', 'sent', 'failed'
    
    # Relationships
    user = relationship("User", back_populates="notifications")





class Telemetry(Base):
    """Application telemetry and audit logs."""
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    event = Column(String, nullable=False)
    meta_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_event_time', 'event', 'created_at'),
    )


class Alert(Base):
    """Alerts for position monitoring."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # 'profit_target', 'time_decay', 'delta_threshold', 'covered_call_opportunity'
    symbol = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSONB, nullable=True)  # Additional alert data
    status = Column(String, default="pending")  # 'pending', 'processed', 'dismissed'
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_alerts_type_status', 'type', 'status'),
        Index('idx_alerts_symbol_time', 'symbol', 'created_at'),
    )


class ChatGPTCache(Base):
    """Cache for ChatGPT responses."""
    __tablename__ = "chatgpt_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    response_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ttl = Column(DateTime, nullable=False)  # Time to live
    
    # Indexes
    __table_args__ = (
        Index('idx_ttl', 'ttl'),
    )
