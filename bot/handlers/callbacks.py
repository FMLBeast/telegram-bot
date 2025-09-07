"""Clean callback query handlers for inline keyboards."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.openai_service import OpenAIService
from ..services.user_service import UserService

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
    
    logger.info("Callback received", user_id=user.id, callback_data=callback_data)
    
    try:
        if callback_data == "start":
            await show_main_menu(query, context)
        elif callback_data == "help":
            await show_help_menu(query, context)
        elif callback_data == "ai_menu":
            await show_ai_menu(query, context)
        elif callback_data == "crypto_menu":
            await show_crypto_menu(query, context)
        elif callback_data == "todo_menu":
            await show_todo_menu(query, context)
        elif callback_data == "calc_menu":
            await show_calc_menu(query, context)
        elif callback_data == "nsfw_menu":
            await show_nsfw_menu(query, context)
        elif callback_data == "voting_menu":
            await show_voting_menu(query, context)
        elif callback_data == "stats_menu":
            await show_stats_menu(query, context)
        else:
            await query.edit_message_text("❌ Unknown command. Use /start to go back to the main menu.")
            
    except Exception as e:
        logger.error("Callback error", callback_data=callback_data, error=str(e), exc_info=True)
        try:
            await query.edit_message_text("❌ An error occurred. Use /start to go back to the main menu.")
        except Exception:
            pass


async def show_main_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu."""
    user = query.from_user
    
    text = (
        f"🤖 **Welcome {user.first_name or user.username}!**\n\n"
        "Choose what you'd like to do:\n\n"
        "🧠 **AI Chat & Images** - Chat with AI, generate images\n"
        "💰 **Crypto Tools** - Live prices, trading tools\n"
        "📝 **Todo Management** - Organize your tasks\n"
        "🎲 **Calculators** - Mines & B2B betting tools\n"
        "🔞 **NSFW Content** - Adult content (18+)\n"
        "🗳️ **Polls & Voting** - Create and participate in polls\n"
        "📊 **Statistics** - Your activity stats\n"
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
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_help_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help menu."""
    text = (
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
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_ai_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show AI menu."""
    text = (
        "🧠 **AI Chat & Image Generation**\n\n"
        "**Available Features:**\n"
        "• AI conversation with GPT-4\n"
        "• AI image generation with DALL-E\n"
        "• Multiple image creation\n\n"
        "**How to Use:**\n"
        "• Use `/ask [question]` for AI chat\n"
        "• Use `/draw_me [prompt]` for images\n"
        "• Use `/draw_multiple [prompt]` for multiple images\n\n"
        "💡 *Just type your question or image prompt!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_crypto_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show crypto menu."""
    text = (
        "💰 **Crypto Tools**\n\n"
        "**Available Features:**\n"
        "• Live cryptocurrency prices\n"
        "• Currency converter\n"
        "• Virtual crypto betting\n"
        "• Trading balance tracking\n\n"
        "**How to Use:**\n"
        "• Use `/price [symbol]` for current prices\n"
        "• Use `/convert [amount] [from] [to]` for conversion\n"
        "• Use `/bet [symbol] [up/down] [amount]` for betting\n"
        "• Use `/balance` to check your virtual balance\n\n"
        "💡 *All trading is virtual - no real money involved!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_todo_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show todo menu."""
    text = (
        "📝 **Todo Management**\n\n"
        "**Available Features:**\n"
        "• Create and organize todo lists\n"
        "• Add tasks with priorities\n"
        "• Mark tasks as complete\n"
        "• Track productivity statistics\n\n"
        "**How to Use:**\n"
        "• Use `/add_todo [task]` to add tasks\n"
        "• Use `/list_todos` to see your tasks\n"
        "• Use `/complete_todo [id]` to mark complete\n"
        "• Use `/todo_stats` for statistics\n\n"
        "💡 *Stay organized and productive!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_calc_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show calculator menu."""
    text = (
        "🎲 **Game Calculators**\n\n"
        "**Available Calculators:**\n"
        "• Mines game calculator\n"
        "• B2B betting progression calculator\n\n"
        "**How to Use:**\n"
        "• Use `/mines [mines] [diamonds]` for odds calculation\n"
        "• Use `/mines [multiplier]` to find best combinations\n"
        "• Use `/b2b [base] [multiplier] [increase%]` for betting progression\n\n"
        "**Examples:**\n"
        "• `/mines 5 3` - Calculate odds for 5 mines, 3 diamonds\n"
        "• `/b2b 100 2.0 10` - Base bet 100, 2x multiplier, 10% increase\n\n"
        "💡 *Mathematical precision for gaming!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_nsfw_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show NSFW menu."""
    text = (
        "🔞 **NSFW Adult Content (18+)**\n\n"
        "⚠️ **Adults Only - 18+ Required** ⚠️\n\n"
        "**Available Features:**\n"
        "• Random adult images\n"
        "• Random adult videos\n"
        "• Content search by category\n"
        "• Performer information lookup\n\n"
        "**How to Use:**\n"
        "• Use `/random_boobs` for random images\n"
        "• Use `/random_video` for random videos\n"
        "• Use `/gimme [type]` for specific content\n"
        "• Use `/show_me [name]` for performer info\n\n"
        "⚠️ *This content is for adults only!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_voting_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show voting menu."""
    text = (
        "🗳️ **Polls & Voting System**\n\n"
        "**Available Features:**\n"
        "• Create custom polls\n"
        "• Multiple choice voting\n"
        "• Real-time results\n"
        "• Anonymous voting options\n\n"
        "**How to Use:**\n"
        "• Use `/poll \"Question\" \"Option1\" \"Option2\"` to create polls\n"
        "• Use `/polls` to list active polls\n"
        "• Use `/vote [poll_id] [option]` to cast votes\n\n"
        "**Examples:**\n"
        "• `/poll \"Best pizza?\" \"Margherita\" \"Pepperoni\" \"Hawaiian\"`\n\n"
        "💡 *Full democracy in your chats!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_stats_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show statistics menu."""
    user = query.from_user
    
    text = (
        f"📊 **Statistics Dashboard**\n\n"
        f"**Your Info:**\n"
        f"• User: {user.first_name or user.username}\n"
        f"• ID: {user.id}\n\n"
        f"**Available Stats:**\n"
        f"• Personal activity statistics\n"
        f"• Command usage analytics\n"
        f"• Bot performance metrics\n"
        f"• Feature usage tracking\n\n"
        f"**How to Use:**\n"
        f"• Use `/my_activity` for your stats\n"
        f"• Use `/most_active_users` for leaderboards\n"
        f"• Use `/night_owls` for activity patterns\n\n"
        f"💡 *Data-driven insights for optimization!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )