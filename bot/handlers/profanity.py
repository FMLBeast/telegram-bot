"""Profanity monitoring and statistics handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..services.profanity_service import profanity_service
from ..services.user_service import user_service
from ..decorators.auth import auth_check
from ..core.logging import get_logger

logger = get_logger(__name__)


@auth_check
async def cunt_counter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cunt_counter command - show profanity statistics."""
    try:
        # Get target user (can be self or mentioned user)
        target_user_id = update.effective_user.id
        target_display = "your"
        
        # Check if a user was mentioned
        if context.args and context.args[0].startswith('@'):
            username = context.args[0][1:]  # Remove @
            # In a real implementation, you'd look up user by username
            await update.message.reply_text(
                "🔍 User lookup by username not yet implemented. Use `/cunt_stats` to see your own stats.",
                parse_mode=ParseMode.HTML
            )
            return
        elif update.message.reply_to_message:
            target_user_id = update.message.reply_to_message.from_user.id
            target_display = update.message.reply_to_message.from_user.first_name or "their"
        
        # Send loading message
        loading_message = await update.message.reply_text(
            f"🔍 Analyzing {target_display} profanity usage...",
            parse_mode=ParseMode.HTML
        )
        
        # Get profanity stats
        chat_id = update.effective_chat.id if update.effective_chat.type != 'private' else None
        stats = await profanity_service.get_user_profanity_stats(
            user_id=target_user_id,
            chat_id=chat_id,
            days=30
        )
        
        if 'error' in stats:
            await loading_message.edit_text(
                f"❌ Error getting profanity stats: {stats['error']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Format response
        message_parts = [
            f"🤬 <b>Profanity Counter for {stats['display_name']}</b>",
            "",
            f"📊 <b>Overview (Last 30 days):</b>",
            f"• Total profanity used: <b>{stats['total_profanity_count']}</b>",
            f"• Messages with profanity: <b>{stats['messages_with_profanity']}</b>",
            f"• Total messages checked: <b>{stats['total_messages_checked']}</b>",
            f"• Profanity rate: <b>{stats['profanity_rate']}%</b>",
        ]
        
        if stats['top_words']:
            message_parts.append("")
            message_parts.append("🏆 <b>Most Used Words:</b>")
            for i, (word, count) in enumerate(stats['top_words'][:5], 1):
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1] if i <= 5 else f"{i}."
                message_parts.append(f"{medal} {word}: <b>{count}</b> times")
        
        if stats['total_profanity_count'] == 0:
            message_parts.append("")
            message_parts.append("😇 <i>This user has a surprisingly clean mouth!</i>")
        elif stats['profanity_rate'] > 50:
            message_parts.append("")
            message_parts.append("🚨 <i>This user needs to wash their mouth with soap!</i>")
        elif stats['profanity_rate'] > 20:
            message_parts.append("")
            message_parts.append("😅 <i>Someone's been a bit naughty with their words!</i>")
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("📈 Chat Leaderboard", callback_data="profanity_leaderboard"),
                InlineKeyboardButton("📝 Word Stats", callback_data="profanity_word_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"profanity_refresh_{target_user_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response_text = "\n".join(message_parts)
        await loading_message.edit_text(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        # Log command usage
        await user_service.log_command_usage(
            update.effective_user.id, 
            "cunt_counter", 
            target_user=target_user_id
        )
        
    except Exception as e:
        logger.error(f"Error in cunt_counter_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while getting profanity stats.",
            parse_mode=ParseMode.HTML
        )


@auth_check
async def profanity_leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /profanity_leaderboard command - show chat profanity leaderboard."""
    try:
        # Only works in groups
        if update.effective_chat.type == 'private':
            await update.message.reply_text(
                "👥 This command only works in group chats!",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Send loading message
        loading_message = await update.message.reply_text(
            "🏆 Generating profanity leaderboard...",
            parse_mode=ParseMode.HTML
        )
        
        # Get leaderboard
        chat_id = update.effective_chat.id
        leaderboard = await profanity_service.get_chat_profanity_leaderboard(
            chat_id=chat_id,
            days=7,
            limit=10
        )
        
        if not leaderboard:
            await loading_message.edit_text(
                "😇 No profanity detected in this chat in the last 7 days!\n"
                "Everyone has been very well-behaved! 👼",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Format leaderboard
        message_parts = [
            "🤬 <b>Profanity Leaderboard</b>",
            f"<i>Top potty-mouths in the last 7 days:</i>",
            ""
        ]
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        for i, user_data in enumerate(leaderboard):
            medal = medals[i]
            rate = user_data['profanity_rate']
            total = user_data['total_profanity_count']
            top_word = user_data.get('top_word', 'N/A')
            
            message_parts.append(
                f"{medal} <b>{user_data['display_name']}</b>\n"
                f"    💬 {total} profanities ({rate}% of messages)\n"
                f"    🏆 Favorite word: <code>{top_word}</code>"
            )
        
        message_parts.extend([
            "",
            "💡 <i>Use /cunt_counter to see detailed stats for yourself!</i>"
        ])
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("📝 Word Stats", callback_data="profanity_word_stats"),
                InlineKeyboardButton("🔄 Refresh", callback_data="profanity_leaderboard_refresh")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response_text = "\n".join(message_parts)
        await loading_message.edit_text(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in profanity_leaderboard_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while getting the leaderboard.",
            parse_mode=ParseMode.HTML
        )


@auth_check
async def word_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /word_stats command - show statistics for a specific word."""
    try:
        # Check if word was provided
        if not context.args:
            monitored_words = list(profanity_service.get_monitored_words())[:10]
            words_text = ", ".join(f"<code>{word}</code>" for word in sorted(monitored_words))
            
            await update.message.reply_text(
                f"📝 <b>Word Statistics</b>\n\n"
                f"💡 <b>Usage:</b> /word_stats [word]\n"
                f"📝 <b>Example:</b> /word_stats cunt\n\n"
                f"🔍 <b>Monitored words:</b>\n{words_text}\n\n"
                f"<i>Use /cunt_counter for overall profanity stats!</i>",
                parse_mode=ParseMode.HTML
            )
            return
        
        word = context.args[0].lower()
        
        # Send loading message
        loading_message = await update.message.reply_text(
            f"🔍 Analyzing usage of '<code>{word}</code>'...",
            parse_mode=ParseMode.HTML
        )
        
        # Get word stats
        chat_id = update.effective_chat.id if update.effective_chat.type != 'private' else None
        stats = await profanity_service.get_word_specific_stats(
            word=word,
            chat_id=chat_id,
            days=7,
            limit=10
        )
        
        if 'error' in stats:
            await loading_message.edit_text(
                f"❌ {stats['error']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Format response
        message_parts = [
            f"📝 <b>Statistics for '<code>{stats['word']}</code>'</b>",
            f"<i>Last 7 days:</i>",
            "",
            f"📊 <b>Overview:</b>",
            f"• Total usage: <b>{stats['total_usage']}</b> times",
            f"• Used by: <b>{stats['unique_users']}</b> different users",
        ]
        
        if stats['top_users']:
            message_parts.append("")
            message_parts.append("🏆 <b>Top Users:</b>")
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            
            for i, user_data in enumerate(stats['top_users'][:5]):
                medal = medals[i]
                message_parts.append(
                    f"{medal} {user_data['display_name']}: <b>{user_data['count']}</b> times"
                )
        
        if stats['total_usage'] == 0:
            message_parts.append("")
            message_parts.append(f"😇 <i>Nobody has used '{word}' recently. How wholesome!</i>")
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🏆 Leaderboard", callback_data="profanity_leaderboard"),
                InlineKeyboardButton("📊 User Stats", callback_data=f"profanity_refresh_{update.effective_user.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response_text = "\n".join(message_parts)
        await loading_message.edit_text(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in word_stats_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while getting word statistics.",
            parse_mode=ParseMode.HTML
        )


async def profanity_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle profanity-related callback queries."""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "profanity_leaderboard":
            # Show chat leaderboard
            if update.effective_chat.type == 'private':
                await query.edit_message_text("👥 Leaderboards only work in group chats!")
                return
            
            loading_message = await query.edit_message_text(
                "🏆 Loading leaderboard...",
                parse_mode=ParseMode.HTML
            )
            
            leaderboard = await profanity_service.get_chat_profanity_leaderboard(
                chat_id=update.effective_chat.id,
                days=7,
                limit=10
            )
            
            if not leaderboard:
                await loading_message.edit_text(
                    "😇 No profanity detected in this chat in the last 7 days!"
                )
                return
            
            # Format and send leaderboard (similar to handler above)
            message_parts = [
                "🤬 <b>Profanity Leaderboard</b>",
                "<i>Top potty-mouths in the last 7 days:</i>",
                ""
            ]
            
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            
            for i, user_data in enumerate(leaderboard):
                medal = medals[i]
                rate = user_data['profanity_rate']
                total = user_data['total_profanity_count']
                top_word = user_data.get('top_word', 'N/A')
                
                message_parts.append(
                    f"{medal} <b>{user_data['display_name']}</b>\n"
                    f"    💬 {total} profanities ({rate}% of messages)\n"
                    f"    🏆 Favorite: <code>{top_word}</code>"
                )
            
            keyboard = [
                [
                    InlineKeyboardButton("📝 Word Stats", callback_data="profanity_word_stats"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="profanity_leaderboard")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_message.edit_text(
                "\n".join(message_parts),
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        elif query.data == "profanity_word_stats":
            # Show info about word stats
            monitored_words = list(profanity_service.get_monitored_words())[:10]
            words_text = ", ".join(f"<code>{word}</code>" for word in sorted(monitored_words))
            
            await query.edit_message_text(
                f"📝 <b>Word Statistics</b>\n\n"
                f"💡 Use <code>/word_stats [word]</code> to see detailed usage statistics for any monitored word.\n\n"
                f"🔍 <b>Currently monitored:</b>\n{words_text}\n\n"
                f"<i>Example: /word_stats cunt</i>",
                parse_mode=ParseMode.HTML
            )
            
        elif query.data.startswith("profanity_refresh_"):
            user_id = int(query.data.replace("profanity_refresh_", ""))
            
            loading_message = await query.edit_message_text(
                "🔄 Refreshing stats...",
                parse_mode=ParseMode.HTML
            )
            
            chat_id = update.effective_chat.id if update.effective_chat.type != 'private' else None
            stats = await profanity_service.get_user_profanity_stats(
                user_id=user_id,
                chat_id=chat_id,
                days=30
            )
            
            # Format response (similar to main handler)
            message_parts = [
                f"🤬 <b>Profanity Counter for {stats['display_name']}</b>",
                "",
                f"📊 <b>Overview (Last 30 days):</b>",
                f"• Total profanity used: <b>{stats['total_profanity_count']}</b>",
                f"• Messages with profanity: <b>{stats['messages_with_profanity']}</b>",
                f"• Profanity rate: <b>{stats['profanity_rate']}%</b>",
            ]
            
            if stats['top_words']:
                message_parts.append("")
                message_parts.append("🏆 <b>Most Used Words:</b>")
                for i, (word, count) in enumerate(stats['top_words'][:5], 1):
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
                    message_parts.append(f"{medal} {word}: <b>{count}</b> times")
            
            keyboard = [
                [
                    InlineKeyboardButton("📈 Chat Leaderboard", callback_data="profanity_leaderboard"),
                    InlineKeyboardButton("📝 Word Stats", callback_data="profanity_word_stats")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_message.edit_text(
                "\n".join(message_parts),
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error in profanity_callback_handler: {str(e)}", exc_info=True)
        await query.edit_message_text("❌ An error occurred.")