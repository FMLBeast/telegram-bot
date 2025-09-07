"""Clean callback query handlers for inline keyboards."""

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
        # Action buttons
        elif callback_data == "crypto_prices":
            await handle_crypto_prices(query, context)
        elif callback_data == "crypto_balance":
            await handle_crypto_balance(query, context)
        elif callback_data == "todo_list":
            await handle_todo_list(query, context)
        elif callback_data == "todo_stats":
            await handle_todo_stats(query, context)
        elif callback_data == "polls_active":
            await handle_polls_active(query, context)
        elif callback_data == "nsfw_random":
            await handle_nsfw_random(query, context)
        elif callback_data == "stats_user":
            await handle_user_stats(query, context)
        elif callback_data == "mines_quick":
            await handle_mines_quick(query, context)
        elif callback_data == "b2b_quick":
            await handle_b2b_quick(query, context)
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
        "**Quick Actions:**\n"
        "Use the buttons below for instant access!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Live Prices", callback_data="crypto_prices"),
            InlineKeyboardButton("💰 My Balance", callback_data="crypto_balance"),
        ],
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
        "**Quick Actions:**\n"
        "Use the buttons below for instant access!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📋 My Todos", callback_data="todo_list"),
            InlineKeyboardButton("📊 Todo Stats", callback_data="todo_stats"),
        ],
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
        "**Quick Actions:**\n"
        "Use the buttons below for instant calculations!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💎 Mines Calc", callback_data="mines_quick"),
            InlineKeyboardButton("📈 B2B Calc", callback_data="b2b_quick"),
        ],
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
        "**Quick Actions:**\n"
        "⚠️ *Adults only - by using buttons you confirm 18+ age*"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔞 Random Content", callback_data="nsfw_random"),
        ],
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
        "**Quick Actions:**\n"
        "Use the buttons below to access active polls!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗳️ Active Polls", callback_data="polls_active"),
        ],
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
        [InlineKeyboardButton("📊 My Stats", callback_data="stats_user")],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# Action handlers that perform actual functionality
async def handle_crypto_prices(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show live crypto prices."""
    await query.edit_message_text("📊 Fetching live crypto prices...")
    
    try:
        symbols = ["BTC", "ETH", "BNB"]
        price_text = "📊 **Live Crypto Prices**\n\n"
        
        for symbol in symbols:
            try:
                price_data = await crypto_service.get_crypto_price(symbol)
                if price_data and 'price' in price_data:
                    price = price_data['price']
                    change = price_data.get('change_percent', 0)
                    emoji = "📈" if change >= 0 else "📉"
                    price_text += f"• **{symbol}**: ${price:,.2f} {emoji} {change:+.1f}%\n"
            except Exception:
                price_text += f"• **{symbol}**: Error\n"
        
        price_text += f"\n💡 Use `/price [symbol]` for any coin"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="crypto_prices")],
            [InlineKeyboardButton("🏠 Back", callback_data="crypto_menu")]
        ]
        
    except Exception:
        price_text = "❌ Error fetching prices."
        keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="crypto_menu")]]
    
    await query.edit_message_text(price_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_crypto_balance(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's crypto balance."""
    user = query.from_user
    
    try:
        balance_data = await crypto_service.get_user_balance(user.id)
        balance = balance_data.get('balance', 1000.0) if balance_data else 1000.0
        
        balance_text = f"💰 **Your Trading Balance**\n\n💵 Balance: **${balance:,.2f}**\n\n💡 Use `/bet [symbol] [up/down] [amount]`"
        
    except Exception:
        balance_text = "❌ Error loading balance."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="crypto_menu")]]
    await query.edit_message_text(balance_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_todo_list(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's todo list."""
    user = query.from_user
    
    try:
        todo_lists = await todo_service.get_user_lists(user.id)
        
        if todo_lists:
            todo_text = "📝 **Your Todo Lists**\n\n"
            for todo_list in todo_lists[:2]:
                list_name = todo_list.get('name', 'Tasks')
                todo_text += f"📋 **{list_name}**\n"
                
                tasks = await todo_service.get_tasks(user_id=user.id, list_id=todo_list['id'], limit=3)
                for task in (tasks or []):
                    status = "✅" if task.get('completed') else "⏳"
                    title = task.get('title', 'Untitled')[:25]
                    todo_text += f"  {status} {title}\n"
                todo_text += "\n"
        else:
            todo_text = "📝 **Your Todo Lists**\n\n✨ No tasks yet!\n💡 Use `/add_todo [task]`"
            
    except Exception:
        todo_text = "❌ Error loading todos."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="todo_menu")]]
    await query.edit_message_text(todo_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_todo_stats(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show todo statistics."""
    user = query.from_user
    
    try:
        stats = await todo_service.get_task_stats(user.id)
        total = stats.get('total_tasks', 0)
        completed = stats.get('completed_tasks', 0)
        
        stats_text = f"📊 **Todo Stats**\n\n📝 Total: **{total}**\n✅ Done: **{completed}**\n"
        
        if total > 0:
            rate = (completed / total) * 100
            stats_text += f"🎯 Rate: **{rate:.0f}%**"
        else:
            stats_text += "💡 Add tasks to see stats!"
        
    except Exception:
        stats_text = "❌ Error loading stats."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="todo_menu")]]
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_polls_active(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show active polls."""
    try:
        polls = await voting_service.get_active_polls()
        
        if polls:
            poll_text = "🗳️ **Active Polls**\n\n"
            for i, poll in enumerate(polls[:2], 1):
                question = poll.get('question', 'Poll')[:40]
                votes = poll.get('total_votes', 0)
                poll_text += f"{i}. **{question}**\n   👥 {votes} votes\n\n"
        else:
            poll_text = "🗳️ **Active Polls**\n\n📋 No active polls\n💡 Use `/poll \"Q\" \"A\" \"B\"`"
    except Exception:
        poll_text = "❌ Error loading polls."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="voting_menu")]]
    await query.edit_message_text(poll_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_nsfw_random(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get random NSFW content."""
    await query.edit_message_text("🔍 Fetching...")
    
    try:
        image = await nsfw_service.get_image_by_category("boobs")
        if image and image.get('image_url'):
            try:
                await query.message.reply_photo(photo=image['image_url'], caption="🔞 Random content")
                await query.message.delete()
            except Exception:
                await query.edit_message_text(f"🔞 [View Image]({image['image_url']})", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ No content available")
    except Exception:
        await query.edit_message_text("❌ Error fetching content")


async def handle_user_stats(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics."""
    user = query.from_user
    
    try:
        stats = await activity_service.get_user_activity_stats(user.id)
        
        stats_text = f"📊 **Your Stats**\n\n👤 **{user.first_name or user.username}**\n"
        
        if stats and isinstance(stats, dict):
            msgs = stats.get('total_messages', 0)
            days = stats.get('active_days', 0)
            stats_text += f"💬 Messages: **{msgs}**\n📅 Days: **{days}**"
        else:
            stats_text += "📊 No data yet!"
        
    except Exception:
        stats_text = "❌ Error loading stats."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="stats_menu")]]
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_mines_quick(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick mines calculation."""
    result = await mines_service.calculate_multiplier_from_mines_diamonds(5, 3)
    
    if result:
        calc_text = f"💎 **Mines Example**\n\n⛏️ 5 mines, 💎 3 diamonds\n🎯 **{result['multiplier']}x** multiplier\n📊 **{result['winning_chance']:.1f}%** chance\n\n💡 `/mines [mines] [diamonds]`"
    else:
        calc_text = "❌ Calculator error."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="calc_menu")]]
    await query.edit_message_text(calc_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_b2b_quick(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick B2B calculation."""
    bets, _, total = await b2b_service.calculate_bets(100, 2.0, 10, 3)
    
    if bets:
        calc_text = f"💰 **B2B Example**\n\n$100 → 2x → +10%\n"
        for i, bet in enumerate(bets, 1):
            calc_text += f"{i}. ${bet:.0f}\n"
        calc_text += f"\n💡 `/b2b [base] [mult] [inc%]`"
    else:
        calc_text = "❌ Calculator error."
    
    keyboard = [[InlineKeyboardButton("🏠 Back", callback_data="calc_menu")]]
    await query.edit_message_text(calc_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")