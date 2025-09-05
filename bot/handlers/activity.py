"""User activity tracking handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..decorators.auth import auth_check
from ..services.activity_service import activity_service
from ..services.user_service import UserService

logger = get_logger(__name__)
user_service = UserService()


@auth_check
async def night_owls_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /night_owls command to show users active during night hours."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    logger.info("Night owls request", user_id=user_id, chat_id=chat_id)
    
    try:
        await update.message.reply_text("🌙 Analyzing night owl activity...")
        
        # Get night owls data
        night_owls = await activity_service.get_night_owls(
            chat_id=chat_id,
            days=7
        )
        
        if not night_owls:
            await update.message.reply_text(
                "🌙 **Night Owls Report**\n\n"
                "No night owl activity found in the past 7 days.\n"
                "Maybe everyone's getting proper sleep! 😴",
                parse_mode="Markdown"
            )
            return
        
        # Format response
        message_lines = ["🌙 **Night Owls Report** (22:00-06:00)\n"]
        
        for i, user in enumerate(night_owls[:10], 1):
            name = user['display_name']
            count = user['night_messages']
            
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = "🌙"
            
            message_lines.append(
                f"{emoji} **{i}.** {name}: {count} messages"
            )
        
        message_lines.extend([
            "",
            "📊 *Analysis period: Last 7 days*",
            "🕐 *Night hours: 22:00 - 06:00*"
        ])
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Activity Stats", callback_data="activity_stats"),
                InlineKeyboardButton("🔄 Refresh", callback_data="night_owls_refresh"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in night owls handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error generating night owls report. Please try again.")


@auth_check
async def most_active_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /most_active_users command to show most active users."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    logger.info("Most active users request", user_id=user_id, chat_id=chat_id)
    
    try:
        await update.message.reply_text("📊 Analyzing user activity...")
        
        # Get most active users
        active_users = await activity_service.get_most_active_users(
            chat_id=chat_id,
            days=7,
            limit=10
        )
        
        if not active_users:
            await update.message.reply_text(
                "📊 **Most Active Users Report**\n\n"
                "No activity found in the past 7 days.\n"
                "Time to wake up the chat! 💬",
                parse_mode="Markdown"
            )
            return
        
        # Format response
        message_lines = ["📊 **Most Active Users Report**\n"]
        
        total_messages = sum(user['message_count'] for user in active_users)
        
        for i, user in enumerate(active_users, 1):
            name = user['display_name']
            count = user['message_count']
            avg_length = user['avg_message_length']
            percentage = round((count / total_messages) * 100, 1) if total_messages > 0 else 0
            
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = "📈"
            
            message_lines.append(
                f"{emoji} **{i}.** {name}\n"
                f"    💬 {count} messages ({percentage}%)\n"
                f"    📏 Avg: {avg_length} chars"
            )
        
        message_lines.extend([
            "",
            f"📈 *Total messages tracked: {total_messages}*",
            "📊 *Analysis period: Last 7 days*"
        ])
        
        keyboard = [
            [
                InlineKeyboardButton("🌙 Night Owls", callback_data="night_owls"),
                InlineKeyboardButton("📊 Chat Stats", callback_data="chat_stats"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="active_users_refresh"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in most active users handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error generating activity report. Please try again.")


@auth_check
async def my_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /my_activity command to show personal activity stats."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    logger.info("Personal activity request", user_id=user_id, chat_id=chat_id)
    
    try:
        await update.message.reply_text("📊 Analyzing your activity...")
        
        # Get user activity stats
        activity_stats = await activity_service.get_user_activity_stats(
            user_id=user_id,
            chat_id=chat_id,
            days=30
        )
        
        total_messages = activity_stats['total_messages']
        messages_per_day = activity_stats['messages_per_day']
        most_active_hour = activity_stats['most_active_hour']
        hourly_dist = activity_stats['hourly_distribution']
        
        # Create activity chart (simple text representation)
        chart_hours = []
        if hourly_dist:
            max_count = max(hourly_dist.values())
            for hour in range(24):
                count = hourly_dist.get(hour, 0)
                if max_count > 0:
                    bar_length = int((count / max_count) * 10)
                    bar = '█' * bar_length + '░' * (10 - bar_length)
                else:
                    bar = '░' * 10
                chart_hours.append(f"{hour:02d}:00 {bar} {count}")
        
        message_lines = [
            f"📊 **Your Activity Report**\n",
            f"👤 **Stats for last 30 days:**",
            f"💬 Total messages: **{total_messages}**",
            f"📈 Messages per day: **{messages_per_day}**",
            f"🕐 Most active hour: **{most_active_hour}:00**" if most_active_hour is not None else "🕐 Most active hour: **Not available**",
            "",
            f"📊 **Hourly Activity Pattern:**"
        ]
        
        if chart_hours:
            # Show only hours with activity or peak hours
            active_hours = [line for line in chart_hours if ' 0' not in line.split()[-1] or int(line.split()[-1]) > 0]
            if active_hours:
                message_lines.extend(active_hours[:12])  # Limit to 12 hours to avoid message length issues
            else:
                message_lines.append("No activity pattern available")
        else:
            message_lines.append("No hourly data available")
        
        keyboard = [
            [
                InlineKeyboardButton("🌙 Night Activity", callback_data=f"user_night_activity_{user_id}"),
                InlineKeyboardButton("📈 Trends", callback_data=f"user_activity_trends_{user_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in personal activity handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error generating your activity report. Please try again.")


async def handle_activity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle activity-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info("Activity callback", user_id=user_id, callback_data=callback_data)
    
    try:
        if callback_data == "night_owls":
            # Show night owls
            night_owls = await activity_service.get_night_owls(
                chat_id=update.effective_chat.id if update.effective_chat else None,
                days=7
            )
            
            if night_owls:
                message = "🌙 **Night Owls (22:00-06:00)**\n\n"
                for i, user in enumerate(night_owls[:5], 1):
                    name = user['display_name']
                    count = user['night_messages']
                    message += f"{i}. {name}: {count} messages\n"
            else:
                message = "🌙 No night owl activity found."
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data == "active_users_refresh":
            # Refresh active users
            await query.edit_message_text("📊 Refreshing activity data...")
            
            active_users = await activity_service.get_most_active_users(
                chat_id=update.effective_chat.id if update.effective_chat else None,
                days=7,
                limit=10
            )
            
            if active_users:
                message = "📊 **Most Active Users (Refreshed)**\n\n"
                for i, user in enumerate(active_users[:5], 1):
                    name = user['display_name']
                    count = user['message_count']
                    message += f"{i}. {name}: {count} messages\n"
            else:
                message = "📊 No activity data available."
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data == "chat_stats":
            # Show chat statistics
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id:
                stats = await activity_service.get_chat_activity_summary(chat_id, days=7)
                
                message = (
                    f"📊 **Chat Activity Summary**\n\n"
                    f"💬 Total messages: {stats['total_messages']}\n"
                    f"👥 Active users: {stats['unique_users']}\n"
                    f"📈 Messages/day: {stats['messages_per_day']}\n"
                    f"💬 Messages/user: {stats['messages_per_user']}"
                )
            else:
                message = "📊 Chat statistics not available for this chat type."
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        else:
            await query.edit_message_text("❓ Unknown activity action.")
            
    except Exception as e:
        logger.error("Error handling activity callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.edit_message_text("❌ Error processing activity request.")