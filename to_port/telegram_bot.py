import openai
import os
import random
import string
import asyncio
import logging
import re
import sys
import time
import traceback
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ConversationHandler, 
    MessageHandler, filters, ContextTypes, ChatMemberHandler, PicklePersistence, 
    PersistenceInput
)
from telegram.request import HTTPXRequest
from telegram.error import (
    Forbidden,
    BadRequest,
    TimedOut,
    ChatMigrated,
    NetworkError,
    TelegramError,
    Conflict,
    EndPointNotFound,
    InvalidToken,
    PassportDecryptionError,
    RetryAfter
)
from telegram.helpers import mention_html
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import SchedulerAlreadyRunningError
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
from contextlib import suppress

# Import your local modules
from boob_bot.query_module import interpret_and_query_database, query_database
from boob_bot.data_handlers import get_airdrops_and_giveaways
from config.logging_config import logger
from database import db_conn, add_authorized_channel, load_authorized_channels
from config import OPENAI_API_KEY, TIDDIES_AND_TITS_BOT_TOKEN
from boob_bot.image_handlers import (
    handle_draw_me_command, handle_draw_multiple_command, handle_edit_image_command, 
    handle_image_variation, WAITING_FOR_IMAGE,
    view_personal_collection, add_to_group_collection, view_group_collection,
    add_to_collection, set_favorite
)
from boob_bot.modules.profile.conversation import create_profile_handler
from boob_bot.modules.profile.timezone import timecheck_command

from boob_bot.timezone_handler import set_timezone_conversation_handler, ASK_LOCATION, CONFIRM_TIMEZONE
from boob_bot.user_module import (
    handle_new_member, handle_chat_member_update, check_timezone_on_message, 
    set_timezone, handle_set_timezone_command, show_times
)
from boob_bot.reminder_module import reminder_conversation_handler, set_reminder, edit_reminder, delete_reminder
from boob_bot.bot_handlers import (
    random_tiddies, tits_of_the_day, synonym_of_the_day, add_synonym, 
    vote_command, handle_vote, help_command, shuffle_the_usernames
)
from boob_bot.bc_handler import process_message_with_gpt
from boob_bot.wen_handlers import wen_coco_handler, wen_rish_handler, wen_tits_handler
from boob_bot.user_activity import night_owls_command, most_active_users_command, top_senders_command
from boob_bot.nsfw import search_pornstar_command, random_movie_command, increment_cunt_counter, fetch_image_command
from boob_bot.mines_calculator import mines_multi_command
from boob_bot.crypto_converter import convert_crypto
from boob_bot.mood_analysis import check_user_mood
from boob_bot.bet_calculations import calculate_bets_command
from boob_bot.relay_handlers import relay_command, join_relay_command, relay_action
from boob_bot.gpt_commands import ask_gpt_command
from boob_bot.todo_list import list_todos, move_priority, add_remark 
from boob_bot.casino_handler import CasinoHandler

# Configure logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

casino_handler = None
USER_ID = 6921082971
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load environment / constants
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
AUTHORIZED_CHANNEL_IDS = load_authorized_channels()

# Instead of starting the scheduler immediately, just declare it:
scheduler = AsyncIOScheduler()


# Error Handler and Utility Functions
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the Telegram Bot."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    try:
        if isinstance(update, Update):
            if update.effective_message:
                chat_id = update.effective_chat.id
                user = update.effective_user.username if update.effective_user else 'Unknown'
                update_str = f"chat_id={chat_id}, user={user}"
            elif update.callback_query:
                chat_id = update.callback_query.message.chat.id
                user = update.callback_query.from_user.username if update.callback_query.from_user else 'Unknown'
                update_str = f"chat_id={chat_id}, user={user}"
            else:
                update_str = "No message or callback query"
        else:
            update_str = "Unknown update type"

        error_type = type(context.error).__name__
        error_msg = str(context.error)
        tb_string = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))

        message = (
            f"An exception occurred:\n"
            f"Update: {update_str}\n"
            f"Error Type: {error_type}\n"
            f"Error Message: {error_msg}\n\n"
            f"Traceback:\n{tb_string}"
        )
        logger.error(message)

        if isinstance(context.error, Forbidden):
            logger.warning(f'Bot lacks permission in {update_str}')
            return

        if isinstance(context.error, BadRequest):
            if "Message is not modified" in error_msg:
                return
            if "Query is too old" in error_msg:
                if isinstance(update, Update) and update.callback_query:
                    await update.callback_query.answer(
                        "This button is no longer valid. Please try the command again.",
                        show_alert=True
                    )
                return

        if isinstance(context.error, (TimedOut, NetworkError)):
            logger.warning(f'{error_type} while handling update: {update_str}')
            return

        if isinstance(context.error, ChatMigrated):
            new_chat_id = context.error.new_chat_id
            logger.info(f"Chat migrated to new chat ID: {new_chat_id} from {update_str}")
            return

        if isinstance(context.error, Conflict):
            logger.warning(f"Conflict error encountered: {error_msg}")
            return

        if isinstance(context.error, EndPointNotFound):
            logger.error(f"Endpoint not found: {error_msg}")
            return

        if isinstance(context.error, InvalidToken):
            logger.critical("Invalid bot token provided.")
            sys.exit(1)

        if isinstance(context.error, PassportDecryptionError):
            logger.error("Failed to decrypt passport data.")
            return

        if isinstance(context.error, RetryAfter):
            retry_after = context.error.retry_after
            logger.warning(f"Flood limit exceeded. Retry after {retry_after} seconds.")
            await asyncio.sleep(retry_after)
            return

        if isinstance(update, Update):
            if update.effective_message:
                await update.effective_message.reply_text("Sorry, an unexpected error occurred.")
            elif update.callback_query:
                await update.callback_query.message.reply_text("Sorry, an unexpected error occurred.")
    except Exception as e:
        logger.error(f"Error in error_handler: {str(e)}")
        logger.error(traceback.format_exc())

def check_environment() -> None:
    """Verify required environment variables and paths."""
    required_vars = {
        'TIDDIES_AND_TITS_BOT_TOKEN': TIDDIES_AND_TITS_BOT_TOKEN,
        'OPENAI_API_KEY': OPENAI_API_KEY,
    }
    
    missing_vars = [v for v, val in required_vars.items() if not val]
    if missing_vars:
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

    required_paths = [
        os.path.join(script_dir, 'media/photos'),
        os.path.join(script_dir, 'media/documents'),
        os.path.join(script_dir, 'media/audio'),
        os.path.join(script_dir, 'media/videos'),
        os.path.join(script_dir, 'bot_persistence'),
        os.path.join(script_dir, 'telegram_media')
    ]
    
    for path in required_paths:
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, '.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            raise RuntimeError(f"Failed to verify path {path}: {str(e)}")

async def check_authorization(update: Update) -> bool:
    """Check if the bot is authorized in the channel."""
    if not update.effective_chat:
        return False
    chat_id = update.effective_chat.id
    if chat_id not in AUTHORIZED_CHANNEL_IDS:
        msg = "You are not authorized to use this bot in this channel."
        if update.message:
            await update.message.reply_text(msg)
        elif update.callback_query:
            await update.callback_query.message.reply_text(msg)
        logger.warning(f"Unauthorized access attempt in chat {chat_id}")
        return False
    return True

def wrap_handler_with_auth(handler_func):
    """Decorator for logging & authorization."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if await check_authorization(update):
                if update.message and update.message.text and update.message.text.startswith('/'):
                    command = update.message.text.split()[0]
                    args = update.message.text.split()[1:]
                    logger.info(f"Command: {command} | Args: {' '.join(args)} | "
                                f"User: {update.effective_user.username if update.effective_user else 'Unknown'}")
                return await handler_func(update, context)
            logger.warning(f"Unauthorized access by {update.effective_user.username if update.effective_user else 'Unknown'}")
        except Exception as e:
            logger.error(f"Error in handler {handler_func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            if update.effective_message:
                await update.effective_message.reply_text("Error while processing your request.")
    return wrapper

async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grant bot access to channels (admin only)."""
    if not update.message or not update.message.from_user:
        return
    if update.message.from_user.id != USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized grant_access attempt by {update.message.from_user.id}")
        return

    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Provide user ID and channel ID to grant access.")
        return

    try:
        user_id, channel_id = map(int, context.args)
    except ValueError:
        await update.message.reply_text("Invalid user/channel ID format.")
        return

    add_authorized_channel(channel_id)
    AUTHORIZED_CHANNEL_IDS.add(channel_id)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"Access granted for channel {channel_id}."
    )
    await update.message.reply_text(f"Access granted for user {user_id} to channel {channel_id}.")

async def save_message_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save incoming messages to DB."""
    if not update.message:
        return
    message = update.message
    media_path = None
    media_type = None
    file_obj = None

    try:
        if message.photo:
            media_type = 'photo'
            file_obj = await message.photo[-1].get_file()
            file_name = f"{int(time.time())}_{message.message_id}.jpg"
            media_path = os.path.join(script_dir, 'media/photos', file_name)
        elif message.document:
            media_type = 'document'
            file_obj = await message.document.get_file()
            file_name = f"{int(time.time())}_{message.message_id}_{message.document.file_name}"
            media_path = os.path.join(script_dir, 'media/documents', file_name)
        elif message.audio:
            media_type = 'audio'
            file_obj = await message.audio.get_file()
            file_name = f"{int(time.time())}_{message.message_id}.mp3"
            media_path = os.path.join(script_dir, 'media/audio', file_name)
        elif message.video:
            media_type = 'video'
            file_obj = await message.video.get_file()
            file_name = f"{int(time.time())}_{message.message_id}.mp4"
            media_path = os.path.join(script_dir, 'media/videos', file_name)

        if file_obj and media_path:
            await file_obj.download_to_drive(media_path)

        chat_id = message.chat.id
        chat_name = message.chat.title or message.chat.username or 'Unknown'
        sender = message.from_user.username if message.from_user else 'Unknown'

        with db_conn.get_connection() as conn:
            conn.execute(
                '''INSERT INTO messages 
                   (user_id, username, chat_id, chat_name, content, media, media_type) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    message.from_user.id if message.from_user else None,
                    sender,
                    chat_id,
                    chat_name,
                    message.text,
                    media_path,
                    media_type
                )
            )

        logger.debug(
            f"Message saved - Chat: {chat_name} ({chat_id}), "
            f"User: {sender}, Type: {media_type or 'text'}, Content: {message.text}"
        )

    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")
        logger.error(traceback.format_exc())
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
                logger.info(f"Cleaned up file after error: {media_path}")
            except Exception as del_e:
                logger.error(f"Error deleting media file {media_path}: {str(del_e)}")

async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user access requests."""
    if not update.message or not update.message.from_user:
        return
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat_id

    msg = f"User @{username} (ID: {user_id}) requests access for channel {chat_id}."
    try:
        await context.bot.send_message(chat_id=USER_ID, text=msg)
        await update.message.reply_text("Access request sent to admin.")
        logger.info(f"Access request from @{username} (ID: {user_id}) for {chat_id}")
    except Exception as e:
        logger.error(f"Error processing access request: {str(e)}")
        await update.message.reply_text("Error processing request. Try again later.")

async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log incoming updates more verbosely."""
    if not update:
        return
    try:
        user = (update.message.from_user if update.message else 
                update.callback_query.from_user if update.callback_query else None)
        chat_name = update.effective_chat.title or update.effective_chat.username or 'Private Chat'

        if update.message and update.message.text and update.message.text.startswith('/'):
            command = update.message.text.split()[0]
            args = update.message.text.split()[1:]
            logger.info(f"Command: {command} | Args: {' '.join(args)} | User: {user.username if user else 'Unknown'} | Chat: {chat_name}")
    except Exception as e:
        logger.error(f"Error in log_update: {str(e)}")

async def add_channel(channel_id: int, channel_name: str = None) -> None:
    """Add or update a channel in the database."""
    try:
        with db_conn.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO channels (id, name, created_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (channel_id, channel_name))
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    logger.info("Received /start command")
    if not update.message:
        return
    user_id = update.message.chat_id
    username = update.message.from_user.username if update.message.from_user else None
    channel_id = update.message.chat_id
    channel_name = update.message.chat.title if update.message.chat else None

    try:
        await add_channel(channel_id, channel_name)
        with db_conn.get_connection() as conn:
            conn.execute('INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)', (user_id, username))

        logger.info(f"New user: {username} (ID: {user_id}) in chat {channel_id}")
        await update.message.reply_text('Welcome! Use /menu to interact.')
    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}")
        await update.message.reply_text("Error during startup. Please try again.")

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu."""
    if not update.message:
        return
    channel_id = update.message.chat_id
    logger.info(f"Showing menu in chat {channel_id}")
    try:
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
    except Exception as e:
        logger.error(f"Error showing menu: {str(e)}")
        await update.message.reply_text("Error displaying menu.")

async def handle_timezone_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, data):
    """Handle timezone confirmation callbacks."""
    query = update.callback_query
    action = data[0].split('_')[-1]
    try:
        if action == 'yes':
            timezone_name = data[1]
            location = data[2]
            user_id = query.from_user.id
            with db_conn.get_connection() as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO user_timezones (user_id, username, timezone, location) VALUES (?, ?, ?, ?)',
                    (user_id, query.from_user.username, timezone_name, location)
                )
            await query.message.reply_text(f"Saved your timezone as {timezone_name} for {location}.")
        elif action == 'no':
            await query.message.reply_text("Let's try again. Please tell me your location:")
            return ASK_LOCATION
    except Exception as e:
        logger.error(f"Error in timezone confirmation: {str(e)}")
        await query.message.reply_text("Error. Please set your timezone again.")
        return ConversationHandler.END

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    if not update.callback_query:
        return
    query = update.callback_query
    try:
        await query.answer()
        data = query.data.rsplit('_', 1)  # e.g. "random_tiddies_12345"
        if data[0] == 'casino_menu':
            await casino_handler.handle_casino_menu(update, context)
            return
        if data[0].startswith('confirm_timezone'):
            await handle_timezone_confirmation(update, context, data)
            return
        if len(data) < 2:
            logger.error(f"Invalid callback data: {query.data}")
            await query.message.reply_text("Error. Please try again.")
            return

        action = data[0]
        channel_id = data[1]
        context.args = []
        logger.debug(f"Button pressed: {action}, channel_id={channel_id}")
        await handle_button_action(update, context, action, channel_id)
    except Exception as e:
        logger.error(f"Error in button handler: {str(e)}")
        try:
            await query.message.reply_text("An error occurred. Please try again.")
        except Exception:
            pass

async def handle_button_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, channel_id: str):
    """Handle various button actions."""
    query = update.callback_query
    action_handlers = {
        'random_tiddies': (random_tiddies, "Exploring randomness..."),
        'tits_of_the_day': (tits_of_the_day, "Today's special!"),
        'synonym_of_the_day': (synonym_of_the_day, None),
        'set_personal_favorite_tiddies': (None, "Send me the image to set as favorite."),
        'view_personal_collection': (view_personal_collection, "Here are your personal favorites."),
        'add_to_group_collection': (None, "Send the image you want to add."),
        'view_group_collection': (view_group_collection, "Here are the group favorites."),
        'night_owls': (night_owls_command, None),
        'most_active_users': (most_active_users_command, None),
        'search_pornstar': (None, "Use /show_me <name>."),
        'convert_crypto': (None, "Use /convert <amount> <symbol>."),
        'calculate_b2b': (None, "Use /b2b <params>."),
        'draw_me': (None, "Use /draw_me <prompt>."),
        'mines_multi': (None, "Use /mines_multi <params>."),
        'vote': (None, "Use /vote <poll question>."),
        'check_user_mood': (None, "Use /hows <username>.")
    }
    try:
        if action in action_handlers:
            handler, message = action_handlers[action]
            if message:
                await query.message.reply_text(message)
            if handler:
                await handler(update, context)
        else:
            logger.warning(f"Unknown button action: {action}")
    except Exception as e:
        logger.error(f"Error in button action '{action}': {str(e)}")
        await query.message.reply_text("An error occurred.")

async def send_mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send MP4 file with error handling."""
    if not update.message:
        return
    try:
        chat_id = update.message.chat_id
        video_path = os.path.join(script_dir, 'telegram_media', 'spit_hawk.mp4')
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return
        async with open(video_path, 'rb') as video_file:
            await context.bot.send_video(chat_id=chat_id, video=video_file, supports_streaming=True)
    except Exception as e:
        logger.error(f"Failed to send MP4: {str(e)}")

KEYWORDS = ['hawk', 'spit', 'hawk tuag', 'thang']
KEYWORDS2 = ['jerk', 'soggybiscuit', 'cookie', 'war']
KEYWORD_PATTERN = r'\b(?:' + '|'.join(re.escape(k) for k in KEYWORDS) + r')\b'
KEYWORD_PATTERN2 = r'\b(?:' + '|'.join(re.escape(k) for k in KEYWORDS2) + r')\b'

async def keyword_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keywords that trigger MP4 response."""
    if not update.message or not update.message.text:
        return
    try:
        text = update.message.text.lower()
        if re.search(KEYWORD_PATTERN, text):
            await send_mp4(update, context)
    except Exception as e:
        logger.error(f"Error in keyword handler: {str(e)}")

async def keyword_handlerwar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keywords that trigger a GIF response."""
    if not update.message or not update.message.text:
        return
    try:
        text = update.message.text.lower()
        if re.search(KEYWORD_PATTERN2, text):
            gif_path = os.path.join(script_dir, 'telegram_media', 'war.gif')
            if not os.path.exists(gif_path):
                logger.error(f"GIF not found: {gif_path}")
                return
            async with open(gif_path, 'rb') as gif_file:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=gif_file)
    except Exception as e:
        logger.error(f"Error in war keyword handler: {str(e)}")

async def airdrops_and_giveaways_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle airdrops/giveaways command."""
    if not update.message:
        return
    logger.info(f"Fetching airdrops/giveaways in chat {update.message.chat_id}")
    try:
        result = get_airdrops_and_giveaways()
        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("No airdrop/giveaway messages found.")
    except Exception as e:
        logger.error(f"Error fetching airdrops: {str(e)}")
        await update.message.reply_text("Error fetching info.")

async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mention all members in the chat."""
    if not update.message:
        return
    chat = update.effective_chat
    logger.info(f"Mentioning all in chat {chat.id}")
    try:
        members = await context.bot.get_chat_administrators(chat.id)
        mentions = [mention_html(m.user.id, m.user.full_name) for m in members]
        message = ' '.join(mentions)
        if context.args:
            message += '\n' + ' '.join(context.args)
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error mentioning members: {str(e)}")
        await update.message.reply_text("Error mentioning members.")

async def query_gpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle GPT query."""
    if not update.message:
        return
    user_query = ' '.join(context.args) if context.args else ''
    if not user_query:
        await update.message.reply_text(
            "Usage: /query <your question>\n"
            "e.g. '/query lvl 23 with 1000000$ wager'"
        )
        return
    logger.info(f"Processing GPT query: {user_query}")
    await update.message.reply_text(f"Interpreting your query: {user_query}...")

    try:
        gpt_response = await process_message_with_gpt(user_query)
        formatted_response = gpt_response.replace("[", "").replace("]", "").replace("\\", "")
        await update.message.reply_text(formatted_response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error processing GPT: {str(e)}")
        await update.message.reply_text(f"Error: {str(e)}")

def init_handlers():
    """Init any module-specific handlers needing DB."""
    global casino_handler
    if casino_handler is None:
        casino_handler = CasinoHandler(db_conn)
    return casino_handler

def setup_profile_handlers(application):
    """Set up profile-related handlers"""
    application.add_handler(create_profile_handler())
    application.add_handler(CommandHandler('timecheck', timecheck_command))

# ------------------------------------------------------------------------------
# NEW ASYNC BOT STARTUP
# ------------------------------------------------------------------------------
async def run_telegram_bot_async() -> None:
    """Fully async bot startup + scheduler initialization + polling."""
    # Initialize the scheduler locally
    scheduler = AsyncIOScheduler()
    try:
        scheduler.start()
    except SchedulerAlreadyRunningError:
        logger.warning("Scheduler is already running. Skipping scheduler start.")

    # Make sure environment & paths are correct
    check_environment()
    TOKEN = TIDDIES_AND_TITS_BOT_TOKEN
    if not TOKEN:
        raise ValueError("No TIDDIES_AND_TITS_BOT_TOKEN found.")

    # Initialize scheduler in an active event loop

    scheduler.start()

    # Setup persistence
    persistence_path = os.path.join(script_dir, 'bot_persistence')
    os.makedirs(persistence_path, exist_ok=True)
    persistence = PicklePersistence(
        filepath=os.path.join(persistence_path, 'conversation_states.pickle'),
        store_data=PersistenceInput(
            bot_data=True,
            chat_data=True,
            user_data=True,
            callback_data=True
        ),
        update_interval=60,
        single_file=True,
        on_flush=False
    )

    # Create app
    application = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    # Casino
    global casino_handler
    casino_handler = init_handlers()
    setup_profile_handlers(application)

    # Add conversation handlers first
    application.add_handler(set_timezone_conversation_handler)
    application.add_handler(reminder_conversation_handler)
    application.add_handler(CallbackQueryHandler(wrap_handler_with_auth(handle_vote), pattern='^vote_'))
    application.add_handler(CallbackQueryHandler(wrap_handler_with_auth(relay_action), pattern='^(join_relay|start_relay|moveup|movedown|skip|end_relay)'))
    application.add_handler(CallbackQueryHandler(wrap_handler_with_auth(move_priority), pattern=r'^edit_'))
    application.add_handler(CallbackQueryHandler(wrap_handler_with_auth(casino_handler.handle_callback), pattern='^(casino_|calc_|compare_)'))

    # Image commands
    application.add_handler(CommandHandler('draw_me', wrap_handler_with_auth(handle_draw_me_command)))
    application.add_handler(CommandHandler('create', wrap_handler_with_auth(handle_draw_me_command)))
    application.add_handler(CommandHandler('draw_multiple', wrap_handler_with_auth(handle_draw_multiple_command)))
    application.add_handler(CommandHandler('edit_image', wrap_handler_with_auth(handle_edit_image_command)))

    # Collection commands
    application.add_handler(CommandHandler('set_favorite', wrap_handler_with_auth(set_favorite)))
    application.add_handler(CommandHandler('add_to_collection', wrap_handler_with_auth(add_to_collection)))
    application.add_handler(CommandHandler('add_to_group_collection', wrap_handler_with_auth(add_to_group_collection)))
    application.add_handler(CommandHandler('view_personal_collection', wrap_handler_with_auth(view_personal_collection)))
    application.add_handler(CommandHandler('view_group_collection', wrap_handler_with_auth(view_group_collection)))

    # TODO
    application.add_handler(CommandHandler('list_todos', wrap_handler_with_auth(list_todos)))
    application.add_handler(CommandHandler('remark', wrap_handler_with_auth(add_remark)))

    # Authorization
    application.add_handler(CommandHandler('grant_access', wrap_handler_with_auth(grant_access)))
    application.add_handler(CommandHandler('request_access', request_access))

    # Basic
    application.add_handler(CommandHandler('start', wrap_handler_with_auth(start)))
    application.add_handler(CommandHandler('menu', wrap_handler_with_auth(show_menu)))
    application.add_handler(CommandHandler('help', wrap_handler_with_auth(help_command)))

    # Features
    application.add_handler(CommandHandler('b2b', wrap_handler_with_auth(calculate_bets_command)))
    application.add_handler(CommandHandler('hows', wrap_handler_with_auth(check_user_mood)))
    application.add_handler(CommandHandler('random_boobs', wrap_handler_with_auth(random_tiddies)))
    application.add_handler(CommandHandler('add_synonym', wrap_handler_with_auth(add_synonym)))
    application.add_handler(CommandHandler('relay', wrap_handler_with_auth(relay_command)))
    application.add_handler(CommandHandler('join_relay', wrap_handler_with_auth(join_relay_command)))
    application.add_handler(CommandHandler('vote', wrap_handler_with_auth(vote_command)))

    # Member updates
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, wrap_handler_with_auth(handle_new_member))
    )
    application.add_handler(
        ChatMemberHandler(wrap_handler_with_auth(handle_chat_member_update), ChatMemberHandler.MY_CHAT_MEMBER)
    )

    # Keyword triggers
    for pattern, handler in [
        (r'\bwen coco\b', wen_coco_handler),
        (r'\bwen rish\b', wen_rish_handler),
        (r'\bwen tits\b', wen_tits_handler),
        (r'cunt\b', increment_cunt_counter)
    ]:
        application.add_handler(MessageHandler(filters.TEXT & filters.Regex(pattern), wrap_handler_with_auth(handler)))

    # Activity
    application.add_handler(CommandHandler('night_owls', wrap_handler_with_auth(night_owls_command)))
    application.add_handler(CommandHandler('most_active_users', wrap_handler_with_auth(most_active_users_command)))

    # Search / content
    application.add_handler(CommandHandler('show_me', wrap_handler_with_auth(search_pornstar_command)))
    application.add_handler(CommandHandler('gimme', wrap_handler_with_auth(fetch_image_command)))
    application.add_handler(CommandHandler('porn', wrap_handler_with_auth(random_movie_command)))
    application.add_handler(CommandHandler('mines_multi', wrap_handler_with_auth(mines_multi_command)))
    application.add_handler(CommandHandler('convert', wrap_handler_with_auth(convert_crypto)))

    # GPT
    application.add_handler(CommandHandler('ask_gpt', wrap_handler_with_auth(ask_gpt_command)))
    application.add_handler(CommandHandler('show_airdrops', wrap_handler_with_auth(airdrops_and_giveaways_command)))
    application.add_handler(CommandHandler('all', wrap_handler_with_auth(mention_all)))
    application.add_handler(CommandHandler('shuffle_userlist', wrap_handler_with_auth(shuffle_the_usernames)))
    application.add_handler(CommandHandler('bc', wrap_handler_with_auth(query_gpt_command)))

    # Casino
    application.add_handler(CommandHandler('casino', wrap_handler_with_auth(casino_handler.handle_casino_command)))

    # Timezone
    application.add_handler(CommandHandler('show_times', wrap_handler_with_auth(show_times)))

    # Button handler
    application.add_handler(CallbackQueryHandler(button))

    # Error handler
    application.add_error_handler(error_handler)

    # Last: save messages
    application.add_handler(MessageHandler(filters.ALL, save_message_to_db))

    logger.info("Starting Telegram bot (async).")
    await application.run_polling()
    logger.info("Telegram bot stopped.")

# ------------------------------------------------------------------------------
# Keep your existing retry logic, but call the async function inside it
# ------------------------------------------------------------------------------
def run_telegram_bot() -> None:
    """Sync wrapper around async bot start."""
    logger.info("Initializing bot")
    max_retries = 5
    retry_delay = 5
    current_retry = 0

    while current_retry < max_retries:
        try:
            current_retry += 1
            asyncio.run(run_telegram_bot_async())  # <--- key change
        except Exception as e:
            logger.critical(f"Bot crashed: {str(e)}")
            logger.critical(traceback.format_exc())
            if current_retry < max_retries:
                logger.info(f"Restart {current_retry}/{max_retries} in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.critical("Max retries reached. Shutting down.")
                sys.exit(1)

if __name__ == '__main__':
    run_telegram_bot()
