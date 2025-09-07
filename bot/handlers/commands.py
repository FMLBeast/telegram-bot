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
        "I'm your comprehensive AI assistant with powerful features:\n\n"
        "🌟 <b>Quick Actions:</b>\n"
        "• 🧠 AI chat & image generation\n"
        "• 💰 Crypto tools & calculators\n"
        "• 📝 Todo & task management\n"
        "• 🗳️ Polls & voting systems\n"
        "• 🔞 NSFW content (18+)\n"
        "• 📊 Stats & analytics\n\n"
        "✨ Click the buttons below for instant access!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 AI & Images", callback_data="ai_menu"),
            InlineKeyboardButton("💰 Crypto Tools", callback_data="crypto_menu"),
        ],
        [
            InlineKeyboardButton("📝 Todo List", callback_data="todo_menu"),
            InlineKeyboardButton("🗳️ Polls", callback_data="voting_menu"),
        ],
        [
            InlineKeyboardButton("🎲 Calculators", callback_data="calc_menu"),
            InlineKeyboardButton("🔞 NSFW (18+)", callback_data="nsfw_menu"),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
            InlineKeyboardButton("🆘 Help", callback_data="help"),
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
        f"📋 **Interactive Menu** - {user.first_name or user.username}\n\n"
        "🎯 **All Features Available:**\n"
        "• 🧠 AI Chat & Image Generation\n"
        "• 💰 Crypto Trading & Tools (Real API)\n"
        "• 🗳️ Polls & Voting System\n"
        "• 📝 Todo & Task Management\n"
        "• 📊 Activity & Stats Analytics\n"
        "• 🔞 NSFW Content (18+)\n"
        "• 🎲 Game Calculators (Mines, B2B)\n\n"
        "Click any button for instant access:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 AI & Images", callback_data="ai_menu"),
            InlineKeyboardButton("💰 Crypto Tools", callback_data="crypto_menu"),
        ],
        [
            InlineKeyboardButton("📝 Todo List", callback_data="todo_menu"),
            InlineKeyboardButton("🗳️ Polls", callback_data="voting_menu"),
        ],
        [
            InlineKeyboardButton("🎲 Calculators", callback_data="calc_menu"),
            InlineKeyboardButton("🔞 NSFW (18+)", callback_data="nsfw_menu"),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
            InlineKeyboardButton("🆘 Help", callback_data="help"),
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
        "🆘 <b>Interactive Bot Help</b>\n\n"
        "Click the buttons below for instant access to features:\n\n"
        
        "🧠 <b>AI & Images:</b> Chat with AI, generate images\n"
        "💰 <b>Crypto Tools:</b> Live prices, trading, conversions\n"
        "📝 <b>Todo List:</b> Task management & productivity\n"
        "🗳️ <b>Polls:</b> Create & participate in voting\n"
        "🎲 <b>Calculators:</b> Mines & B2B betting tools\n"
        "🔞 <b>NSFW (18+):</b> Adult content & features\n"
        "📊 <b>Stats:</b> Analytics & bot performance\n\n"
        
        "💡 <b>Quick Tips:</b>\n"
        "• Just send me any message for AI chat\n"
        "• All features work with interactive buttons\n"
        "• No need to remember commands!\n\n"
        
        "✨ <i>Choose a category below to get started!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 AI & Images", callback_data="ai_menu"),
            InlineKeyboardButton("💰 Crypto Tools", callback_data="crypto_menu"),
        ],
        [
            InlineKeyboardButton("📝 Todo List", callback_data="todo_menu"),
            InlineKeyboardButton("🗳️ Polls", callback_data="voting_menu"),
        ],
        [
            InlineKeyboardButton("🎲 Calculators", callback_data="calc_menu"),
            InlineKeyboardButton("🔞 NSFW (18+)", callback_data="nsfw_menu"),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
            InlineKeyboardButton("🏠 Back to Start", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )