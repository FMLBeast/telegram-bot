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
        # Main menu categories
        elif callback_data == "ai_menu":
            await handle_ai_menu_callback(query, context)
        elif callback_data == "casino_menu":
            await handle_casino_menu_callback(query, context)
        elif callback_data == "crypto_menu":
            await handle_crypto_menu_callback(query, context)
        elif callback_data == "voting_menu":
            await handle_voting_menu_callback(query, context)
        elif callback_data == "todo_menu":
            await handle_todo_menu_callback(query, context)
        elif callback_data == "nsfw_menu":
            await handle_nsfw_menu_callback(query, context)
        elif callback_data == "calc_menu":
            await handle_calc_menu_callback(query, context)
        elif callback_data == "stats_menu":
            await handle_stats_menu_callback(query, context)
        # Legacy support
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


async def handle_ai_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI & Images menu callback."""
    ai_text = (
        "🧠 <b>AI & Image Generation</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/ask_gpt [question]</code> - Ask AI anything\n"
        "• <code>/draw_me [prompt]</code> - Generate AI image\n"
        "• <code>/create [prompt]</code> - Generate AI image\n"
        "• <code>/draw_multiple [prompt]</code> - Multiple images\n\n"
        "<b>Quick Actions:</b>\n"
        "• Just send me a message for AI chat!\n"
        "• Send detailed prompts for better images\n\n"
        "💡 <i>AI powered by GPT-4 and DALL-E 3</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧠 Start AI Chat", callback_data="ai_chat"),
            InlineKeyboardButton("🎨 Generate Image", callback_data="generate_image"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        ai_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_casino_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Casino & Games menu callback."""
    casino_text = (
        "🎰 <b>Casino & Gambling Games</b>\n\n"
        "<b>Available Games:</b>\n"
        "• <code>/casino</code> - Full casino (dice, slots, blackjack)\n"
        "• <code>/bet [game]</code> - Quick betting games\n\n"
        "<b>Casino Features:</b>\n"
        "• 🎲 Dice rolling vs house\n"
        "• 🎰 Slot machines with multipliers\n"
        "• 🃏 Blackjack card game\n"
        "• 🎯 Lucky number games\n"
        "• 🪙 Coin flip betting\n\n"
        "💰 <i>Virtual credits - no real money involved!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🎰 Enter Casino", callback_data="casino_enter"),
            InlineKeyboardButton("🎲 Quick Bet", callback_data="casino_quick_bet"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        casino_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_crypto_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Crypto & Trading menu callback."""
    crypto_text = (
        "💰 <b>Crypto Trading & Tools</b>\n\n"
        "<b>Trading Commands:</b>\n"
        "• <code>/price [symbol]</code> - Get crypto prices\n"
        "• <code>/bet [symbol] [up/down] [amount]</code> - Price betting\n"
        "• <code>/balance</code> - Check trading balance\n"
        "• <code>/bets</code> - View betting history\n\n"
        "<b>Conversion Tools:</b>\n"
        "• <code>/convert [amount] [from] [to]</code> - Currency converter\n"
        "• Supports crypto & fiat currencies\n"
        "• Auto PHP conversion for specific chats\n\n"
        "📈 <i>Real-time market data & virtual trading</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Crypto Prices", callback_data="crypto_prices"),
            InlineKeyboardButton("💱 Converter", callback_data="crypto_convert"),
        ],
        [
            InlineKeyboardButton("💰 My Balance", callback_data="crypto_balance"),
            InlineKeyboardButton("📈 Quick Bet", callback_data="crypto_bet_quick"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        crypto_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_voting_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Polls & Voting menu callback."""
    voting_text = (
        "🗳️ <b>Polls & Voting System</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/poll \"Question\" \"Option1\" \"Option2\"</code> - Create poll\n"
        "• <code>/polls</code> - List active polls\n"
        "• <code>/vote [poll_id] [option]</code> - Cast vote\n\n"
        "<b>Poll Features:</b>\n"
        "• Single & multiple choice polls\n"
        "• Anonymous voting mode\n"
        "• Quiz mode with correct answers\n"
        "• Real-time results with progress bars\n"
        "• Interactive voting buttons\n\n"
        "📊 <i>Full democracy in your chats!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗳️ Create Poll", callback_data="poll_create"),
            InlineKeyboardButton("📊 Active Polls", callback_data="poll_list"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        voting_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_todo_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Todo & Tasks menu callback."""
    todo_text = (
        "📝 <b>Todo & Task Management</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/add_todo [task]</code> - Add new task\n"
        "• <code>/list_todos</code> - Show all tasks\n"
        "• <code>/complete_todo [id]</code> - Mark complete\n"
        "• <code>/remove_todo [id]</code> - Delete task\n\n"
        "<b>Features:</b>\n"
        "• Priority levels (!high, !medium, !low)\n"
        "• Due date support\n"
        "• Task categories and tags\n"
        "• Progress tracking\n"
        "• Interactive task management\n\n"
        "✅ <i>Stay organized and productive!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Task", callback_data="todo_add"),
            InlineKeyboardButton("📝 View Tasks", callback_data="todo_list"),
        ],
        [
            InlineKeyboardButton("📊 Todo Stats", callback_data="todo_stats"),
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        todo_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_nsfw_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle NSFW Content menu callback."""
    nsfw_text = (
        "🔞 <b>NSFW Adult Content (18+)</b>\n\n"
        "<b>⚠️ Adults Only - 18+ Required ⚠️</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/random_boobs</code> - Random adult content\n"
        "• <code>/show_me [name]</code> - Search performer info\n"
        "• <code>/gimme [type]</code> - Specific content type\n\n"
        "<b>Content Types:</b>\n"
        "• Random adult images with interactive buttons\n"
        "• Performer information and stats\n"
        "• Favorite & collection features\n\n"
        "⚠️ <i>This content is for adults only!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔞 Random Content", callback_data="nsfw_random"),
            InlineKeyboardButton("🔍 Search Info", callback_data="nsfw_search"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        nsfw_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_calc_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Game Calculators menu callback."""
    calc_text = (
        "🎲 <b>Game Calculators</b>\n\n"
        "<b>Available Calculators:</b>\n"
        "• <code>/mines [multiplier]</code> - Mines game calculator\n"
        "• <code>/mines [mines] [diamonds]</code> - Odds calculator\n"
        "• <code>/b2b [base] [mult] [inc%]</code> - Betting progression\n\n"
        "<b>Calculator Features:</b>\n"
        "• Mines: Find best mine/diamond combinations\n"
        "• B2B: Betting progression strategy analysis\n"
        "• Real-time odds and probability calculations\n"
        "• Detailed strategy recommendations\n\n"
        "🎯 <i>Mathematical precision for gaming!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💎 Mines Calculator", callback_data="mines_info"),
            InlineKeyboardButton("💰 B2B Calculator", callback_data="b2b_info"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        calc_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_stats_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Quick Stats menu callback."""
    stats_text = (
        "📊 <b>Quick Stats & Analytics</b>\n\n"
        "<b>Available Stats:</b>\n"
        "• User activity and command usage\n"
        "• Crypto trading performance\n"
        "• Casino game statistics\n"
        "• Poll participation rates\n"
        "• Todo completion rates\n\n"
        "<b>Quick Actions:</b>\n"
        "• View personal statistics\n"
        "• Check feature usage\n"
        "• Monitor bot performance\n\n"
        "📈 <i>Data-driven insights for optimization!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
            InlineKeyboardButton("🤖 Bot Status", callback_data="bot_status"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="start"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )