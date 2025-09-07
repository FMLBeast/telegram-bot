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
        f"🤖 **Welcome back {user.first_name or user.username}!** 👋\n\n"
        "Choose what you'd like to do:\n\n"
        "🧠 **AI Chat & Images** - Chat with AI, generate images\n"
        "💰 **Crypto Tools** - Live prices, trading tools\n"
        "📝 **Todo Management** - Organize your tasks\n"
        "🎲 **Calculators** - Mines & B2B betting tools\n"
        "🔞 **NSFW Content** - Adult content (18+)\n"
        "🗳️ **Polls & Voting** - Create and participate in polls\n"
        "📊 **Statistics** - Your activity stats"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 AI & Images", callback_data="ai_menu"),
            InlineKeyboardButton("💰 Crypto Tools", callback_data="crypto_menu"),
        ],
        [
            InlineKeyboardButton("📝 Todo List", callback_data="todo_menu"),
            InlineKeyboardButton("🎲 Calculators", callback_data="calc_menu"),
        ],
        [
            InlineKeyboardButton("🔞 NSFW (18+)", callback_data="nsfw_menu"),
            InlineKeyboardButton("🗳️ Polls", callback_data="voting_menu"),
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="stats_menu"),
            InlineKeyboardButton("🆘 Help", callback_data="help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /menu command with comprehensive feature menu."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    logger.info("Menu command received", user_id=user.id, username=user.username)
    
    menu_text = (
        f"🤖 **Welcome {user.first_name or user.username}!**\n\n"
        "Choose what you'd like to do:\n\n"
        "🧠 **AI Chat & Images** - Chat with AI, generate images\n"
        "💰 **Crypto Tools** - Live prices, trading tools\n"
        "📝 **Todo Management** - Organize your tasks\n"
        "🎲 **Calculators** - Mines & B2B betting tools\n"
        "🔞 **NSFW Content** - Adult content (18+)\n"
        "🗳️ **Polls & Voting** - Create and participate in polls\n"
        "📊 **Statistics** - Your activity stats"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 AI & Images", callback_data="ai_menu"),
            InlineKeyboardButton("💰 Crypto Tools", callback_data="crypto_menu"),
        ],
        [
            InlineKeyboardButton("📝 Todo List", callback_data="todo_menu"),
            InlineKeyboardButton("🎲 Calculators", callback_data="calc_menu"),
        ],
        [
            InlineKeyboardButton("🔞 NSFW (18+)", callback_data="nsfw_menu"),
            InlineKeyboardButton("🗳️ Polls", callback_data="voting_menu"),
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="stats_menu"),
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
        "🆘 **Help & Commands**\n\n"
        "**Basic Commands:**\n"
        "• `/start` - Main menu\n"
        "• `/menu` - Show menu\n"
        "• `/help` - Show help\n\n"
        "**AI Commands:**\n"
        "• `/ask [question]` - Ask AI anything\n"
        "• `/draw_me [prompt]` - Generate image\n\n"
        "**Crypto Commands:**\n"
        "• `/price [symbol]` - Get crypto price\n"
        "• `/convert [amount] [from] [to]` - Convert currency\n\n"
        "**Todo Commands:**\n"
        "• `/add_todo [task]` - Add task\n"
        "• `/list_todos` - Show tasks\n\n"
        "**Calculator Commands:**\n"
        "• `/mines [mines] [diamonds]` - Mines calculator\n"
        "• `/b2b [base] [multiplier] [increase%]` - B2B calculator\n\n"
        "**NSFW Commands (18+):**\n"
        "• `/random_boobs` - Random content\n"
        "• `/gimme [type]` - Specific content\n\n"
        "**Poll Commands:**\n"
        "• `/poll \"Question\" \"Option1\" \"Option2\"` - Create poll\n"
        "• `/polls` - List active polls\n\n"
        "💡 *Use the menu buttons for easier access!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )