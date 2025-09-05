import asyncio
import openai
import random
import re
import html
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from config.logging_config import logger
from database.database import db_conn  # Assuming db_conn provides a synchronous connection
from config import OPENAI_API_KEY
from concurrent.futures import ThreadPoolExecutor

# Initialize OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Initialize a ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=5)

def escape_markdown(text: str) -> str:
    """
    Escape MarkdownV2 special characters for Telegram.
    Reference: https://core.telegram.org/bots/api#markdownv2-style
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def fetch_messages(cursor, query, params):
    """
    Execute a SQL query to fetch messages.
    """
    cursor.execute(query, params)
    return cursor.fetchall()

async def process_message_with_gpt(message: str) -> str:
    """Process message with GPT API with retry logic."""
    prompt = message
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            completion = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            chatgpt_answer = completion.choices[0].message.content.strip()
            return chatgpt_answer
        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded on attempt {attempt}: {e}")
            if attempt < max_retries:
                backoff_time = (2 ** attempt) + (random.uniform(0, 1))
                logger.info(f"Retrying after {backoff_time:.2f} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error("Max retries reached. Unable to process the message.")
                raise
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error on attempt {attempt}: {e}")
            if attempt < max_retries:
                backoff_time = (2 ** attempt) + (random.uniform(0, 1))
                logger.info(f"Retrying after {backoff_time:.2f} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error("Max retries reached. Unable to process the message.")
                raise
        except Exception as e:
            logger.exception(f"Unexpected error on attempt {attempt}: {e}")
            raise

async def check_user_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check and analyze user mood based on their messages."""
    if not context.args:
        await update.message.reply_text(
            "Please provide a username.\nUsage: /check_user_mood @username or /check_user_mood @everyone"
        )
        return

    username = ' '.join(context.args).strip('@')
    chat_id = update.effective_chat.id

    logger.info(f"Checking mood for: {username} in chat {chat_id}")

    await update.message.reply_text("Fetching messages...")

    try:
        # Obtain a synchronous connection
        conn = db_conn.get_connection()
        cursor = conn.cursor()

        if username.lower() == "everyone":
            query = '''
                SELECT content 
                FROM messages 
                WHERE chat_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 200
            '''
            params = (chat_id,)

            # Fetch messages in a separate thread
            messages = await asyncio.get_event_loop().run_in_executor(
                executor, fetch_messages, cursor, query, params
            )

            if not messages:
                await update.message.reply_text("No messages found in this group.")
                return

            messages_text = "\n".join([msg[0] for msg in messages if msg[0]])
            await update.message.reply_text("Analyzing group mood...")

            mood_update_prompt = (
                "Provide a playful and humorous summary of the following messages. "
                "Keep it short, accurate, and funny:\n\n"
                "Messages:\n" + messages_text
            )

            mood_update = await process_message_with_gpt(mood_update_prompt)
            escaped_mood_update = escape_markdown(mood_update)

            formatted_mood_update = (
                f"*Group Mood Update:*\n\n"
                f"{escaped_mood_update} 😄🎉"
            )

            await update.message.reply_text(
                formatted_mood_update,
                parse_mode='MarkdownV2'
            )
        else:
            # Fetch user_id and actual username
            query_user = '''
                SELECT DISTINCT user_id, username 
                FROM messages 
                WHERE LOWER(username) = LOWER(?) AND chat_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            '''
            params_user = (username, chat_id)

            user_result = await asyncio.get_event_loop().run_in_executor(
                executor, fetch_messages, cursor, query_user, params_user
            )
            user_result = user_result[0] if user_result else None

            if not user_result:
                # Fetch available users
                query_available = '''
                    SELECT DISTINCT username 
                    FROM messages 
                    WHERE chat_id = ? 
                    AND username IS NOT NULL
                    ORDER BY username
                '''
                params_available = (chat_id,)

                available_users = await asyncio.get_event_loop().run_in_executor(
                    executor, fetch_messages, cursor, query_available, params_available
                )
                userlist = ", ".join(f"@{user[0]}" for user in available_users if user[0])

                await update.message.reply_text(
                    f"No messages found for user @{username}.\n\n"
                    f"Available users in this chat: {userlist}"
                )
                return

            user_id, actual_username = user_result[0], user_result[1]

            # Fetch user's messages
            query_messages = '''
                SELECT content 
                FROM messages 
                WHERE user_id = ? AND chat_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 30
            '''
            params_messages = (user_id, chat_id)

            messages = await asyncio.get_event_loop().run_in_executor(
                executor, fetch_messages, cursor, query_messages, params_messages
            )

            if not messages:
                await update.message.reply_text(f"No messages found for user @{actual_username}.")
                return

            messages_text = "\n".join([msg[0] for msg in messages if msg[0].strip()])

            await update.message.reply_text("Analyzing mood...")

            mood_update_prompt = (
                "Analyze the mood of the following messages and provide a short, funny, and well-analyzed mood update without using any HTML tags:\n\n"
                "1. Determine if the user is in the mood to send coin to the group.\n"
                "2. Indicate if the user feels generally ok and like winning.\n"
                "3. Compare the user to an animal based on their characteristics.\n"
                "4. Use quotes from the messages if they are funny.\n\n"
                "Messages:\n" + messages_text
            )

            mood_update = await process_message_with_gpt(mood_update_prompt)
            escaped_mood_update = escape_markdown(mood_update)

            formatted_mood_update = (
                f"*Mood Update for @{escape_markdown(actual_username)}:*\n\n"
                f"{escaped_mood_update} 😆👍"
            )

            await update.message.reply_text(
                formatted_mood_update,
                parse_mode='MarkdownV2'
            )

    except Exception as e:
        logger.exception(f"Error while checking user mood: {e}")
        await update.message.reply_text(f"An error occurred while processing your request: {str(e)}")
    finally:
        # Ensure the cursor and connection are closed
        try:
            cursor.close()
            conn.close()
        except:
            pass
