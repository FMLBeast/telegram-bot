"""Command handlers for the bot."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.user_service import UserService
from ..services.openai_service import OpenAIService

logger = get_logger(__name__)
user_service = UserService()
openai_service = OpenAIService()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    logger.info("Start command received", user_id=user.id, username=user.username)
    
    # Register or update user
    await user_service.create_or_update_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    
    welcome_text = (
        f"🤖 Welcome back {user.first_name or user.username}! 👋\n\n"
        "I'm a comprehensive Telegram bot with advanced AI and analytics.\n\n"
        "🌟 <b>Main Features:</b>\n"
        "• 🧠 AI-powered conversations & image generation\n"
        "• 💰 Real crypto prices, betting & conversions\n"
        "• 🎯 Activity tracking & mood analysis\n"
        "• 🎲 Gambling calculators & casino games\n"
        "• 📝 Task management & smart reminders\n"
        "• 🔞 NSFW content (videos, images, searches)\n"
        "• 🤬 Profanity monitoring & statistics\n"
        "• 📚 Learning tools & synonyms\n"
        "• 🗳️ Polls, voting & group utilities\n\n"
        "✨ Use /help to see all available commands!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🆘 Help", callback_data="help"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
        [
            InlineKeyboardButton("🧠 Ask AI", callback_data="ai_chat"),
            InlineKeyboardButton("🎨 Generate Image", callback_data="generate_image"),
        ],
        [
            InlineKeyboardButton("🎲 Mines Calculator", callback_data="mines_info"),
            InlineKeyboardButton("💰 B2B Calculator", callback_data="b2b_info"),
        ],
        [
            InlineKeyboardButton("💱 Crypto Convert", callback_data="crypto_info"),
            InlineKeyboardButton("📝 Todo List", callback_data="todo_info"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /menu command with comprehensive feature menu."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    logger.info("Menu command received", user_id=user.id, username=user.username)
    
    menu_text = (
        f"📋 **Complete Feature Menu** - {user.first_name or user.username}\n\n"
        "🎯 **All Available Features:**\n"
        "• 🧠 AI Chat & Image Generation\n"
        "• 🎰 Casino & Gambling Games\n"  
        "• 💰 Crypto Trading & Betting (Real API)\n"
        "• 🗳️ Polls & Voting System\n"
        "• 📝 Todo & Task Management\n"
        "• 📊 Activity & Mood Analytics\n"
        "• 🤬 Profanity Monitoring\n"
        "• 🔞 NSFW Content (18+)\n"
        "• 🎲 Game Calculators\n\n"
        "Choose a category below:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🆘 Help", callback_data="help"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
        [
            InlineKeyboardButton("🧠 AI & Images", callback_data="ai_menu"),
            InlineKeyboardButton("🎰 Casino & Games", callback_data="casino_menu"),
        ],
        [
            InlineKeyboardButton("💰 Crypto & Trading", callback_data="crypto_menu"),
            InlineKeyboardButton("🗳️ Polls & Voting", callback_data="voting_menu"),
        ],
        [
            InlineKeyboardButton("📝 Todo & Tasks", callback_data="todo_menu"),
            InlineKeyboardButton("🔞 NSFW Content", callback_data="nsfw_menu"),
        ],
        [
            InlineKeyboardButton("🎲 Game Calculators", callback_data="calc_menu"),
            InlineKeyboardButton("📊 Quick Stats", callback_data="stats_menu"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        menu_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    logger.info("Help command received", user_id=user.id, username=user.username)
    
    help_text = (
        "🆘 <b>Complete Bot Commands Guide</b>\n\n"
        "<b>🤖 Basic Commands:</b>\n"
        "/start - Start the bot\n"
        "/menu - Show main menu\n"
        "/help - Show this help message\n\n"
        
        "<b>🧠 AI Commands:</b>\n"
        "/ask_gpt [question] - Ask AI a question\n"
        "Just message me - AI will respond!\n\n"
        
        "<b>🎨 Image Commands:</b>\n"
        "/draw_me [prompt] - Generate AI image\n"
        "/create [prompt] - Generate AI image (alias)\n"
        "/draw_multiple [prompt] - Generate multiple images\n\n"
        
        "<b>🎰 Casino & Gambling:</b>\n"
        "/casino - Enter the casino (dice, slots, blackjack)\n"
        "/bet [game] - Quick betting games\n\n"
        
        "<b>💰 Crypto & Trading:</b>\n"
        "/price [symbol] - Get crypto price\n"
        "/bet [symbol] [up/down] [amount] - Bet on crypto\n"
        "/balance - Check crypto betting balance\n"
        "/convert [amount] [from] [to] - Convert currencies\n\n"
        
        "<b>🗳️ Polls & Voting:</b>\n"
        "/poll \"Question\" \"Option1\" \"Option2\" - Create poll\n"
        "/polls - List active polls\n"
        "/vote [poll_id] [option] - Cast vote\n\n"
        
        "<b>📝 Todo & Tasks:</b>\n"
        "/add_todo [task] - Add todo item\n"
        "/list_todos - Show all todos\n"
        "/complete_todo [id] - Mark complete\n\n"
        
        "<b>🎲 Game Calculators:</b>\n"
        "/mines [multiplier] or [mines] [diamonds] - Mines calculator\n"
        "/b2b [base] [mult] [inc%] - Betting progression\n\n"
        
        "<b>🔞 NSFW Content (18+):</b>\n"
        "/random_boobs - Random adult content\n"
        "/random_video - Random NSFW video\n"
        "/fetch_image [category] - Get NSFW image by category\n"
        "/show_me [name] - Search adult performer\n"
        "/gimme [type] - Specific adult content\n\n"
        
        "<b>🤬 Profanity Monitoring:</b>\n"
        "/cunt_counter - Your profanity statistics\n"
        "/profanity_leaderboard - Chat profanity leaderboard\n"
        "/word_stats [word] - Statistics for specific word\n\n"
        
        "<b>📊 Activity & Analytics:</b>\n"
        "/night_owls - Most active users at night\n"
        "/most_active_users - Most active users\n"
        "/my_activity - Your activity statistics\n"
        "/hows [user] - Analyze user mood\n"
        "/mood_trends - User mood trends over time\n\n"
        
        "<b>📚 Synonyms & Learning:</b>\n"
        "/add_synonym [word] [synonyms] - Add word synonyms\n"
        "/synonym_of_day - Get daily synonym\n"
        "/search_synonyms [word] - Find synonyms\n\n"
        
        "<b>🔧 Utilities:</b>\n"
        "/all - Mention all users in group\n"
        "/shuffle_userlist - Shuffle user list\n"
        "/random_user - Pick random user\n"
        "/set_timezone [timezone] - Set your timezone\n"
        "/remind_me [time] [message] - Set reminder\n\n"
        
        "💡 <i>Use /menu for interactive navigation!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🏠 Back to Start", callback_data="start"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )