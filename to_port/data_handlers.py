import os
import re
import asyncio
import re
from datetime import datetime
from collections import defaultdict
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel, MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.users import GetFullUserRequest
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, PHONE_NUMBER
from config.logging_config import logger
from database.database import db_conn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
from config import RAPIDAPI_KEY
from telegram import Update
from telegram.ext import ContextTypes
MEDIA_DIR = 'telegram_media'
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

def escape_markdown(text):
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

async def fetch_username_from_db(user_id):
    try:
        cursor = db_conn.execute('SELECT username FROM messages WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Failed to fetch username for user_id {user_id} from database: {e}")
        return None

async def fetch_username_from_api(client, user_id):
    try:
        user_full = await client(GetFullUserRequest(user_id))
        user = user_full.user
        return user.username if user.username else 'Unknown'
    except Exception as e:
        logger.error(f"Failed to fetch username for user_id {user_id} from API: {e}")
        return 'Unknown'

async def save_media(client, message):
    media_path = None
    if isinstance(message.media, MessageMediaPhoto):
        media_path = await client.download_media(message, file=os.path.join(MEDIA_DIR, f"{message.id}.jpg"))
    elif isinstance(message.media, MessageMediaDocument):
        media_path = await client.download_media(message, file=os.path.join(MEDIA_DIR, f"{message.id}"))
    return media_path

async def insert_messages_into_db(messages, client, channel_id, channel_name):
    with db_conn:
        for message in messages:
            try:
                user_id = message.from_id.user_id if hasattr(message.from_id, 'user_id') else message.from_id
                content = message.message or ''
                date = message.date.strftime('%Y-%m-%d %H:%M:%S')

                # Check for duplicate messages
                cursor = db_conn.execute('SELECT 1 FROM messages WHERE user_id = ? AND content = ? AND timestamp = ?', (user_id, content, date))
                if cursor.fetchone():
                    logger.info(f"Duplicate message from user {user_id} with content '{content}' at {date}. Skipping insertion.")
                    continue

                username = message.from_id.username if hasattr(message.from_id, 'username') else None
                if not username:
                    username = await fetch_username_from_db(user_id)
                    if not username:
                        username = await fetch_username_from_api(client, user_id)

                media_path = None
                media_type = None
                if message.media:
                    media_path = await save_media(client, message)
                    if isinstance(message.media, MessageMediaPhoto):
                        media_type = 'photo'
                    elif isinstance(message.media, MessageMediaDocument):
                        media_type = 'document'

                logger.info(f"Inserting message from user {user_id} with content: {content}")

                db_conn.execute('''
                    INSERT INTO messages (user_id, username, chat_id, chat_name, content, media, media_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    username,
                    channel_id,
                    channel_name,
                    content,
                    media_path,
                    media_type,
                    date
                ))
                db_conn.commit()
            except Exception as e:
                logger.error(f"Failed to insert message from user {user_id} with content '{content}': {e}")

async def fetch_channel_messages(client, channel_id, channel_name, total_count_limit=22000):
    await client.start(PHONE_NUMBER)

    try:
        entity = await client.get_entity(PeerChannel(channel_id))
        
        cursor = db_conn.execute('SELECT MAX(timestamp) FROM messages WHERE chat_id = ?', (channel_id,))
        last_message_date = cursor.fetchone()[0] or "1970-01-01 00:00:00"
        
        offset_id = 0
        limit = 200
        total_messages = 0
        sleep_interval = 5

        while total_messages < total_count_limit:
            try:
                logger.info(f"Fetching messages with offset_id {offset_id} and limit {limit}")
                history = await client(GetHistoryRequest(
                    peer=entity,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                if not history.messages:
                    logger.info("No more messages found.")
                    break

                messages = [msg for msg in history.messages if msg.date.strftime('%Y-%m-%d %H:%M:%S') > last_message_date]
                if not messages:
                    logger.info("No new messages found.")
                    break

                await insert_messages_into_db(messages, client, channel_id, channel_name)

                offset_id = messages[-1].id
                total_messages += len(messages)

                logger.info(f"Fetched {len(messages)} messages, total so far: {total_messages}")

                if total_messages >= total_count_limit:
                    break

                logger.info(f"Sleeping for {sleep_interval} seconds")
                await asyncio.sleep(sleep_interval)

            except FloodWaitError as e:
                logger.warning(f"Flood wait error: sleeping for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                sleep_interval = min(sleep_interval * 2, 60)

        logger.info(f"Fetched {total_messages} messages from channel {channel_id}")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.disconnect()

async def synchronize_all_chats():
    client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start(PHONE_NUMBER)
    
    channels = db_conn.execute('SELECT chat_id, chat_name FROM channels').fetchall()
    for channel_id, channel_name in channels:
        logger.info(f"Starting synchronization for channel {channel_name} ({channel_id})")
        await fetch_channel_messages(client, channel_id, channel_name)
        logger.info(f"Finished synchronization for channel {channel_name} ({channel_id})")
    
    await client.disconnect()

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(synchronize_all_chats, 'interval', minutes=15)
    scheduler.start()

if __name__ == "__main__":
    start_scheduler()
    asyncio.get_event_loop().run_forever()

async def fetch_cctip_stats(chat_id):
    try:
        cursor = db_conn.execute('''
            SELECT username, content 
            FROM messages 
            WHERE chat_id = ? AND username = 'cctip_bot'
            ORDER BY timestamp DESC
        ''', (chat_id,))
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch cctip stats: {e}")
        return []


def get_airdrops_and_giveaways(chat_id):
    try:
        cursor = db_conn.execute('''
            SELECT timestamp, username, content 
            FROM messages 
            WHERE chat_id = ? AND username = 'cctip_bot'
            ORDER BY timestamp DESC
        ''', (chat_id,))

        airdrops_and_giveaways = []

        airdrop_pattern = re.compile(
            r"(?P<sender>\w+)\s+Created an airdrop in\s+(?P<amount>\d+(\.\d+)?)\s+(?P<currency>\w+)\s+for\s+(?P<numberofusers>\d+)\s+users\.\nSend Grab to grab it!"
        )
        giveaway_pattern = re.compile(
            r"(?P<sender>\w+)\s+Created a giveaway in\s+(?P<amount>\d+(\.\d+)?)\s+(?P<currency>\w+)\s+for\s+(?P<numberofusers>\d+)\s+users!"
        )

        for row in cursor.fetchall():
            timestamp, username, content = row

            match = airdrop_pattern.search(content) or giveaway_pattern.search(content)
            if match:
                sender = match.group('sender')
                amount = match.group('amount')
                currency = match.group('currency')
                numberofusers = match.group('numberofusers')
                
                # Extract hashtag if present
                hashtag = ''
                hashtag_match = re.search(r'#\w+', content)
                if hashtag_match:
                    hashtag = hashtag_match.group(0)
                
                airdrops_and_giveaways.append({
                    'date': timestamp,
                    'sender': sender,
                    'amount': amount,
                    'currency': currency,
                    'numberofusers': numberofusers,
                    'hashtag': hashtag
                })

        # Format and decorate the response for airdrops and giveaways
        decorated_list = "<b>Date - Sender - Amount - Currency - Number of Users - Hashtag</b>\n"
        decorated_list += "-" * 60 + "\n"
        
        for entry in airdrops_and_giveaways:
            decorated_list += f"{entry['date']} - {entry['sender']} - {entry['amount']} {entry['currency']} - {entry['numberofusers']} users - {entry['hashtag']}\n"

        return decorated_list

    except Exception as e:
        logger.error(f"Failed to fetch and parse airdrop and giveaway messages: {e}")
        return None

async def airdrops_and_giveaways_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    result = get_airdrops_and_giveaways(chat_id)
    if result:
        await update.message.reply_text(result, parse_mode="HTML")
    else:
        await update.message.reply_text("No airdrop or giveaway messages found or failed to fetch messages.")