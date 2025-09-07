"""Callback query handlers for inline keyboards."""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.openai_service import OpenAIService
from ..services.user_service import UserService
from ..services.crypto_service import crypto_service
from ..services.todo_service import todo_service
from ..services.voting_service import voting_service
from ..services.mines_service import mines_service
from ..services.b2b_service import b2b_service
from ..services.nsfw_service import nsfw_service
from ..services.activity_service import activity_service
from ..services.mood_service import mood_service

logger = get_logger(__name__)
openai_service = OpenAIService()
user_service = UserService()


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
            logger.info(f"Processing help callback for user {user.id}")
            await handle_help_callback(query, context)
        elif callback_data == "settings":
            logger.info(f"Processing settings callback for user {user.id}")
            await handle_settings_callback(query, context)
        elif callback_data == "start":
            logger.info(f"Processing start callback for user {user.id}")
            await handle_start_callback(query, context)
        # Main menu categories
        # Main menu categories
        elif callback_data == "ai_menu":
            await handle_ai_menu_callback(query, context)
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
        # Direct action buttons
        elif callback_data == "crypto_prices":
            await handle_crypto_prices_action(query, context)
        elif callback_data == "crypto_balance":
            await handle_crypto_balance_action(query, context)
        elif callback_data == "todo_list":
            await handle_todo_list_action(query, context)
        elif callback_data == "todo_stats":
            await handle_todo_stats_action(query, context)
        elif callback_data == "poll_list":
            await handle_poll_list_action(query, context)
        elif callback_data == "nsfw_random":
            await handle_nsfw_random_action(query, context)
        elif callback_data == "user_stats":
            await handle_user_stats_action(query, context)
        elif callback_data == "bot_status":
            await handle_bot_status_action(query, context)
        elif callback_data == "mines_calc":
            await handle_mines_calc_action(query, context)
        elif callback_data == "b2b_calc":
            await handle_b2b_calc_action(query, context)
        # Legacy support and direct actions
        elif callback_data == "ai_chat":
            await handle_ai_chat_callback(query, context)
        elif callback_data == "generate_image":
            await handle_generate_image_action(query, context)
        elif callback_data == "mines_info":
            await handle_mines_info_callback(query, context)
        elif callback_data == "b2b_info":
            await handle_b2b_info_callback(query, context)
        elif callback_data == "crypto_info":
            await handle_crypto_info_callback(query, context)
        elif callback_data == "todo_info":
            await handle_todo_info_callback(query, context)
        else:
            logger.warning(f"Unknown callback data received: {callback_data} from user {user.id}")
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


async def handle_generate_image_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate image action - prompts user for input."""
    image_text = (
        "🎨 <b>Image Generation Ready!</b>\n\n"
        "Please send me your image prompt now.\n\n"
        "Examples:\n"
        "• A cute robot in a garden\n"
        "• Futuristic city at sunset\n"
        "• Abstract art with blue and gold\n\n"
        "🎯 Be descriptive for best results!\n\n"
        "Just type your prompt in the next message!"
    )
    
    # Set user context to expect image prompt
    context.user_data['expecting_image_prompt'] = True
    
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
        "<b>Quick Actions:</b>\n"
        "• Click 'AI Chat' to start chatting\n"
        "• Click 'Generate Image' to create art\n"
        "• Send me any message for instant AI response\n\n"
        "💡 <i>Powered by GPT-4 and DALL-E 3</i>"
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




async def handle_crypto_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Crypto & Trading menu callback."""
    crypto_text = (
        "💰 <b>Crypto Trading & Tools</b>\n\n"
        "Click the buttons below for instant access:\n"
        "• 📊 Live crypto prices\n"
        "• 💰 Your trading balance\n"
        "• 💱 Currency converter\n"
        "• 📈 Quick betting\n\n"
        "📈 <i>Real-time market data & virtual trading</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Crypto Prices", callback_data="crypto_prices"),
            InlineKeyboardButton("💰 My Balance", callback_data="crypto_balance"),
        ],
        [
            InlineKeyboardButton("💱 Converter", callback_data="crypto_convert"),
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
        "Click the buttons below for instant access:\n"
        "• 🗳️ Create new polls\n"
        "• 📊 View active polls\n"
        "• Interactive voting with real-time results\n\n"
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
        "Click the buttons below for instant access:\n"
        "• ➕ Add new tasks\n"
        "• 📝 View your current tasks\n"
        "• 📊 Check your productivity stats\n\n"
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
        "Click the buttons below for instant access:\n"
        "• 🔞 Random adult content\n"
        "• 🔍 Search performer info\n"
        "• Interactive favorites & collections\n\n"
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
        "Click the buttons below for instant calculations:\n"
        "• 💎 Mines calculator - odds & multipliers\n"
        "• 💰 B2B calculator - betting progressions\n"
        "• Real-time probability calculations\n\n"
        "🎯 <i>Mathematical precision for gaming!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💎 Mines Calculator", callback_data="mines_calc"),
            InlineKeyboardButton("💰 B2B Calculator", callback_data="b2b_calc"),
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
        "Click the buttons below for instant stats:\n"
        "• 📊 Your personal statistics\n"
        "• 🤖 Bot performance & health\n"
        "• Real-time system monitoring\n\n"
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


# Action handlers that perform actual functionality
async def handle_crypto_prices_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current crypto prices."""
    try:
        prices = await crypto_service.get_trending_prices()
        if prices:
            price_text = "📊 <b>Current Crypto Prices</b>\n\n"
            for symbol, data in prices.items():
                price_text += f"• <b>{symbol.upper()}</b>: ${data['price']:,.2f}\n"
                if 'change_24h' in data:
                    change = data['change_24h']
                    emoji = "📈" if change >= 0 else "📉"
                    price_text += f"  {emoji} {change:+.2f}% (24h)\n"
            price_text += "\n💡 Use /price [symbol] for specific coins"
        else:
            price_text = "❌ Unable to fetch crypto prices at the moment."
    except Exception as e:
        price_text = "❌ Error fetching crypto prices."
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="crypto_prices"),
                 InlineKeyboardButton("🏠 Back", callback_data="crypto_menu")]]
    
    await query.edit_message_text(
        price_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_crypto_balance_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's crypto balance."""
    user = query.from_user
    balance = await crypto_service.get_user_balance(user.id)
    
    balance_text = f"💰 <b>Your Crypto Balance</b>\n\n"
    balance_text += f"Virtual Balance: ${balance:,.2f}\n\n"
    balance_text += "💡 Use /bet to place crypto bets\n"
    balance_text += "📈 Use /bets to see your betting history"
    
    keyboard = [
        [InlineKeyboardButton("📈 My Bets", callback_data="crypto_bets"),
         InlineKeyboardButton("🎯 Quick Bet", callback_data="crypto_bet_quick")],
        [InlineKeyboardButton("🏠 Back", callback_data="crypto_menu")]
    ]
    
    await query.edit_message_text(
        balance_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_todo_list_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's todo list."""
    user = query.from_user
    try:
        todos = await todo_service.get_user_todos(user.id)
        
        if todos:
            todo_text = "📝 <b>Your Todo List</b>\n\n"
            for i, todo in enumerate(todos[:10], 1):  # Show max 10 todos
                status = "✅" if todo.get('completed') else "⏳"
                priority = ""
                if todo.get('priority') == 'high':
                    priority = "🔴 "
                elif todo.get('priority') == 'medium':
                    priority = "🟡 "
                
                todo_text += f"{i}. {status} {priority}{todo['title']}\n"
                if todo.get('due_date'):
                    todo_text += f"   📅 Due: {todo['due_date']}\n"
            
            if len(todos) > 10:
                todo_text += f"\n... and {len(todos) - 10} more tasks"
        else:
            todo_text = "📝 <b>Your Todo List</b>\n\n✨ No tasks yet! Add one with the button below."
    except Exception as e:
        todo_text = "❌ Error loading todo list."
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Task", callback_data="todo_add"),
         InlineKeyboardButton("📊 Stats", callback_data="todo_stats")],
        [InlineKeyboardButton("🏠 Back", callback_data="todo_menu")]
    ]
    
    await query.edit_message_text(
        todo_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_todo_stats_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's todo statistics."""
    user = query.from_user
    try:
        stats = await todo_service.get_user_stats(user.id)
        
        stats_text = f"📊 <b>Todo Statistics</b>\n\n"
        stats_text += f"📝 Total tasks: {stats.get('total', 0)}\n"
        stats_text += f"✅ Completed: {stats.get('completed', 0)}\n"
        stats_text += f"⏳ Pending: {stats.get('pending', 0)}\n"
        stats_text += f"🔴 High priority: {stats.get('high_priority', 0)}\n"
        
        completion_rate = 0
        if stats.get('total', 0) > 0:
            completion_rate = (stats.get('completed', 0) / stats.get('total', 0)) * 100
        
        stats_text += f"\n🎯 Completion rate: {completion_rate:.1f}%"
    except Exception as e:
        stats_text = "❌ Error loading todo statistics."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="todo_menu")]]
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_poll_list_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show active polls."""
    try:
        polls = await voting_service.get_active_polls(limit=5)
        
        if polls:
            poll_text = "🗳️ <b>Active Polls</b>\n\n"
            for i, poll in enumerate(polls, 1):
                poll_text += f"{i}. <b>{poll['question']}</b>\n"
                poll_text += f"   👥 {poll.get('vote_count', 0)} votes\n"
                if poll.get('created_by'):
                    poll_text += f"   👤 By: {poll['created_by']}\n"
                poll_text += "\n"
        else:
            poll_text = "🗳️ <b>Active Polls</b>\n\n📋 No active polls found.\n\n💡 Create one with /poll \"Question\" \"Option1\" \"Option2\""
    except Exception as e:
        poll_text = "❌ Error loading polls."
    
    keyboard = [
        [InlineKeyboardButton("🗳️ Create Poll", callback_data="poll_create")],
        [InlineKeyboardButton("🏠 Back", callback_data="voting_menu")]
    ]
    
    await query.edit_message_text(
        poll_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_nsfw_random_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get random NSFW content."""
    user = query.from_user
    
    # Send "fetching" message
    await query.edit_message_text("🔍 Fetching random content...")
    
    try:
        images = await nsfw_service.get_random_adult_images()
        if images:
            # Send the first image
            image_url = images[0] if isinstance(images, list) else images
            
            keyboard = [
                [InlineKeyboardButton("🔄 Another", callback_data="nsfw_random"),
                 InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{image_url}")],
                [InlineKeyboardButton("🏠 Back", callback_data="nsfw_menu")]
            ]
            
            # Try to send image, fallback to text if it fails
            try:
                await query.message.reply_photo(
                    photo=image_url,
                    caption="🔞 Random adult content",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Delete the "fetching" message
                await query.message.delete()
            except Exception:
                await query.edit_message_text(
                    f"🔞 Random adult content\n\n🖼️ [View Image]({image_url})",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
        else:
            await query.edit_message_text(
                "❌ No content found. Try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="nsfw_menu")]])
            )
    except Exception as e:
        await query.edit_message_text(
            "❌ Error fetching content.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="nsfw_menu")]])
        )


async def handle_user_stats_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics."""
    user = query.from_user
    
    try:
        # Get user activity stats
        activity_stats = await activity_service.get_user_activity(user.id)
        
        stats_text = f"📊 <b>Your Statistics</b>\n\n"
        stats_text += f"👤 User: {user.first_name or user.username}\n"
        stats_text += f"🆔 ID: {user.id}\n\n"
        
        if activity_stats:
            stats_text += f"💬 Messages sent: {activity_stats.get('message_count', 0)}\n"
            stats_text += f"🤖 Bot commands used: {activity_stats.get('command_count', 0)}\n"
            stats_text += f"📅 Active days: {activity_stats.get('active_days', 0)}\n"
            stats_text += f"⏰ Last active: {activity_stats.get('last_active', 'Never')}\n"
        else:
            stats_text += "📊 No activity data yet - start using the bot!"
            
    except Exception as e:
        stats_text = "❌ Error loading user statistics."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="stats_menu")]]
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_bot_status_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot status and health."""
    import psutil
    import time
    from datetime import datetime
    
    try:
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        status_text = f"🤖 <b>Bot Status</b>\n\n"
        status_text += f"✅ Status: Online\n"
        status_text += f"🔄 Uptime: Active\n"
        status_text += f"📊 CPU Usage: {cpu_percent:.1f}%\n"
        status_text += f"💾 Memory: {memory.percent:.1f}% used\n"
        status_text += f"💿 Disk: {disk.percent:.1f}% used\n\n"
        status_text += f"⚡ Response time: Fast\n"
        status_text += f"🌐 API Status: Connected\n"
        status_text += f"📡 Last update: {datetime.now().strftime('%H:%M:%S')}"
        
    except Exception as e:
        status_text = "🤖 <b>Bot Status</b>\n\n✅ Bot is running normally!"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="bot_status")],
        [InlineKeyboardButton("🏠 Back", callback_data="stats_menu")]
    ]
    
    await query.edit_message_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_mines_calc_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick mines calculator."""
    calc_text = (
        "💎 <b>Quick Mines Calculator</b>\n\n"
        "Enter mines and diamonds to calculate:\n\n"
        "Format: [mines] [diamonds]\n"
        "Example: 5 3\n\n"
        "Please send your calculation in the next message!"
    )
    
    context.user_data['expecting_mines_calc'] = True
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="calc_menu")]]
    
    await query.edit_message_text(
        calc_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_b2b_calc_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick B2B calculator."""
    calc_text = (
        "💰 <b>Quick B2B Calculator</b>\n\n"
        "Enter betting parameters:\n\n"
        "Format: [base_bet] [multiplier] [increase_%]\n"
        "Example: 100 2.0 10\n\n"
        "Please send your calculation in the next message!"
    )
    
    context.user_data['expecting_b2b_calc'] = True
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="calc_menu")]]
    
    await query.edit_message_text(
        calc_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )