"""Main application class for the Telegram bot."""

import asyncio
from typing import Optional, List
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .database import db_manager
from .logging import configure_logging, LoggerMixin
from .exceptions import ConfigurationError
from ..handlers import (
    start_handler,
    help_handler,
    menu_handler,
    error_handler,
    message_handler,
    ask_gpt_handler,
    callback_handler,
    # Admin handlers
    grant_access_handler,
    revoke_access_handler,
    list_authorized_channels_handler,
    ban_user_handler,
    unban_user_handler,
    make_admin_handler,
    request_access_handler,
    # Image handlers
    draw_me_handler,
    draw_multiple_handler,
    view_personal_collection_handler,
    view_group_collection_handler,
    image_stats_handler,
    handle_image_callback,
    # Todo handlers
    list_todos_handler,
    add_todo_handler,
    complete_todo_handler,
    remove_todo_handler,
    todo_stats_handler,
    handle_todo_callback,
)
from ..handlers.timezone import (
    set_timezone_handler,
    search_timezone_handler,
    my_time_handler,
    remind_me_handler,
    list_reminders_handler,
    cancel_reminder_handler,
    handle_timezone_callback,
)
from ..handlers.crypto import (
    crypto_price_handler,
    crypto_bet_handler,
    crypto_balance_handler,
    crypto_bets_handler,
    crypto_leaderboard_handler,
    crypto_convert_handler,
    handle_crypto_callback,
)
from ..handlers.mines import (
    mines_calculator_handler,
    mines_compare_handler,
    handle_mines_callback,
)
from ..handlers.b2b import (
    b2b_calculator_handler,
    handle_b2b_callback,
)
from ..handlers.nsfw import (
    random_boobs_handler,
    show_me_handler,
    gimme_handler,
    handle_nsfw_callback,
)
from ..handlers.gambling import (
    casino_handler,
    bet_handler,
    handle_gambling_callback,
)
from ..handlers.voting import (
    create_poll_handler,
    list_polls_handler,
    vote_handler,
    handle_voting_callback,
)
from ..handlers.activity import (
    night_owls_handler,
    most_active_users_handler,
    my_activity_handler,
    handle_activity_callback,
)
from ..handlers.mood import (
    mood_analysis_handler,
    mood_trends_handler,
    handle_mood_callback,
)
from ..handlers.synonyms import (
    add_synonym_handler,
    synonym_of_day_handler,
    search_synonyms_handler,
    synonym_stats_handler,
    handle_synonym_callback,
)
from ..handlers.utilities import (
    mention_all_handler,
    shuffle_users_handler,
    random_user_picker_handler,
    handle_utility_callback,
)
from ..services.openai_service import OpenAIService
from ..services.auth_service import auth_service
from ..services.image_service import image_service
from ..services.todo_service import todo_service
from ..services.timezone_service import timezone_service, TimezoneService
from ..services.crypto_service import crypto_service

# Global bot instance for scheduler access
_bot_instance: Optional["TelegramBotApp"] = None


def get_bot_instance() -> Optional["TelegramBotApp"]:
    """Get the global bot instance."""
    return _bot_instance


class TelegramBotApp(LoggerMixin):
    """Main Telegram bot application."""
    
    def __init__(self) -> None:
        """Initialize the bot application."""
        global _bot_instance
        _bot_instance = self
        
        self.application: Optional[Application] = None
        self.scheduler = AsyncIOScheduler()
        self.openai_service = OpenAIService()
        
        # Validate configuration
        if not settings.telegram_bot_token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN is required")
        if not settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is required")
    
    async def setup(self) -> None:
        """Set up the bot application."""
        self.logger.info("Setting up bot application")
        
        # Configure logging
        configure_logging()
        
        # Initialize database
        await db_manager.create_tables()
        
        # Load authorizations
        await auth_service.load_authorizations()
        
        # Initialize timezone service with scheduler
        global timezone_service
        timezone_service = TimezoneService(self.scheduler)
        
        # Start scheduler
        self.scheduler.start()
        
        # Build application
        self.application = (
            ApplicationBuilder()
            .token(settings.telegram_bot_token)
            .concurrent_updates(True)
            .build()
        )
        
        # Register handlers
        self._register_handlers()
        
        # Set error handler
        self.application.add_error_handler(error_handler)
        
        self.logger.info("Bot application setup complete")
    
    def _register_handlers(self) -> None:
        """Register bot handlers."""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        # Basic command handlers
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        self.application.add_handler(CommandHandler("menu", menu_handler))
        self.application.add_handler(CommandHandler("ask_gpt", ask_gpt_handler))
        self.application.add_handler(CommandHandler("ask", ask_gpt_handler))
        
        # Admin command handlers
        self.application.add_handler(CommandHandler("grant_access", grant_access_handler))
        self.application.add_handler(CommandHandler("revoke_access", revoke_access_handler))
        self.application.add_handler(CommandHandler("list_channels", list_authorized_channels_handler))
        self.application.add_handler(CommandHandler("ban_user", ban_user_handler))
        self.application.add_handler(CommandHandler("unban_user", unban_user_handler))
        self.application.add_handler(CommandHandler("make_admin", make_admin_handler))
        self.application.add_handler(CommandHandler("request_access", request_access_handler))
        
        # Image generation handlers
        self.application.add_handler(CommandHandler("draw_me", draw_me_handler))
        self.application.add_handler(CommandHandler("create", draw_me_handler))  # Alias
        self.application.add_handler(CommandHandler("draw_multiple", draw_multiple_handler))
        self.application.add_handler(CommandHandler("view_personal_collection", view_personal_collection_handler))
        self.application.add_handler(CommandHandler("view_group_collection", view_group_collection_handler))
        self.application.add_handler(CommandHandler("image_stats", image_stats_handler))
        
        # Todo management handlers
        self.application.add_handler(CommandHandler("list_todos", list_todos_handler))
        self.application.add_handler(CommandHandler("todos", list_todos_handler))  # Alias
        self.application.add_handler(CommandHandler("add_todo", add_todo_handler))
        self.application.add_handler(CommandHandler("todo", add_todo_handler))  # Alias
        self.application.add_handler(CommandHandler("complete_todo", complete_todo_handler))
        self.application.add_handler(CommandHandler("done", complete_todo_handler))  # Alias
        self.application.add_handler(CommandHandler("remove_todo", remove_todo_handler))
        self.application.add_handler(CommandHandler("delete_todo", remove_todo_handler))  # Alias
        self.application.add_handler(CommandHandler("todo_stats", todo_stats_handler))
        
        # Timezone and reminder handlers
        self.application.add_handler(CommandHandler("set_timezone", set_timezone_handler))
        self.application.add_handler(CommandHandler("timezone", set_timezone_handler))  # Alias
        self.application.add_handler(CommandHandler("search_timezone", search_timezone_handler))
        self.application.add_handler(CommandHandler("find_timezone", search_timezone_handler))  # Alias
        self.application.add_handler(CommandHandler("my_time", my_time_handler))
        self.application.add_handler(CommandHandler("time", my_time_handler))  # Alias
        self.application.add_handler(CommandHandler("remind_me", remind_me_handler))
        self.application.add_handler(CommandHandler("reminder", remind_me_handler))  # Alias
        self.application.add_handler(CommandHandler("list_reminders", list_reminders_handler))
        self.application.add_handler(CommandHandler("reminders", list_reminders_handler))  # Alias
        self.application.add_handler(CommandHandler("cancel_reminder", cancel_reminder_handler))
        
        # Crypto betting handlers
        self.application.add_handler(CommandHandler("price", crypto_price_handler))
        self.application.add_handler(CommandHandler("crypto", crypto_price_handler))  # Alias
        self.application.add_handler(CommandHandler("bet", crypto_bet_handler))
        self.application.add_handler(CommandHandler("balance", crypto_balance_handler))
        self.application.add_handler(CommandHandler("wallet", crypto_balance_handler))  # Alias
        self.application.add_handler(CommandHandler("bets", crypto_bets_handler))
        self.application.add_handler(CommandHandler("history", crypto_bets_handler))  # Alias
        self.application.add_handler(CommandHandler("leaderboard", crypto_leaderboard_handler))
        self.application.add_handler(CommandHandler("top", crypto_leaderboard_handler))  # Alias
        self.application.add_handler(CommandHandler("convert", crypto_convert_handler))
        self.application.add_handler(CommandHandler("conv", crypto_convert_handler))  # Alias
        
        # Mining calculator handlers
        self.application.add_handler(CommandHandler("mines", mines_calculator_handler))
        self.application.add_handler(CommandHandler("mining", mines_calculator_handler))  # Alias
        self.application.add_handler(CommandHandler("compare", mines_compare_handler))
        self.application.add_handler(CommandHandler("comp", mines_compare_handler))  # Alias
        
        # B2B calculator handlers
        self.application.add_handler(CommandHandler("b2b", b2b_calculator_handler))
        self.application.add_handler(CommandHandler("business", b2b_calculator_handler))  # Alias
        
        # NSFW content handlers
        self.application.add_handler(CommandHandler("random_boobs", random_boobs_handler))
        self.application.add_handler(CommandHandler("show_me", show_me_handler))
        self.application.add_handler(CommandHandler("gimme", gimme_handler))
        
        # Gambling handlers
        self.application.add_handler(CommandHandler("casino", casino_handler))
        self.application.add_handler(CommandHandler("bet", bet_handler))
        
        # Voting handlers
        self.application.add_handler(CommandHandler("poll", create_poll_handler))
        self.application.add_handler(CommandHandler("polls", list_polls_handler))
        self.application.add_handler(CommandHandler("vote", vote_handler))
        
        # Activity tracking handlers
        self.application.add_handler(CommandHandler("night_owls", night_owls_handler))
        self.application.add_handler(CommandHandler("most_active_users", most_active_users_handler))
        self.application.add_handler(CommandHandler("my_activity", my_activity_handler))
        
        # Mood analysis handlers
        self.application.add_handler(CommandHandler("hows", mood_analysis_handler))
        self.application.add_handler(CommandHandler("mood", mood_analysis_handler))  # Alias
        self.application.add_handler(CommandHandler("mood_trends", mood_trends_handler))
        
        # Synonym management handlers
        self.application.add_handler(CommandHandler("add_synonym", add_synonym_handler))
        self.application.add_handler(CommandHandler("synonym_of_day", synonym_of_day_handler))
        self.application.add_handler(CommandHandler("search_synonyms", search_synonyms_handler))
        self.application.add_handler(CommandHandler("synonym_stats", synonym_stats_handler))
        
        # User utility handlers
        self.application.add_handler(CommandHandler("all", mention_all_handler))
        self.application.add_handler(CommandHandler("shuffle_userlist", shuffle_users_handler))
        self.application.add_handler(CommandHandler("random_user", random_user_picker_handler))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
        )
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(handle_image_callback, pattern=r"^(fav_|collect_|group_collect_|stats_|favs_|collection_|group_collection_)"))
        self.application.add_handler(CallbackQueryHandler(handle_todo_callback, pattern=r"^todo_"))
        self.application.add_handler(CallbackQueryHandler(handle_timezone_callback, pattern=r"^timezone_"))
        self.application.add_handler(CallbackQueryHandler(handle_crypto_callback, pattern=r"^(crypto_|bet_|price_|convert_)"))
        self.application.add_handler(CallbackQueryHandler(handle_mines_callback, pattern=r"^mines_"))
        self.application.add_handler(CallbackQueryHandler(handle_b2b_callback, pattern=r"^b2b_"))
        self.application.add_handler(CallbackQueryHandler(handle_nsfw_callback, pattern=r"^(fav_|add_collection_|random_boobs_|gimme_another_)"))
        self.application.add_handler(CallbackQueryHandler(handle_gambling_callback, pattern=r"^(casino_|bet_|dice_|slots_|coin_|lucky_|blackjack_|roulette_)"))
        self.application.add_handler(CallbackQueryHandler(handle_voting_callback, pattern=r"^(vote_|refresh_poll_|close_poll_|results_poll_|show_poll_)"))
        self.application.add_handler(CallbackQueryHandler(handle_activity_callback, pattern=r"^(night_owls|active_users|activity_|user_activity_)"))
        self.application.add_handler(CallbackQueryHandler(handle_mood_callback, pattern=r"^(mood_|hows_)"))
        self.application.add_handler(CallbackQueryHandler(handle_synonym_callback, pattern=r"^(synonym_|search_synonyms|add_synonym_)"))
        self.application.add_handler(CallbackQueryHandler(handle_utility_callback, pattern=r"^(shuffle_|random_user_|mention_all|chat_member_)"))
        self.application.add_handler(CallbackQueryHandler(callback_handler))
        
        self.logger.info("All handlers registered")
    
    async def run_polling(self) -> None:
        """Run the bot with polling."""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        self.logger.info("Starting bot with polling")
        
        try:
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Start polling
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            self.logger.info("Bot is running with polling")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            self.logger.error("Error running bot", error=str(e), exc_info=True)
            raise
        finally:
            await self.shutdown()
    
    async def run_webhook(self, webhook_url: str, port: int = 8443) -> None:
        """Run the bot with webhooks."""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        self.logger.info("Starting bot with webhooks", webhook_url=webhook_url, port=port)
        
        try:
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Start webhook
            await self.application.updater.start_webhook(
                listen="0.0.0.0",
                port=port,
                url_path="/webhook",
                webhook_url=f"{webhook_url}/webhook",
                drop_pending_updates=True,
            )
            
            self.logger.info("Bot is running with webhooks")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            self.logger.error("Error running bot", error=str(e), exc_info=True)
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the bot application."""
        self.logger.info("Shutting down bot application")
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        # Shutdown scheduler
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
        
        # Close database connections
        await db_manager.close()
        
        self.logger.info("Bot application shutdown complete")