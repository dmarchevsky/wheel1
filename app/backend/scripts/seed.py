"""Database seeding script."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SyncSessionLocal
from db.models import User, Setting, Ticker, Option, Recommendation, Position, OptionPosition
from config import settings


def seed_database():
    """Seed the database with initial data."""
    db = SyncSessionLocal()
    
    try:
        print("Seeding database...")
        
        # Create default user
        user = User(telegram_chat_id=settings.telegram_chat_id)
        db.add(user)
        print("✓ Created default user")
        
        # Create default settings
        default_settings = [
            ("put_delta_min", str(settings.put_delta_min)),
            ("put_delta_max", str(settings.put_delta_max)),
            ("ivr_min", str(settings.ivr_min)),
            ("ivr_max", str(settings.ivr_max)),
            ("min_oi", str(settings.min_oi)),
            ("min_volume", str(settings.min_volume)),
            ("max_bid_ask_pct", str(settings.max_bid_ask_pct)),
            ("annualized_min_pct", str(settings.annualized_min_pct)),
            ("max_recommendations", str(settings.max_recommendations)),
            ("earnings_blackout_days", str(settings.earnings_blackout_days)),
        ]
        
        for key, value in default_settings:
            setting = Setting(key=key, value=value)
            db.add(setting)
        print("✓ Created default settings")
        
        # Create sample tickers
        sample_tickers = [
            ("AAPL", "Apple Inc.", "Technology"),
            ("MSFT", "Microsoft Corporation", "Technology"),
            ("GOOGL", "Alphabet Inc.", "Technology"),
            ("AMZN", "Amazon.com Inc.", "Consumer Discretionary"),
            ("TSLA", "Tesla Inc.", "Consumer Discretionary"),
            ("NVDA", "NVIDIA Corporation", "Technology"),
            ("META", "Meta Platforms Inc.", "Technology"),
            ("NFLX", "Netflix Inc.", "Communication Services"),
            ("JPM", "JPMorgan Chase & Co.", "Financials"),
            ("JNJ", "Johnson & Johnson", "Healthcare"),
        ]
        
        for symbol, name, sector in sample_tickers:
            ticker = Ticker(symbol=symbol, name=name, sector=sector)
            db.add(ticker)
        print("✓ Created sample tickers")
        
        # Create sample options (for AAPL)
        expiry_date = datetime.utcnow() + timedelta(days=30)
        sample_options = [
            (150.0, 0.25, 0.35, 500, 200, 2.5),
            (155.0, 0.30, 0.40, 750, 300, 2.0),
            (160.0, 0.35, 0.45, 1000, 400, 1.8),
        ]
        
        for strike, bid, ask, oi, volume, spread in sample_options:
            option = Option(
                symbol="AAPL",
                expiry=expiry_date,
                strike=strike,
                option_type="put",
                bid=bid,
                ask=ask,
                open_interest=oi,
                volume=volume,
                implied_volatility=0.25,
                delta=-0.30
            )
            db.add(option)
        print("✓ Created sample options")
        
        # Create sample recommendations
        sample_recommendations = [
            ("AAPL", 0.85, {
                "annualized_yield": 25.5,
                "proximity_score": 0.8,
                "liquidity_score": 0.9,
                "risk_adjustment": 0.95,
                "qualitative_score": 0.85,
                "dte": 30,
                "spread_pct": 2.5,
                "mid_price": 2.5
            }),
            ("MSFT", 0.78, {
                "annualized_yield": 22.3,
                "proximity_score": 0.75,
                "liquidity_score": 0.85,
                "risk_adjustment": 0.90,
                "qualitative_score": 0.80,
                "dte": 28,
                "spread_pct": 3.0,
                "mid_price": 3.2
            }),
            ("GOOGL", 0.72, {
                "annualized_yield": 20.1,
                "proximity_score": 0.70,
                "liquidity_score": 0.80,
                "risk_adjustment": 0.85,
                "qualitative_score": 0.75,
                "dte": 32,
                "spread_pct": 2.8,
                "mid_price": 4.1
            }),
        ]
        
        for symbol, score, rationale in sample_recommendations:
            recommendation = Recommendation(
                symbol=symbol,
                score=score,
                rationale_json=rationale,
                status="proposed"
            )
            db.add(recommendation)
        print("✓ Created sample recommendations")
        
        # Create sample positions
        sample_positions = [
            ("AAPL", 100, 150.50),
            ("MSFT", 50, 320.75),
        ]
        
        for symbol, shares, avg_price in sample_positions:
            position = Position(
                symbol=symbol,
                shares=shares,
                avg_price=avg_price
            )
            db.add(position)
        print("✓ Created sample positions")
        
        # Create sample option positions
        sample_option_positions = [
            ("AAPL", "AAPL240315P150", "short", "put", 1, 150.0, expiry_date, 2.50),
        ]
        
        for symbol, contract_symbol, side, option_type, quantity, strike, expiry, open_price in sample_option_positions:
            option_position = OptionPosition(
                symbol=symbol,
                contract_symbol=contract_symbol,
                side=side,
                option_type=option_type,
                quantity=quantity,
                strike=strike,
                expiry=expiry,
                open_price=open_price,
                open_time=datetime.utcnow() - timedelta(days=5),
                status="open"
            )
            db.add(option_position)
        print("✓ Created sample option positions")
        
        db.commit()
        print("✓ Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
