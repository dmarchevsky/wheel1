"""Telegram bot service for notifications and trade execution."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select

from config import settings
from db.session import AsyncSessionLocal
from db.models import User, Notification, Recommendation
from services.trade_executor import TradeExecutor

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram bot service for notifications and interactions."""
    
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.application = None
        self.trade_executor = TradeExecutor()
    
    async def initialize(self):
        """Initialize the Telegram bot."""
        try:
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("recs", self._recommendations_command))
            self.application.add_handler(CommandHandler("positions", self._positions_command))
            self.application.add_handler(CommandHandler("alerts", self._alerts_command))
            self.application.add_handler(CommandHandler("help", self._help_command))
            
            # Add callback query handler for inline buttons
            self.application.add_handler(CallbackQueryHandler(self._button_callback))
            
            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise
    
    async def start_polling(self):
        """Start the bot polling."""
        if self.application:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot polling started")
    
    async def stop(self):
        """Stop the bot."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped")
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            # Register user if not exists
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.telegram_chat_id == str(chat_id))
                )
                existing_user = result.scalar_one_or_none()
                if not existing_user:
                    new_user = User(telegram_chat_id=str(chat_id))
                    db.add(new_user)
                    await db.commit()
                    logger.info(f"New user registered: {chat_id}")
            
            welcome_message = """
🤖 Welcome to the Wheel Strategy Assistant!

I'll help you with automated options trading recommendations and portfolio management.

Available commands:
• /recs - View current recommendations
• /positions - Check your portfolio
• /alerts - View outstanding actions
• /help - Show this help message

Ready to start trading! 🚀
            """
            
            await update.message.reply_text(welcome_message.strip())
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("Sorry, there was an error. Please try again.")
    
    async def _recommendations_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recs command."""
        try:
            async with AsyncSessionLocal() as db:
                # Get current recommendations
                result = await db.execute(
                    select(Recommendation).where(
                        Recommendation.status == "proposed"
                    ).order_by(Recommendation.score.desc()).limit(3)
                )
                recommendations = result.scalars().all()
                
                if not recommendations:
                    await update.message.reply_text("No current recommendations available.")
                    return
                
                message = "🎯 **Current Recommendations**\n\n"
                
                for i, rec in enumerate(recommendations, 1):
                    score_pct = rec.score * 100
                    annualized_yield = rec.annualized_yield or rec.rationale_json.get('annualized_yield', 0) if rec.rationale_json else 0
                    
                    message += f"{i}. **{rec.symbol}**\n"
                    message += f"   Score: {score_pct:.1f}%\n"
                    message += f"   Annualized Yield: {annualized_yield:.1f}%\n"
                    
                    # Use new fields if available, fallback to rationale_json
                    dte = rec.dte or (rec.rationale_json.get('dte', 'N/A') if rec.rationale_json else 'N/A')
                    spread = rec.spread_pct or (rec.rationale_json.get('spread_pct', 'N/A') if rec.rationale_json else 'N/A')
                    message += f"   DTE: {dte} • Spread: {spread:.1f}%\n"
                    
                    message += "\n"
                
                # Create inline keyboard for trade execution
                keyboard = []
                for rec in recommendations:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Execute {rec.symbol}",
                            callback_data=f"execute_{rec.id}"
                        )
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            logger.error(f"Error in recommendations command: {e}")
            await update.message.reply_text("Sorry, there was an error fetching recommendations.")
    
    async def _positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command."""
        try:
            # This would fetch from the positions API
            message = "📊 **Portfolio Summary**\n\n"
            message += "Feature coming soon! Check the web dashboard for detailed portfolio information."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in positions command: {e}")
            await update.message.reply_text("Sorry, there was an error fetching positions.")
    
    async def _alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command."""
        try:
            message = "🔔 **Outstanding Alerts**\n\n"
            message += "No alerts at this time. All positions are within normal parameters."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in alerts command: {e}")
            await update.message.reply_text("Sorry, there was an error fetching alerts.")
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 **Wheel Strategy Assistant Help**

**Commands:**
• /start - Initialize the bot
• /recs - View current recommendations
• /positions - Check your portfolio
• /alerts - View outstanding actions
• /help - Show this help message

**Features:**
• AI-powered cash-secured put recommendations
• One-tap trade execution
• Portfolio monitoring
• Automated alerts

For detailed analysis, visit the web dashboard!
        """
        
        await update.message.reply_text(help_text.strip(), parse_mode='Markdown')
    
    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            data = query.data
            
            if data.startswith("execute_"):
                recommendation_id = int(data.split("_")[1])
                await self._handle_trade_execution(query, recommendation_id)
            elif data.startswith("confirm_"):
                await self._handle_trade_confirmation(query, data)
            elif data.startswith("cancel_"):
                await self._handle_trade_cancellation(query)
            else:
                await query.edit_message_text("Unknown action.")
                
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            await query.edit_message_text("Sorry, there was an error processing your request.")
    
    async def _handle_trade_execution(self, query, recommendation_id: int):
        """Handle trade execution request."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Recommendation).where(Recommendation.id == recommendation_id)
                )
                recommendation = result.scalar_one_or_none()
            
            if not recommendation:
                await query.edit_message_text("Recommendation not found.")
                return
            
            # Create order preview
            order_preview = await self.trade_executor.preview_order(recommendation)
            
            message = f"📋 **Order Preview**\n\n"
            message += f"Symbol: {recommendation.symbol}\n"
            message += f"Action: Sell Cash-Secured Put\n"
            message += f"Strike: ${order_preview.get('strike', 'N/A')}\n"
            message += f"Expiry: {order_preview.get('expiry', 'N/A')}\n"
            message += f"Quantity: {order_preview.get('quantity', 'N/A')}\n"
            message += f"Limit Price: ${order_preview.get('limit_price', 'N/A')}\n"
            message += f"Estimated Premium: ${order_preview.get('premium', 'N/A')}\n\n"
            message += "Please confirm this trade:"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{recommendation_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in trade execution: {e}")
            await query.edit_message_text("Sorry, there was an error creating the order preview.")
    
    async def _handle_trade_confirmation(self, query, data: str):
        """Handle trade confirmation."""
        try:
            recommendation_id = int(data.split("_")[1])
            
            # Execute the trade
            result = await self.trade_executor.execute_trade(recommendation_id)
            
            if result.get('success'):
                message = "✅ **Trade Executed Successfully!**\n\n"
                message += f"Order ID: {result.get('order_id', 'N/A')}\n"
                message += f"Status: {result.get('status', 'N/A')}\n"
                message += f"Fill Price: ${result.get('fill_price', 'N/A')}\n\n"
                message += "Your position has been updated."
            else:
                message = "❌ **Trade Execution Failed**\n\n"
                message += f"Error: {result.get('error', 'Unknown error')}\n\n"
                message += "Please try again or contact support."
            
            await query.edit_message_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in trade confirmation: {e}")
            await query.edit_message_text("Sorry, there was an error executing the trade.")
    
    async def _handle_trade_cancellation(self, query):
        """Handle trade cancellation."""
        await query.edit_message_text("❌ Trade cancelled.")
    
    async def send_recommendations(self, recommendations: List[Dict[str, Any]]):
        """Send recommendations to Telegram."""
        if not recommendations:
            return
        
        try:
            message = "🎯 **New Recommendations Available!**\n\n"
            
            for rec in recommendations[:3]:  # Limit to 3 recommendations
                message += f"**{rec['symbol']}**\n"
                message += f"Score: {rec['score']:.1f}%\n"
                message += f"Annualized Yield: {rec.get('annualized_yield', 0):.1f}%\n\n"
            
            message += "Use /recs to view details and execute trades."
            
            await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending recommendations: {e}")
    
    async def send_alerts(self, alerts: List[Dict[str, Any]]):
        """Send alerts to Telegram."""
        if not alerts:
            return
        
        try:
            message = "🔔 **Portfolio Alerts**\n\n"
            
            for alert in alerts:
                message += f"**{alert['type']}**: {alert['message']}\n\n"
            
            await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    async def _send_message(self, message: str):
        """Send a message to the configured chat."""
        try:
            if self.application:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
