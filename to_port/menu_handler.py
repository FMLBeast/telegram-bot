from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config.logging_config import logger
from database import db_conn
from .timezone_handler import ASK_LOCATION

class MenuHandlers:
    """Menu-related handlers for the bot"""
    def __init__(self, bot):
        self.bot = bot

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the bot's main menu"""
        channel_id = update.message.chat_id
        logger.info(f"Showing menu in chat {channel_id}")
        keyboard = [
            [InlineKeyboardButton("Random Tiddies", callback_data=f'random_tiddies_{channel_id}')],
            [InlineKeyboardButton("Tits of the Day", callback_data=f'tits_of_the_day_{channel_id}')],
            [InlineKeyboardButton("Set Personal Favorite Tiddies", callback_data=f'set_personal_favorite_tiddies_{channel_id}')],
            [InlineKeyboardButton("View Personal Collection", callback_data=f'view_personal_collection_{channel_id}')],
            [InlineKeyboardButton("Add to Group Collection", callback_data=f'add_to_group_collection_{channel_id}')],
            [InlineKeyboardButton("View Group Collection", callback_data=f'view_group_collection_{channel_id}')],
            [InlineKeyboardButton("Most Active Users", callback_data=f'most_active_users_{channel_id}')],
            [InlineKeyboardButton("Search Pornstar", callback_data=f'search_pornstar_{channel_id}')],
            [InlineKeyboardButton("Convert Crypto", callback_data=f'convert_crypto_{channel_id}')],
            [InlineKeyboardButton("Calculate B2B", callback_data=f'calculate_b2b_{channel_id}')],
            [InlineKeyboardButton("Draw Me", callback_data=f'draw_me_{channel_id}')],
            [InlineKeyboardButton("Show Variations", callback_data=f'show_variations_{channel_id}')],
            [InlineKeyboardButton("Mines Multi Calculator", callback_data=f'mines_multi_{channel_id}')],
            [InlineKeyboardButton("Vote", callback_data=f'vote_{channel_id}')],
            [InlineKeyboardButton("Check User Mood", callback_data=f'check_user_mood_{channel_id}')],
            [InlineKeyboardButton("🎰 Casino Information", callback_data=f'casino_menu_{channel_id}')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Boob bot says:', reply_markup=reply_markup)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        from .bot_handlers import (
            random_tiddies, tits_of_the_day, synonym_of_the_day,
            view_personal_collection, view_group_collection,
            night_owls_command, most_active_users_command,
            set_reminder, edit_reminder, delete_reminder
        )

        query = update.callback_query
        await query.answer()

        data = query.data.rsplit('_', 1)

        # Add casino menu handling
        if data[0] == 'casino_menu':
            await self.bot.casino_handler.handle_casino_menu(update, context)
            return
        
        # Handle timezone confirmation callbacks
        if data[0].startswith('confirm_timezone'):
            action = data[0].split('_')[-1]
            if action == 'yes':
                timezone_name = data[1]
                location = data[2]

                user_id = query.from_user.id
                with db_conn:
                    db_conn.execute(
                        'INSERT OR REPLACE INTO user_timezones (user_id, username, timezone, location) VALUES (?, ?, ?, ?)',
                        (user_id, query.from_user.username, timezone_name, location)
                    )
                    db_conn.commit()

                await query.message.reply_text(f"Great! I've saved your timezone as {timezone_name} for {location}.")
                logger.info(f"User {query.from_user.username} (ID: {user_id}) confirmed timezone {timezone_name} for location {location}.")
            elif action == 'no':
                await query.message.reply_text("Let's try again. Please tell me your location:")
                return ASK_LOCATION
            return

        # Handle all button actions
        await self._handle_button_action(update, context, data)