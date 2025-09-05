import openai
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from datetime import datetime, timedelta
import pytz
from database.database import db_conn
from config.logging_config import logger
import random
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import OPENAI_API_KEY
import re
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass
from contextlib import suppress

# Initialize OpenAI GPT
openai.api_key = OPENAI_API_KEY
client = openai.AsyncOpenAI(api_key=openai.api_key)

# Define states for ConversationHandler
SETTING_REMINDER, EVENT_DETAILS, CONFIRMATION, MENTIONS, SELECT_REMINDER, EDIT_DETAILS, EDIT_CONFIRMATION, DELETE_CONFIRMATION = range(8)

# Initialize the scheduler with proper error handling
scheduler = AsyncIOScheduler(
    job_defaults={
        'misfire_grace_time': 3600,
        'coalesce': True,
        'max_instances': 1
    }
)

@dataclass
class ReminderDetails:
    """Data class for storing reminder details with type hints"""
    event_name: str
    date: Optional[str]
    time: str
    timezone: str
    platform: str
    recurrence: Optional[str]

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Markdown V2 formatting"""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', str(text))

def validate_datetime(date: str, time: str, timezone: str) -> bool:
    """Validate date, time and timezone format"""
    try:
        if date:
            datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")
        pytz.timezone(timezone)
        return True
    except (ValueError, pytz.exceptions.UnknownTimeZoneError):
        return False

async def process_message_with_gpt(message: str) -> Dict[str, Any]:
    """Process message with GPT API with improved error handling and retry logic"""
    prompt = (
        f"{message}\n"
        "Please respond in JSON format with keys 'event_name', 'date', 'time', 'timezone', "
        "'platform', and 'recurrence'. If any information is missing, set the value to null."
    )
    max_retries = 5
    base_delay = 1  # Base delay in seconds

    for attempt in range(max_retries):
        try:
            completion = await client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant specializing in parsing event details."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            response = completion.choices[0].message.content.strip()
            
            # Validate JSON structure
            parsed_response = json.loads(response)
            required_keys = {'event_name', 'date', 'time', 'timezone', 'platform', 'recurrence'}
            if not all(key in parsed_response for key in required_keys):
                raise ValueError("Missing required keys in GPT response")
                
            return parsed_response

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON parse error on attempt {attempt + 1}: {e}. Response: {response}")
            if attempt == max_retries - 1:
                raise ValueError("Failed to parse event details properly")
                
        except openai.RateLimitError as e:
            delay = (2 ** attempt * base_delay) + (random.random() * 0.1)
            logger.warning(f"Rate limit hit on attempt {attempt + 1}. Retrying in {delay:.2f} seconds")
            await asyncio.sleep(delay)
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(base_delay * (attempt + 1))
            
        except Exception as e:
            logger.error(f"Unexpected error in GPT processing: {e}")
            raise

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initialize reminder setting process"""
    help_text = (
        "Please describe the event you want to be reminded about. Include:\n\n"
        "• Event name\n"
        "• Date (YYYY-MM-DD)\n"
        "• Time (HH:MM)\n"
        "• Timezone (e.g., UTC, EST)\n"
        "• Platform or location\n"
        "• Recurrence (daily/weekly/monthly, if needed)\n\n"
        "Example: 'Team meeting tomorrow at 15:00 EST on Zoom, recurring weekly'"
    )
    await update.message.reply_text(escape_markdown_v2(help_text), parse_mode='MarkdownV2')
    return EVENT_DETAILS

async def get_event_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process event details from user input"""
    try:
        user_input = update.message.text
        context.user_data['raw_input'] = user_input

        extracted_details = await process_message_with_gpt(user_input)
        context.user_data['event_details'] = extracted_details

        # Validate date/time if provided
        if extracted_details.get('date') and extracted_details.get('time'):
            if not validate_datetime(
                extracted_details['date'],
                extracted_details['time'],
                extracted_details.get('timezone', 'UTC')
            ):
                await update.message.reply_text(
                    "Invalid date, time, or timezone format. Please try again."
                )
                return EVENT_DETAILS

        # Format confirmation message
        confirmation_message = format_reminder_details(extracted_details)
        await update.message.reply_text(confirmation_message, parse_mode='MarkdownV2')
        return CONFIRMATION

    except ValueError as e:
        await update.message.reply_text(
            escape_markdown_v2(f"Error processing details: {str(e)}\nPlease try again."),
            parse_mode='MarkdownV2'
        )
        return EVENT_DETAILS
    except Exception as e:
        logger.error(f"Error in get_event_details: {e}")
        await update.message.reply_text(
            "An error occurred while processing your request. Please try again."
        )
        return ConversationHandler.END

def format_reminder_details(details: Dict[str, Any]) -> str:
    """Format reminder details for display"""
    return escape_markdown_v2(
        "Here are the extracted details for your reminder:\n\n"
        f"*Event Name*: {details.get('event_name', 'N/A')}\n"
        f"*Date*: {details.get('date', 'Not specified')}\n"
        f"*Time*: {details.get('time', 'N/A')}\n"
        f"*Timezone*: {details.get('timezone', 'UTC')}\n"
        f"*Platform/Location*: {details.get('platform', 'N/A')}\n"
        f"*Recurrence*: {details.get('recurrence', 'None')}\n\n"
        "Is this correct? (Yes/No)"
    )

async def confirm_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder confirmation and creation"""
    try:
        if update.message.text.lower() != 'yes':
            await update.message.reply_text(
                escape_markdown_v2("Reminder setup canceled. You can start over with /set_reminder"),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END

        user_id = update.message.from_user.id
        username = update.message.from_user.username
        chat_id = update.message.chat_id
        event_details = context.user_data['event_details']

        # Set default time if needed
        date_time = get_formatted_datetime(event_details)
        reminder_message = format_reminder_message(event_details)

        # Save reminder to database
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reminders (
                    user_id, username, chat_id, reminder_type, date_time,
                    message, timezone, recurrence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, chat_id, 'specific', date_time,
                reminder_message, event_details.get('timezone', 'UTC'),
                event_details.get('recurrence')
            ))
            reminder_id = cursor.lastrowid

        context.user_data['reminder_id'] = reminder_id

        # Schedule the reminder
        try:
            schedule_reminder(
                reminder_id,
                chat_id,
                date_time,
                event_details.get('timezone', 'UTC'),
                reminder_message,
                event_details.get('recurrence'),
                context.bot
            )
        except Exception as e:
            logger.error(f"Error scheduling reminder: {e}")
            # If scheduling fails, delete the reminder from database
            with db_conn.get_connection() as conn:
                conn.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
            raise

        await update.message.reply_text(
            escape_markdown_v2(
                f"Reminder set successfully for {date_time} "
                f"{event_details.get('timezone', 'UTC')}.\n"
                f"Message: {reminder_message}"
            ),
            parse_mode='MarkdownV2'
        )

        # Ask about mentions
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data='yes_mentions'),
                InlineKeyboardButton("No", callback_data='no_mentions')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            escape_markdown_v2("Would you like to add mentions (tag users)?"),
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        return MENTIONS

    except Exception as e:
        logger.error(f"Error in confirm_reminder: {e}")
        await update.message.reply_text(
            escape_markdown_v2(
                "An error occurred while setting up the reminder. "
                "Please try again with /set_reminder"
            ),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

def get_formatted_datetime(event_details: Dict[str, Any]) -> str:
    """Format datetime string from event details"""
    if not event_details.get('date'):
        default_time = datetime.now() + timedelta(minutes=5)
        return default_time.strftime("%Y-%m-%d %H:%M")
    return f"{event_details['date']} {event_details['time']}"

def format_reminder_message(event_details: Dict[str, Any]) -> str:
    """Format reminder message from event details"""
    return (
        f"Event: {event_details.get('event_name', 'N/A')}\n"
        f"Platform/Location: {event_details.get('platform', 'N/A')}\n"
        f"Recurrence: {event_details.get('recurrence', 'None')}"
    )

async def set_mentions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle mention setup"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'yes_mentions':
        await query.edit_message_text(
            escape_markdown_v2(
                "Please provide the usernames to mention "
                "(separated by commas, without @ symbols)"
            ),
            parse_mode='MarkdownV2'
        )
        return MENTIONS
    
    context.user_data['mentions'] = ""
    await query.edit_message_text(
        escape_markdown_v2("No mentions added. Reminder setup completed."),
        parse_mode='MarkdownV2'
    )
    return ConversationHandler.END

async def save_mentions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save mentions for a reminder"""
    try:
        mentions = update.message.text.strip()
        # Validate mentions format
        if not re.match(r'^[\w,\s]+$', mentions):
            await update.message.reply_text(
                escape_markdown_v2(
                    "Invalid username format. Please use only letters, "
                    "numbers, and underscores, separated by commas."
                ),
                parse_mode='MarkdownV2'
            )
            return MENTIONS

        context.user_data['mentions'] = mentions
        
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE reminders SET mentions = ? WHERE id = ?',
                (mentions, context.user_data['reminder_id'])
            )

        await update.message.reply_text(
            escape_markdown_v2(f"Mentions added: {mentions}"),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error saving mentions: {e}")
        await update.message.reply_text(
            escape_markdown_v2("Error saving mentions. Please try again."),
            parse_mode='MarkdownV2'
        )
        return MENTIONS

def schedule_reminder(
    reminder_id: int,
    chat_id: int,
    date_time: str,
    timezone: str,
    message: str,
    recurrence: Optional[str],
    bot: Bot
) -> None:
    """Schedule a reminder with the job scheduler"""
    try:
        tz = pytz.timezone(timezone)
        scheduled_time = tz.localize(datetime.strptime(date_time, "%Y-%m-%d %H:%M"))
        
        if recurrence:
            interval_seconds = parse_recurrence_to_seconds(recurrence)
            trigger = IntervalTrigger(
                seconds=interval_seconds,
                start_date=scheduled_time,
                timezone=tz
            )
        else:
            trigger = DateTrigger(
                run_date=scheduled_time,
                timezone=tz
            )

        scheduler.add_job(
            trigger_reminder,
            trigger=trigger,
            args=[reminder_id, chat_id, message, bot],
            id=str(reminder_id),
            replace_existing=True,
            misfire_grace_time=3600,  # 1 hour grace time
            coalesce=True
        )
        logger.info(f"Scheduled reminder {reminder_id} for {scheduled_time} {timezone}")
    except Exception as e:
        logger.error(f"Error scheduling reminder: {e}")
        raise

def parse_recurrence_to_seconds(recurrence: str) -> int:
    """Convert recurrence pattern to seconds"""
    recurrence = recurrence.lower().strip()
    patterns = {
        'daily': 86400,    # 24 hours
        'weekly': 604800,  # 7 days
        'monthly': 2592000 # 30 days (approximate)
    }
    if recurrence not in patterns:
        raise ValueError(f"Invalid recurrence pattern: {recurrence}")
    return patterns[recurrence]

async def trigger_reminder(reminder_id: int, chat_id: int, message: str, bot: Bot) -> None:
    """Trigger a reminder and send the message"""
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT mentions, recurrence FROM reminders WHERE id = ?',
                (reminder_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                logger.error(f"Reminder {reminder_id} not found in database")
                return
                
            mentions, recurrence = result

        mention_text = ' '.join([f'@{mention.strip()}' for mention in mentions.split(',')]) if mentions else ''
        reminder_text = f"{message}\n{mention_text}"

        await bot.send_message(
            chat_id=chat_id,
            text=escape_markdown_v2(reminder_text),
            parse_mode='MarkdownV2'
        )
        
        # If this is not a recurring reminder, clean it up
        if not recurrence:
            with db_conn.get_connection() as conn:
                conn.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
            with suppress(Exception):
                scheduler.remove_job(str(reminder_id))

    except TelegramError as e:
        logger.error(f"Telegram error while triggering reminder {reminder_id}: {e}")
    except Exception as e:
        logger.error(f"Error triggering reminder {reminder_id}: {e}")

async def edit_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the reminder editing process"""
    chat_id = update.message.chat_id
    
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, message, date_time, timezone 
                FROM reminders 
                WHERE chat_id = ? 
                ORDER BY date_time ASC
            ''', (chat_id,))
            reminders = cursor.fetchall()

        if not reminders:
            await update.message.reply_text(
                escape_markdown_v2("No reminders set."),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END

        keyboard = []
        for reminder in reminders:
            reminder_id, message, date_time, timezone = reminder
            local_time = pytz.timezone(timezone).localize(
                datetime.strptime(date_time, "%Y-%m-%d %H:%M")
            )
            button_text = f"{message} at {local_time.strftime('%Y-%m-%d %H:%M %Z')}"
            keyboard.append([
                InlineKeyboardButton(
                    escape_markdown_v2(button_text),
                    callback_data=f"edit_{reminder_id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            escape_markdown_v2("Select the reminder to edit:"),
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        return SELECT_REMINDER

    except Exception as e:
        logger.error(f"Error in edit_reminder: {e}")
        await update.message.reply_text(
            escape_markdown_v2("An error occurred. Please try again later."),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the reminder deletion process"""
    chat_id = update.message.chat_id
    
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, message, date_time, timezone 
                FROM reminders 
                WHERE chat_id = ? 
                ORDER BY date_time ASC
            ''', (chat_id,))
            reminders = cursor.fetchall()

        if not reminders:
            await update.message.reply_text(
                escape_markdown_v2("No reminders to delete."),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END

        keyboard = []
        for reminder in reminders:
            reminder_id, message, date_time, timezone = reminder
            local_time = pytz.timezone(timezone).localize(
                datetime.strptime(date_time, "%Y-%m-%d %H:%M")
            )
            button_text = f"{message} at {local_time.strftime('%Y-%m-%d %H:%M %Z')}"
            keyboard.append([
                InlineKeyboardButton(
                    escape_markdown_v2(button_text),
                    callback_data=f"delete_{reminder_id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            escape_markdown_v2("Select the reminder to delete:"),
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        return DELETE_CONFIRMATION

    except Exception as e:
        logger.error(f"Error in delete_reminder: {e}")
        await update.message.reply_text(
            escape_markdown_v2("An error occurred. Please try again later."),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder deletion confirmation"""
    query = update.callback_query
    await query.answer()
    
    try:
        reminder_id = int(query.data.split('_')[1])
        
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))

        with suppress(Exception):
            scheduler.remove_job(str(reminder_id))

        await query.edit_message_text(
            escape_markdown_v2("Reminder deleted successfully."),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in confirm_delete: {e}")
        await query.edit_message_text(
            escape_markdown_v2("Error deleting reminder. Please try again."),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation"""
    await update.message.reply_text(
        escape_markdown_v2('Operation canceled.'),
        parse_mode='MarkdownV2'
    )
    return ConversationHandler.END

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all active reminders for the chat"""
    chat_id = update.message.chat_id
    
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, message, date_time, timezone, recurrence, mentions
                FROM reminders 
                WHERE chat_id = ?
                ORDER BY date_time ASC
            ''', (chat_id,))
            reminders = cursor.fetchall()

        if not reminders:
            await update.message.reply_text(
                escape_markdown_v2("No active reminders."),
                parse_mode='MarkdownV2'
            )
            return

        response = "*Active Reminders:*\n\n"
        for reminder in reminders:
            reminder_id, message, date_time, timezone, recurrence, mentions = reminder
            try:
                local_time = pytz.timezone(timezone).localize(
                    datetime.strptime(date_time, "%Y-%m-%d %H:%M")
                )
                response += (
                    f"*ID:* {reminder_id}\n"
                    f"*Event:* {message}\n"
                    f"*Time:* {local_time.strftime('%Y-%m-%d %H:%M %Z')}\n"
                    f"*Recurrence:* {recurrence or 'None'}\n"
                    f"*Mentions:* {mentions or 'None'}\n\n"
                )
            except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
                logger.error(f"Error formatting reminder {reminder_id}: {e}")
                continue

        await update.message.reply_text(
            escape_markdown_v2(response),
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        logger.error(f"Error listing reminders: {e}")
        await update.message.reply_text(
            escape_markdown_v2("Error retrieving reminders. Please try again later."),
            parse_mode='MarkdownV2'
        )
async def select_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder selection for editing"""
    query = update.callback_query
    await query.answer()
    
    try:
        reminder_id = int(query.data.split('_')[1])
        context.user_data['reminder_id'] = reminder_id

        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message, date_time, timezone, mentions, recurrence 
                FROM reminders 
                WHERE id = ?
            ''', (reminder_id,))
            reminder = cursor.fetchone()

        if not reminder:
            await query.edit_message_text(
                escape_markdown_v2("Reminder not found. It may have been deleted."),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END

        message, date_time, timezone, mentions, recurrence = reminder
        dt = datetime.strptime(date_time, "%Y-%m-%d %H:%M")
        
        current_details = (
            "*Current reminder details:*\n\n"
            f"*Message:* {message}\n"
            f"*Date:* {dt.strftime('%Y-%m-%d')}\n"
            f"*Time:* {dt.strftime('%H:%M')}\n"
            f"*Timezone:* {timezone}\n"
            f"*Mentions:* {mentions or 'None'}\n"
            f"*Recurrence:* {recurrence or 'None'}\n\n"
            "Please provide the new details for the reminder in the same format as when creating a new reminder."
        )

        await query.edit_message_text(
            escape_markdown_v2(current_details),
            parse_mode='MarkdownV2'
        )
        return EDIT_DETAILS

    except Exception as e:
        logger.error(f"Error in select_reminder: {e}")
        await query.edit_message_text(
            escape_markdown_v2("An error occurred. Please try again later."),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

async def confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation of reminder edits"""
    if update.message.text.lower() != 'yes':
        await update.message.reply_text(
            escape_markdown_v2("Edit canceled. No changes were made."),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    try:
        reminder_id = context.user_data.get('reminder_id')
        edit_details = context.user_data.get('edit_details')

        if not reminder_id or not edit_details:
            raise ValueError("Missing reminder details")

        event_name = edit_details.get("event_name")
        date = edit_details.get("date")
        time = edit_details.get("time")
        timezone = edit_details.get("timezone")
        platform = edit_details.get("platform")
        recurrence = edit_details.get("recurrence")

        if not all([event_name, time, timezone]):
            raise ValueError("Missing required fields")

        date_time = f"{date} {time}" if date else time
        reminder_message = escape_markdown_v2(
            f"Event: {event_name}\n"
            f"Platform/Location: {platform}\n"
            f"Recurrence: {recurrence or 'None'}"
        )

        # Update the reminder in the database
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reminders 
                SET date_time = ?, message = ?, timezone = ?, recurrence = ? 
                WHERE id = ?
            ''', (date_time, reminder_message, timezone, recurrence, reminder_id))

            # Verify the update was successful
            cursor.execute('SELECT changes()')
            if cursor.fetchone()[0] == 0:
                raise ValueError("Reminder not found")

        # Reschedule the reminder
        schedule_reminder(
            reminder_id, 
            update.effective_chat.id,
            date_time,
            timezone,
            reminder_message,
            recurrence,
            context.bot
        )

        await update.message.reply_text(
            escape_markdown_v2(
                f"Reminder updated successfully!\n\n"
                f"New time: {date_time} {timezone}\n"
                f"Message: {reminder_message}"
            ),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    except ValueError as e:
        logger.warning(f"Validation error in confirm_edit: {e}")
        await update.message.reply_text(
            escape_markdown_v2(f"Error updating reminder: {str(e)}"),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in confirm_edit: {e}")
        await update.message.reply_text(
            escape_markdown_v2(
                "An unexpected error occurred while updating the reminder. "
                "Please try again later."
            ),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
# Create the conversation handler
# Create the conversation handler with proper entry points and fallbacks
reminder_conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler('set_reminder', set_reminder),
        CommandHandler('edit_reminder', edit_reminder),
        CommandHandler('delete_reminder', delete_reminder)
    ],
    states={
        EVENT_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_details),
            CommandHandler('cancel', cancel)
        ],
        CONFIRMATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_reminder),
            CommandHandler('cancel', cancel)
        ],
        MENTIONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_mentions),
            CallbackQueryHandler(set_mentions, pattern='^(yes|no)_mentions$'),
            CommandHandler('cancel', cancel)
        ],
        SELECT_REMINDER: [
            CallbackQueryHandler(select_reminder, pattern=r'^edit_\d+$'),
            CommandHandler('cancel', cancel)
        ],
        EDIT_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_details),
            CommandHandler('cancel', cancel)
        ],
        EDIT_CONFIRMATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_edit),
            CommandHandler('cancel', cancel)
        ],
        DELETE_CONFIRMATION: [
            CallbackQueryHandler(confirm_delete, pattern=r'^delete_\d+$'),
            CommandHandler('cancel', cancel)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        MessageHandler(filters.COMMAND, cancel)  # Handle any other commands
    ],
    name="reminder_conversation",
    persistent=True,
    conversation_timeout=300,  # 5 minutes timeout
    per_chat=True,
    per_user=True,
    per_message=False,  # Not needed for this use case
    allow_reentry=True  # Allow users to restart the conversation
)

# Standalone command handlers that don't need conversation
reminder_handlers = [
    CommandHandler('list_reminders', list_reminders)
]
