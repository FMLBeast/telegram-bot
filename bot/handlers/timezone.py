"""Timezone and reminder management handlers."""

import re
from datetime import datetime, timedelta
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.timezone_service import timezone_service
from ..decorators.auth import auth_check

logger = get_logger(__name__)


def parse_time_input(time_str: str) -> Optional[datetime]:
    """Parse various time formats into datetime."""
    if not time_str:
        return None
    
    time_str = time_str.strip().lower()
    now = datetime.now()
    
    # Relative time patterns
    relative_patterns = [
        (r"in (\d+) minutes?", lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r"in (\d+) hours?", lambda m: now + timedelta(hours=int(m.group(1)))),
        (r"in (\d+) days?", lambda m: now + timedelta(days=int(m.group(1)))),
        (r"(\d+)m", lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r"(\d+)h", lambda m: now + timedelta(hours=int(m.group(1)))),
        (r"(\d+)d", lambda m: now + timedelta(days=int(m.group(1)))),
    ]
    
    for pattern, func in relative_patterns:
        match = re.search(pattern, time_str)
        if match:
            return func(match)
    
    # Absolute time patterns
    time_patterns = [
        r"(\d{1,2}):(\d{2})\s*(am|pm)?",  # HH:MM [AM/PM]
        r"(\d{1,2})\s*(am|pm)",          # H [AM/PM]
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
            am_pm = match.group(3) if len(match.groups()) > 2 else None
            
            if am_pm:
                if am_pm == "pm" and hour != 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0
            
            # Create time for today or tomorrow if passed
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            
            return target
    
    # Date + time patterns
    date_time_patterns = [
        r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})",  # YYYY-MM-DD HH:MM
        r"(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})",          # MM/DD HH:MM
    ]
    
    for pattern in date_time_patterns:
        match = re.search(pattern, time_str)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 5:  # YYYY-MM-DD HH:MM
                    year, month, day, hour, minute = map(int, groups)
                else:  # MM/DD HH:MM
                    month, day, hour, minute = map(int, groups)
                    year = now.year
                
                return datetime(year, month, day, hour, minute)
            except ValueError:
                continue
    
    return None


@auth_check
async def set_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's timezone."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🌍 **Set Your Timezone**\n\n"
            "Usage: `/set_timezone <timezone>`\n\n"
            "**Examples:**\n"
            "`/set_timezone America/New_York`\n"
            "`/set_timezone Europe/London`\n"
            "`/set_timezone Asia/Tokyo`\n\n"
            "Use `/search_timezone <city>` to find your timezone!",
            parse_mode="Markdown"
        )
        return
    
    timezone_str = " ".join(context.args).replace(" ", "_")
    
    try:
        success = await timezone_service.set_user_timezone(user_id, timezone_str)
        
        if success:
            # Get timezone info to show confirmation
            tz_info = await timezone_service.get_timezone_info(timezone_str)
            
            if tz_info:
                message = (
                    f"✅ **Timezone Set Successfully!**\n\n"
                    f"🌍 **Timezone:** {tz_info['display_name']}\n"
                    f"🕐 **Current Time:** {tz_info['current_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🌐 **UTC Offset:** {tz_info['utc_offset']}\n\n"
                    f"All reminders will now use your local time!"
                )
            else:
                message = f"✅ Timezone set to `{timezone_str}`"
        else:
            message = (
                f"❌ Invalid timezone: `{timezone_str}`\n\n"
                f"Use `/search_timezone <city>` to find valid timezones."
            )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error setting timezone", user_id=user_id, timezone=timezone_str, error=str(e))
        await update.message.reply_text(
            "❌ An error occurred while setting your timezone."
        )


@auth_check
async def search_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for timezones by city name."""
    
    if not update.message or not update.effective_user:
        return
    
    if not context.args:
        await update.message.reply_text(
            "🔍 **Search Timezones**\n\n"
            "Usage: `/search_timezone <city or country>`\n\n"
            "**Examples:**\n"
            "`/search_timezone new york`\n"
            "`/search_timezone london`\n"
            "`/search_timezone tokyo`"
        )
        return
    
    query = " ".join(context.args)
    
    try:
        results = await timezone_service.search_timezones(query, limit=8)
        
        if not results:
            await update.message.reply_text(
                f"🔍 No timezones found for: `{query}`\n\n"
                f"Try searching for a major city name.",
                parse_mode="Markdown"
            )
            return
        
        message = f"🔍 **Timezone Search Results for:** `{query}`\n\n"
        
        for i, result in enumerate(results, 1):
            message += (
                f"{i}. **{result['city']}**\n"
                f"   `{result['timezone']}`\n"
                f"   {result['display_name']}\n\n"
            )
        
        message += (
            f"💡 **To set a timezone:**\n"
            f"`/set_timezone <timezone_name>`\n\n"
            f"Example: `/set_timezone {results[0]['timezone']}`"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error searching timezones", query=query, error=str(e))
        await update.message.reply_text(
            "❌ An error occurred while searching timezones."
        )


@auth_check
async def my_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's current time and timezone info."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        user_tz = await timezone_service.get_user_timezone(user_id)
        tz_info = await timezone_service.get_timezone_info(user_tz)
        
        if tz_info:
            message = (
                f"🕐 **Your Time Information**\n\n"
                f"🌍 **Timezone:** {tz_info['display_name']}\n"
                f"🕐 **Current Time:** {tz_info['current_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🌐 **UTC Offset:** {tz_info['utc_offset']}\n"
                f"☀️ **Daylight Saving:** {'Yes' if tz_info['is_dst'] else 'No'}\n\n"
                f"💡 Use `/set_timezone` to change your timezone."
            )
        else:
            message = "❌ Unable to get timezone information."
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error showing time info", user_id=user_id, error=str(e))
        await update.message.reply_text(
            "❌ An error occurred while getting time information."
        )


@auth_check
async def remind_me_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a reminder."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text(
            "⏰ **Set a Reminder**\n\n"
            "Usage: `/remind_me <time> <message>`\n\n"
            "**Time Formats:**\n"
            "• `in 30 minutes buy milk`\n"
            "• `in 2 hours call john`\n"
            "• `tomorrow 9am meeting`\n"
            "• `2024-12-25 10:00 christmas party`\n"
            "• `15:30 doctor appointment`\n\n"
            "**Short formats:**\n"
            "• `30m`, `2h`, `1d` for relative times\n"
            "• Times use your timezone (set with `/set_timezone`)",
            parse_mode="Markdown"
        )
        return
    
    text = " ".join(context.args)
    
    # Try to extract time and message
    time_part = ""
    message_part = text
    
    # Look for time patterns at the start
    time_patterns = [
        r"^(in \d+ (?:minutes?|hours?|days?))",
        r"^(\d+[mhd])",
        r"^(\d{1,2}:\d{2}(?:\s*(?:am|pm))?)",
        r"^(\d{1,2}\s*(?:am|pm))",
        r"^(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})",
        r"^(\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})",
        r"^(tomorrow\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            time_part = match.group(1)
            message_part = text[match.end():].strip()
            break
    
    if not time_part:
        await update.message.reply_text(
            "❌ Please specify when to remind you.\n\n"
            "Examples: `in 30 minutes`, `tomorrow 9am`, `15:30`",
            parse_mode="Markdown"
        )
        return
    
    if not message_part:
        await update.message.reply_text(
            "❌ Please specify what to remind you about.\n\n"
            "Example: `/remind_me in 30 minutes buy groceries`"
        )
        return
    
    try:
        reminder_time = parse_time_input(time_part)
        
        if not reminder_time:
            await update.message.reply_text(
                f"❌ Could not understand time format: `{time_part}`\n\n"
                f"Try: `in 30 minutes`, `tomorrow 9am`, or `15:30`",
                parse_mode="Markdown"
            )
            return
        
        if reminder_time <= datetime.now():
            await update.message.reply_text(
                "❌ Reminder time must be in the future!"
            )
            return
        
        # Create the reminder
        reminder_id = await timezone_service.create_reminder(
            user_id=user_id,
            chat_id=chat_id,
            message=message_part,
            reminder_time=reminder_time
        )
        
        if reminder_id:
            # Convert to user's timezone for display
            user_time = await timezone_service.convert_to_user_time(user_id, reminder_time)
            
            message = (
                f"✅ **Reminder Set!**\n\n"
                f"⏰ **When:** {user_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"💬 **Message:** {message_part}\n\n"
                f"🆔 **Reminder ID:** `{reminder_id}`\n"
                f"Use `/cancel_reminder {reminder_id}` to cancel."
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "❌ Failed to create reminder. Please try again."
            )
        
    except Exception as e:
        logger.error("Error creating reminder", user_id=user_id, error=str(e))
        await update.message.reply_text(
            "❌ An error occurred while creating the reminder."
        )


@auth_check
async def list_reminders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List user's reminders."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        reminders = await timezone_service.get_user_reminders(user_id, active_only=True, limit=15)
        
        if not reminders:
            await update.message.reply_text(
                "📋 You have no active reminders.\n\n"
                "Use `/remind_me <time> <message>` to create one!",
                parse_mode="Markdown"
            )
            return
        
        message = f"📋 **Your Active Reminders**\n\n"
        
        for reminder in reminders:
            time_str = reminder["reminder_time"].strftime("%Y-%m-%d %H:%M")
            recurring_str = " 🔄" if reminder["is_recurring"] else ""
            
            message += (
                f"🆔 `{reminder['id']}`{recurring_str}\n"
                f"⏰ {time_str}\n"
                f"💬 {reminder['message'][:60]}{'...' if len(reminder['message']) > 60 else ''}\n\n"
            )
        
        message += (
            f"💡 **Commands:**\n"
            f"• `/cancel_reminder <id>` - Cancel a reminder\n"
            f"• `/remind_me <time> <message>` - Create new reminder"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error listing reminders", user_id=user_id, error=str(e))
        await update.message.reply_text(
            "❌ An error occurred while loading your reminders."
        )


@auth_check
async def cancel_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel a reminder."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🗑️ **Cancel Reminder**\n\n"
            "Usage: `/cancel_reminder <reminder_id>`\n\n"
            "Use `/list_reminders` to see reminder IDs."
        )
        return
    
    try:
        reminder_id = int(context.args[0])
        
        success = await timezone_service.cancel_reminder(user_id, reminder_id)
        
        if success:
            await update.message.reply_text(
                f"✅ Reminder `{reminder_id}` cancelled successfully!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Reminder `{reminder_id}` not found or doesn't belong to you.",
                parse_mode="Markdown"
            )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please provide a valid reminder ID (number).\n\n"
            "Use `/list_reminders` to see your reminder IDs."
        )
    except Exception as e:
        logger.error("Error cancelling reminder", user_id=user_id, error=str(e))
        await update.message.reply_text(
            "❌ An error occurred while cancelling the reminder."
        )


async def handle_timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle timezone-related callback queries."""
    
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        if callback_data.startswith("timezone_set_"):
            timezone_str = callback_data.replace("timezone_set_", "")
            
            success = await timezone_service.set_user_timezone(user_id, timezone_str)
            
            if success:
                tz_info = await timezone_service.get_timezone_info(timezone_str)
                
                message = (
                    f"✅ **Timezone Set!**\n\n"
                    f"🌍 {tz_info['display_name']}\n"
                    f"🕐 {tz_info['current_time'].strftime('%H:%M:%S')}"
                )
                
                await query.edit_message_text(message, parse_mode="Markdown")
            else:
                await query.answer("❌ Failed to set timezone", show_alert=True)
        
        elif callback_data == "timezone_info":
            user_tz = await timezone_service.get_user_timezone(user_id)
            tz_info = await timezone_service.get_timezone_info(user_tz)
            
            if tz_info:
                info_text = (
                    f"🌍 {tz_info['display_name']}\n"
                    f"🕐 {tz_info['current_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🌐 UTC{tz_info['utc_offset']}"
                )
                await query.answer(info_text, show_alert=True)
            else:
                await query.answer("❌ Unable to get timezone info", show_alert=True)
        
        else:
            await query.answer("❓ Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error("Error handling timezone callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)