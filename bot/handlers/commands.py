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
        "I'm a modern, cutting-edge Telegram bot with AI capabilities.\n\n"
        "Here's what I can do:\n"
        "• 🧠 AI-powered conversations\n"
        "• 🎨 Image generation and editing\n"
        "• 🎲 Gambling calculators (Mines, B2B)\n"
        "• 💰 Crypto tools and conversions\n"
        "• 📝 Task management\n"
        "• 🎯 Smart reminders\n\n"
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
    """Handle the /menu command with fresh buttons."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    logger.info("Menu command received", user_id=user.id, username=user.username)
    
    menu_text = (
        f"📋 **Main Menu** - {user.first_name or user.username}\n\n"
        "Choose an option below:"
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
        "🆘 <b>Bot Commands Help</b>\n\n"
        "<b>🤖 Basic Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settings - Configure bot settings\n"
        "/status - Check bot status\n\n"
        
        "<b>🧠 AI Commands:</b>\n"
        "/ask [question] - Ask AI a question\n"
        "/chat - Start AI conversation\n"
        "/translate [text] - Translate text\n"
        "/analyze [text] - Analyze text sentiment\n\n"
        
        "<b>🎨 Image Commands:</b>\n"
        "/generate [prompt] - Generate image from text\n"
        "/edit - Edit an image (reply to image)\n"
        "/variation - Create image variations\n\n"
        
        "<b>📝 Productivity:</b>\n"
        "/todo [task] - Add a todo item\n"
        "/todos - List all todos\n"
        "/remind [time] [message] - Set reminder\n"
        "/note [text] - Save a note\n\n"
        
        "<b>🎲 Gambling Tools:</b>\n"
        "/mines [multiplier] - Find mines/diamonds for target multiplier\n"
        "/mines [mines] [diamonds] - Calculate multiplier and odds\n"
        "/b2b [base_bet] [multiplier] [increase%] - Betting progression calculator\n\n"
        
        "<b>💰 Crypto Tools:</b>\n"
        "/crypto [amount] [from] [to] - Convert crypto currencies\n"
        "/price [symbol] - Get crypto price\n\n"
        
        "<b>📊 Analytics:</b>\n"
        "/stats - Show usage statistics\n"
        "/activity - Show activity report\n\n"
        
        "<b>⚙️ Admin Commands:</b>\n"
        "/admin - Admin panel (admin only)\n"
        "/broadcast [message] - Broadcast message\n"
        "/users - List all users\n\n"
        
        "💡 <i>Tip: You can also just send me a message and I'll respond with AI!</i>"
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