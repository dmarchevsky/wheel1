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


class Ticker(Base):
    """Stock ticker information."""
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    options = relationship("Option", back_populates="ticker")
    recommendations = relationship("Recommendation", back_populates="ticker")
    positions = relationship("Position", back_populates="ticker")
    earnings = relationship("EarningsCalendar", back_populates="ticker")


class Option(Base):
    """Options chain data."""
    __tablename__ = "options"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("tickers.symbol"), nullable=False)
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
    open_interest = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker = relationship("Ticker", back_populates="options")
    recommendations = relationship("Recommendation", back_populates="option")
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_symbol_expiry_strike_type', 'symbol', 'expiry', 'strike', 'option_type', unique=True),
    )


class Recommendation(Base):
    """Cash-secured put recommendations."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("tickers.symbol"), nullable=False)
    option_id = Column(Integer, ForeignKey("options.id"), nullable=True)
    rationale_json = Column(JSONB, nullable=True)  # Scoring breakdown
    score = Column(Float, nullable=False)
    status = Column(String, default="proposed")  # proposed, executed, dismissed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticker = relationship("Ticker", back_populates="recommendations")
    option = relationship("Option", back_populates="recommendations")
    trades = relationship("Trade", back_populates="recommendation")


class Position(Base):
    """Equity positions."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("tickers.symbol"), nullable=False)
    shares = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker = relationship("Ticker", back_populates="positions")


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
        Index('idx_symbol_time', 'symbol', 'created_at'),
        Index('idx_status_time', 'status', 'created_at'),
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


class EarningsCalendar(Base):
    """Earnings calendar data."""
    __tablename__ = "earnings_calendar"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("tickers.symbol"), nullable=False)
    earnings_date = Column(DateTime, nullable=False)
    source = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticker = relationship("Ticker", back_populates="earnings")
    
    # Indexes
    __table_args__ = (
        Index('idx_symbol_earnings_date', 'symbol', 'earnings_date'),
    )


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
        Index('idx_type_status', 'type', 'status'),
        Index('idx_symbol_time', 'symbol', 'created_at'),
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
