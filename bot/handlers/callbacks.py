"""Callback query handlers for inline keyboards."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.openai_service import OpenAIService

logger = get_logger(__name__)
openai_service = OpenAIService()


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()  # Answer the callback query
    
    user = update.effective_user
    callback_data = query.data
    
    logger.info(
        "Callback query received",
        user_id=user.id,
        username=user.username,
        callback_data=callback_data
    )
    
    try:
        if callback_data == "help":
            await handle_help_callback(query, context)
        elif callback_data == "settings":
            await handle_settings_callback(query, context)
        elif callback_data == "start":
            await handle_start_callback(query, context)
        elif callback_data == "ai_chat":
            await handle_ai_chat_callback(query, context)
        elif callback_data == "generate_image":
            await handle_generate_image_callback(query, context)
        elif callback_data == "mines_info":
            await handle_mines_info_callback(query, context)
        elif callback_data == "b2b_info":
            await handle_b2b_info_callback(query, context)
        elif callback_data == "crypto_info":
            await handle_crypto_info_callback(query, context)
        elif callback_data == "todo_info":
            await handle_todo_info_callback(query, context)
        else:
            await query.edit_message_text("🤷‍♂️ Unknown command!")
            
    except Exception as e:
        logger.error(
            "Error handling callback query",
            user_id=user.id,
            callback_data=callback_data,
            error=str(e),
            exc_info=True
        )
        
        try:
            await query.edit_message_text(
                "❌ An error occurred while processing your request."
            )
        except Exception:
            pass  # Ignore if we can't edit the message


async def handle_help_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help callback."""
    help_text = (
        "🆘 <b>Quick Help</b>\n\n"
        "• Send me any message and I'll respond with AI\n"
        "• Use /generate [prompt] to create images\n"
        "• Use /ask [question] for specific questions\n"
        "• Use /help for full command list\n\n"
        "What would you like to do?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 Ask AI", callback_data="ai_chat"),
            InlineKeyboardButton("🎨 Generate Image", callback_data="generate_image"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Start", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_settings_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings callback."""
    settings_text = (
        "⚙️ <b>Bot Settings</b>\n\n"
        "Current settings:\n"
        "• AI Model: GPT-4\n"
        "• Language: Auto-detect\n"
        "• Response Mode: Friendly\n"
        "• Notifications: Enabled\n\n"
        "Settings are automatically optimized for the best experience!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="toggle_notifications"),
            InlineKeyboardButton("🌍 Language", callback_data="change_language"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Start", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_start_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start callback (back to main menu)."""
    welcome_text = (
        "🤖 Welcome back! 👋\n\n"
        "I'm ready to help you with:\n"
        "• 🧠 AI-powered conversations\n"
        "• 🎨 Image generation and editing\n"
        "• 🎲 Gambling calculators (Mines, B2B)\n"
        "• 💰 Crypto tools and conversions\n"
        "• 📝 Task management\n\n"
        "What would you like to do?"
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
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_ai_chat_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI chat callback."""
    chat_text = (
        "🧠 <b>AI Chat Mode</b>\n\n"
        "Just send me any message and I'll respond with AI!\n\n"
        "Examples:\n"
        "• \"Explain quantum computing\"\n"
        "• \"Write a haiku about robots\"\n"
        "• \"Help me plan my day\"\n"
        "• \"What's the weather like in Tokyo?\"\n\n"
        "💬 Go ahead, ask me anything!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        chat_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_generate_image_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate image callback."""
    image_text = (
        "🎨 <b>Image Generation</b>\n\n"
        "Use the command: <code>/generate [your prompt]</code>\n\n"
        "Examples:\n"
        "• <code>/generate a cute robot in a garden</code>\n"
        "• <code>/generate futuristic city at sunset</code>\n"
        "• <code>/generate abstract art with blue and gold</code>\n\n"
        "🎯 Be descriptive for best results!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        image_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_mines_info_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Mines calculator info callback."""
    mines_text = (
        "🎲 <b>Mines Casino Game Calculator</b>\n\n"
        "Calculate multipliers and odds for the Mines casino game!\n\n"
        "<b>Commands:</b>\n"
        "• <code>/mines [multiplier]</code> - Find mines/diamonds for target multiplier\n"
        "• <code>/mines [mines] [diamonds]</code> - Calculate multiplier and odds\n\n"
        "<b>Examples:</b>\n"
        "• <code>/mines 2.5</code> - Find combinations for 2.5x multiplier\n"
        "• <code>/mines 5 3</code> - 5 mines, 3 diamonds to pick\n\n"
        "🎯 Based on a 5×5 grid (25 tiles total)"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mines_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_b2b_info_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle B2B calculator info callback."""
    b2b_text = (
        "💰 <b>B2B Betting Progression Calculator</b>\n\n"
        "Calculate betting progression for back-to-back strategy!\n\n"
        "<b>Command:</b>\n"
        "• <code>/b2b [base_bet] [multiplier] [increase%]</code>\n\n"
        "<b>Examples:</b>\n"
        "• <code>/b2b 100 2.0 10</code> - Base bet 100, 2x multiplier, 10% increase\n"
        "• <code>/b2b 50 1.5 5</code> - Base bet 50, 1.5x multiplier, 5% increase\n\n"
        "📊 Shows 20 rounds of betting progression with totals"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        b2b_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_crypto_info_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle crypto tools info callback."""
    crypto_text = (
        "💱 <b>Crypto Tools</b>\n\n"
        "Convert between cryptocurrencies and get live prices!\n\n"
        "<b>Commands:</b>\n"
        "• <code>/crypto [amount] [from] [to]</code> - Convert currencies\n"
        "• <code>/price [symbol]</code> - Get current price\n\n"
        "<b>Examples:</b>\n"
        "• <code>/crypto 100 BTC USD</code> - Convert 100 BTC to USD\n"
        "• <code>/price ETH</code> - Get Ethereum price\n\n"
        "📈 Real-time market data powered by CoinGecko"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        crypto_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_todo_info_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle todo list info callback."""
    todo_text = (
        "📝 <b>Todo List Manager</b>\n\n"
        "Organize your tasks with smart todo management!\n\n"
        "<b>Commands:</b>\n"
        "• <code>/add_todo [task]</code> - Add a new task\n"
        "• <code>/list_todos</code> - Show all tasks\n"
        "• <code>/complete_todo [id]</code> - Mark task complete\n\n"
        "<b>Examples:</b>\n"
        "• <code>/add_todo Finish project</code>\n"
        "• <code>/add_todo !high Call client tomorrow</code>\n\n"
        "🏷️ Supports priorities, due dates, and tags!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        todo_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )