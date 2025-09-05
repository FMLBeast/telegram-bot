import json
import pytz
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from boob_bot.bc_handler import process_message_with_gpt
from config.logging_config import logger
from database import db_conn

# Constants for conversation states
ASK_LOCATION, CONFIRM_TIMEZONE = range(2)

# Function to handle /set_timezone command
async def handle_set_timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f"User {user.username} (ID: {user.id}) initiated /set_timezone")
    
    await update.message.reply_text("Please tell me your location (e.g., city, country):")
    context.user_data['user_id'] = user.id
    return ASK_LOCATION

# Function to handle the location input by user
async def handle_set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != context.user_data.get('user_id'):
        return  # Ignore messages from other users during the conversation
    
    location = update.message.text.strip()
    logger.info(f"User provided location: {location}")
    
    try:
        # Request GPT to provide a clean JSON response
        response = await process_message_with_gpt(
            f"Determine the timezone for the location: {location}. "
            "Respond only in JSON format with keys 'timezone' and 'remark'. "
            "Ensure the 'timezone' is a valid timezone string like 'Europe/Brussels' that can be used directly. "
            "The 'remark' should be a short and witty comment about the timezone or location."
        )

        # Clean the response to remove any non-JSON content
        response = response.strip()
        response = response.replace('```', '').replace('json', '').strip()

        # Parse the cleaned JSON response
        data = json.loads(response)
        timezone_name = data.get('timezone')
        witty_remark = data.get('remark')
        
        if not timezone_name:
            raise ValueError("Timezone not found in GPT response.")

        # Validate timezone
        user_timezone = pytz.timezone(timezone_name)
        current_time = datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S')
        
        reply_text = (
            f"{witty_remark}\n"
            f"The current time in {location} is {current_time}. "
            "Is this information correct?"
        )
        
        # Correctly format the callback data to be handled by the CallbackQueryHandler
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=f"confirm_timezone_yes_{timezone_name}_{location}"),
                InlineKeyboardButton("No", callback_data="confirm_timezone_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        return CONFIRM_TIMEZONE
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from GPT for location {location}: {response}")
        await update.message.reply_text("I couldn't understand the response. Please try again.")
        return ASK_LOCATION
    except Exception as e:
        logger.error(f"Error determining timezone for {location}: {e}")
        await update.message.reply_text("I couldn't determine the timezone for that location. Please try again.")
        return ASK_LOCATION

# Function to handle timezone confirmation
async def handle_confirm_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logger.info(f"Callback received: {query.data} from user {query.from_user.username}")

    if query.from_user.id != context.user_data.get('user_id'):
        logger.info("Ignoring callback from different user")
        return  # Ignore callback queries from other users during the conversation

    if query.data.startswith("confirm_timezone_yes_"):
        _, _, timezone_name, location = query.data.split("_", 3)
        user_id = query.from_user.id
        
        # Save to database
        with db_conn:
            db_conn.execute(
                'INSERT OR REPLACE INTO user_timezones (user_id, username, timezone, location) VALUES (?, ?, ?, ?)',
                (user_id, query.from_user.username, timezone_name, location)
            )
            db_conn.commit()
        
        await query.message.reply_text(f"Great! I've saved your timezone as {timezone_name} for {location}.")
        logger.info(f"User {query.from_user.username} (ID: {user_id}) confirmed timezone {timezone_name} for location {location}.")
    elif query.data == "confirm_timezone_no":
        await query.message.reply_text("Let's try again. Please tell me your location:")
        return ASK_LOCATION
    else:
        logger.error(f"Unexpected callback data: {query.data}")

    return ConversationHandler.END

# Function to show current times for all users
async def show_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.message.from_user.username} (ID: {update.message.from_user.id}) requested to show all user times.")
    
    # Fetch all users with timezones from the database
    with db_conn:
        cur = db_conn.cursor()
        cur.execute("SELECT username, timezone, location FROM user_timezones")
        users = cur.fetchall()

    if not users:
        await update.message.reply_text("No users have set their timezone yet.")
        return
    
    response_lines = []
    
    for username, timezone_name, location in users:
        try:
            user_timezone = pytz.timezone(timezone_name)
            current_time = datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S')
            response_lines.append(f"{username} ({location}): {current_time} [{timezone_name}]")
        except Exception as e:
            logger.error(f"Error fetching time for user {username} in timezone {timezone_name}: {e}")
            response_lines.append(f"{username} ({location}): Error fetching time.")
    
    response_text = "\n".join(response_lines)
    await update.message.reply_text(response_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the timezone setting process."""
    await update.message.reply_text("Timezone setting cancelled.")
    return ConversationHandler.END

# Conversation handler for /set_timezone
set_timezone_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('set_timezone', handle_set_timezone_command)],
    states={
        ASK_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_timezone),
            CommandHandler('cancel', cancel)  # Add cancel command
        ],
        CONFIRM_TIMEZONE: [
            CallbackQueryHandler(handle_confirm_timezone, pattern=r"^confirm_timezone_"),
            CommandHandler('cancel', cancel)
        ]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    name="timezone_conversation",
    persistent=True,
    conversation_timeout=300,  # 5 minutes timeout
    per_chat=True,
    per_user=True,
    allow_reentry=True
)