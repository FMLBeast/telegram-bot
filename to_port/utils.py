# boob_bot/utils.py
from telegram import Update
from telegram.ext import ContextTypes
import logging

AUTHORIZED_CHANNELS = [-1002004041727]  # Replace with your actual authorized channel IDs

def is_channel_authorized(channel_id):
    return channel_id in AUTHORIZED_CHANNELS

def channel_authorization(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        channel_id = update.effective_chat.id
        if not is_channel_authorized(channel_id):
            await update.message.reply_text('Not authorized to use this bot in this channel.')
            logging.info(f"Unauthorized access attempt in channel {channel_id}")
            return
        logging.info(f"Authorized access in channel {channel_id}")
        return await func(update, context)
    return wrapper
