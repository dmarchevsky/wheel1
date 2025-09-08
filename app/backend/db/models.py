"""Database models for the Wheel Strategy application."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from utils.timezone import pacific_now

Base = declarative_base()


class User(Base):
    """User model for Telegram integration."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    
    # Relationships
    notifications = relationship("Notification", back_populates="user")


class Setting(Base):
    """Global application settings."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=pacific_now, onupdate=pacific_now)


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
    next_earnings_date = Column(DateTime(timezone=True), nullable=True)  # Next upcoming earnings date
    active = Column(Boolean, default=True)  # Whether ticker is active for analysis
    universe_score = Column(Float, nullable=True)  # Composite score for universe selection
    last_analysis_date = Column(DateTime(timezone=True), nullable=True)  # Last time universe score was calculated
    source = Column(String, default="sp500")  # 'sp500', 'manual', etc.
    added_at = Column(DateTime(timezone=True), default=pacific_now)
    updated_at = Column(DateTime(timezone=True), default=pacific_now, onupdate=pacific_now)
    
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
    put_call_ratio = Column(Float, nullable=True)  # Put/Call ratio
    updated_at = Column(DateTime(timezone=True), default=pacific_now, onupdate=pacific_now)
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="quotes")
    
    # Composite unique constraint - one quote per symbol
    __table_args__ = (
        Index('idx_symbol_unique', 'symbol', unique=True),
    )


class Option(Base):
    """Options chain data."""
    __tablename__ = "options"
    
    symbol = Column(String, primary_key=True)  # Tradier API symbol (e.g., VXX190517P00016000)
    underlying_symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    expiry = Column(DateTime(timezone=True), nullable=False)
    strike = Column(Float, nullable=False)
    option_type = Column(String, nullable=False)  # 'put' or 'call'
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    last = Column(Float, nullable=True)
    price = Column(Float, nullable=True)  # Calculated price field
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    iv_rank = Column(Float, nullable=True)  # Implied volatility rank
    dte = Column(Integer, nullable=True)  # Days to expiration
    open_interest = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=pacific_now, onupdate=pacific_now)
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="options", foreign_keys=[underlying_symbol])
    recommendations = relationship("Recommendation", back_populates="option", foreign_keys="[Recommendation.option_symbol]")
    
    # Indexes
    __table_args__ = (
        Index('idx_options_underlying_symbol', 'underlying_symbol'),
        Index('idx_options_expiry', 'expiry'),
        Index('idx_options_strike', 'strike'),
        Index('idx_options_type', 'option_type'),
        Index('idx_options_dte', 'dte'),
        Index('idx_options_delta', 'delta'),
        Index('idx_options_price', 'price'),
        Index('idx_options_underlying_expiry_type', 'underlying_symbol', 'expiry', 'option_type'),
    )


class Recommendation(Base):
    """Cash-secured put recommendations."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    option_symbol = Column(String, ForeignKey("options.symbol"), nullable=True)  # References options.symbol
    rationale_json = Column(JSONB, nullable=True)  # Scoring breakdown (legacy)
    score = Column(Float, nullable=False)
    status = Column(String, default="proposed")  # proposed, executed, dismissed
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    
    # Expanded rationale fields
    annualized_yield = Column(Float, nullable=True)
    proximity_score = Column(Float, nullable=True)
    liquidity_score = Column(Float, nullable=True)
    risk_adjustment = Column(Float, nullable=True)
    qualitative_score = Column(Float, nullable=True)
    dte = Column(Integer, nullable=True)
    spread_pct = Column(Float, nullable=True)
    mid_price = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    iv_rank = Column(Float, nullable=True)
    open_interest = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)
    probability_of_profit_black_scholes = Column(Float, nullable=True)
    probability_of_profit_monte_carlo = Column(Float, nullable=True)
    option_side = Column(String, nullable=True)  # 'put' or 'call' - derived from option.option_type
    
    # Relationships
    ticker = relationship("InterestingTicker", back_populates="recommendations")
    option = relationship("Option", back_populates="recommendations", foreign_keys=[option_symbol])
    trades = relationship("Trade", back_populates="recommendation")


class Position(Base):
    """Equity positions."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("interesting_tickers.symbol"), nullable=False)
    shares = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=pacific_now, onupdate=pacific_now)
    
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
    expiry = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Float, nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="open")  # 'open' or 'closed'
    underlying_cost_basis = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=pacific_now, onupdate=pacific_now)


class Trade(Base):
    """Trade history."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    symbol = Column(String, nullable=False)
    option_symbol = Column(String, nullable=True)
    side = Column(String, nullable=False)  # 'sell_to_open', 'buy_to_close', etc.
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)  # Limit price or 0 for market orders
    order_id = Column(String, nullable=True)  # External order ID from broker
    status = Column(String, default="pending")  # 'pending', 'filled', 'cancelled', 'rejected'
    
    # Extended order details
    order_type = Column(String, nullable=True)  # 'limit', 'market'
    duration = Column(String, nullable=True)  # 'day', 'gtc'
    class_type = Column(String, nullable=True)  # 'equity', 'option'
    filled_quantity = Column(Integer, nullable=True, default=0)  # How much was filled
    avg_fill_price = Column(Float, nullable=True)  # Average price filled at
    remaining_quantity = Column(Integer, nullable=True)  # Remaining unfilled quantity
    
    # Trading environment tracking
    environment = Column(String, nullable=True)  # 'production', 'sandbox'
    
    # Additional metadata from Tradier
    tradier_data = Column(JSONB, nullable=True)  # Store complete Tradier order response
    
    # Strike and expiry for options (denormalized for easier querying)
    strike = Column(Float, nullable=True)  # Strike price for options
    expiry = Column(DateTime(timezone=True), nullable=True)  # Expiry date for options
    option_type = Column(String, nullable=True)  # 'put', 'call'
    
    # Expiration and closing tracking
    expiration_outcome = Column(String, nullable=True)  # 'expired_profitable', 'expired_loss', 'assigned', 'exercised', 'closed_early'
    final_pnl = Column(Float, nullable=True)  # Final P&L when position closed/expired
    closed_at = Column(DateTime(timezone=True), nullable=True)  # When position was closed/expired
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)  # When order was filled
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="trades")
    option_events = relationship("OptionEvent", back_populates="trade")
    
    # Indexes
    __table_args__ = (
        Index('idx_trades_symbol_time', 'symbol', 'created_at'),
        Index('idx_trades_status_time', 'status', 'created_at'),
        Index('idx_trades_order_id', 'order_id'),
        Index('idx_trades_environment', 'environment'),
        Index('idx_trades_expiry', 'expiry'),
    )


class Notification(Base):
    """Telegram notifications."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel = Column(String, default="telegram")  # 'telegram'
    payload_json = Column(JSONB, nullable=False)  # Notification content
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending")  # 'pending', 'sent', 'failed'
    
    # Relationships
    user = relationship("User", back_populates="notifications")





class Telemetry(Base):
    """Application telemetry and audit logs."""
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    event = Column(String, nullable=False)
    meta_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    
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
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
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
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    ttl = Column(DateTime(timezone=True), nullable=False)  # Time to live
    
    # Indexes
    __table_args__ = (
        Index('idx_ttl', 'ttl'),
    )


class PositionSnapshot(Base):
    """Position snapshots for tracking position changes over time."""
    __tablename__ = "position_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    contract_symbol = Column(String, nullable=True)  # For options
    environment = Column(String, nullable=False)  # 'production' or 'sandbox'
    quantity = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    market_value = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    tradier_data = Column(JSONB, nullable=True)  # Complete Tradier position response
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    
    # Indexes
    __table_args__ = (
        Index('idx_position_snapshots_symbol_date', 'symbol', 'snapshot_date'),
        Index('idx_position_snapshots_env_date', 'environment', 'snapshot_date'),
        Index('idx_position_snapshots_contract', 'contract_symbol'),
    )


class OptionEvent(Base):
    """Option lifecycle events (expiration, assignment, exercise, etc.)."""
    __tablename__ = "option_events"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)  # Link to originating trade
    symbol = Column(String, nullable=False)  # Underlying symbol
    contract_symbol = Column(String, nullable=False)  # Option contract symbol
    event_type = Column(String, nullable=False)  # 'expiration', 'assignment', 'exercise', 'early_close'
    event_date = Column(DateTime(timezone=True), nullable=False)
    final_price = Column(Float, nullable=True)
    final_pnl = Column(Float, nullable=True)
    environment = Column(String, nullable=False)
    tradier_data = Column(JSONB, nullable=True)  # Any Tradier API response data
    created_at = Column(DateTime(timezone=True), default=pacific_now)
    
    # Relationships
    trade = relationship("Trade", back_populates="option_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_option_events_trade_id', 'trade_id'),
        Index('idx_option_events_event_date', 'event_date'),
        Index('idx_option_events_symbol_type', 'symbol', 'event_type'),
        Index('idx_option_events_contract', 'contract_symbol'),
    )
