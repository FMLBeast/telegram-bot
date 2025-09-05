from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import random
import os
import httpx
import re
from datetime import datetime
import sqlite3
from database.database import db_conn
from config.logging_config import logger
from telegram.ext import ContextTypes
import asyncio
from telegram.helpers import mention_html
from boob_bot.data_handlers import get_airdrops_and_giveaways
from boob_bot.bc_handler import process_message_with_gpt

async def random_tiddies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    url = 'https://girls-nude-image.p.rapidapi.com/'
    headers = {
        'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
        'X-RapidAPI-Host': 'girls-nude-image.p.rapidapi.com'
    }

    additional_keywords = ' '.join(context.args) if context.args else ''
    search_type = 'boobs ' + additional_keywords if additional_keywords else 'boobs'
    params = {'type': search_type}

    retries = 3
    for attempt in range(retries):
        try:
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            image_url = response.json().get('url')

            if image_url:
                await context.bot.send_photo(chat_id=channel_id, photo=image_url)
                return
            else:
                await update.message.reply_text("No image found. Try again later.")
                return
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        if attempt < retries - 1:
            await asyncio.sleep(2 ** attempt)
        else:
            await update.message.reply_text("Failed to fetch image after several attempts. Please try again later.")

async def tits_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message else update.callback_query.message
    channel_id = message.chat_id
    cur = db_conn.cursor()
    cur.execute('''
        SELECT images.file_path
        FROM user_images
        JOIN images ON user_images.image_id = images.id
        WHERE user_images.user_id = ?
    ''', (channel_id,))
    images = cur.fetchall()

    if images:
        chosen_image = random.choice(images)
        with open(chosen_image[0], 'rb') as img_file:
            await message.reply_photo(photo=img_file, caption="Tits of the day!")
    else:
        await message.reply_text("No images found in the personal collection.")

async def synonym_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().day
    cur = db_conn.cursor()
    cur.execute('SELECT term FROM synonyms')
    synonyms = cur.fetchall()
    if synonyms:
        synonym = synonyms[today % len(synonyms)][0]
        message = f"🌟 *Synonym of the Day* 🌟\n\nToday's word for 'titties': *{synonym}*"
        if update.message:
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.callback_query.message.reply_text(message, parse_mode='Markdown')
    else:
        message = "No synonyms available."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)

async def add_synonym(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        synonym = ' '.join(context.args)
        if not synonym:
            await update.message.reply_text("Please provide a synonym to add.")
            return

        cur = db_conn.cursor()
        cur.execute('INSERT INTO synonyms (term) VALUES (?)', (synonym,))
        db_conn.commit()
        await update.message.reply_text(f"Synonym '{synonym}' added to the database.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("This synonym already exists in the database.")
    except Exception as e:
        logger.error(f"Failed to add the synonym: {e}")
        await update.message.reply_text("Failed to add the synonym.")

async def view_personal_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id if update.message else update.callback_query.from_user.id

    cur = db_conn.cursor()
    cur.execute('''
        SELECT images.file_path
        FROM user_images
        JOIN images ON user_images.image_id = images.id
        WHERE user_images.user_id = ?
    ''', (user_id,))
    images = cur.fetchall()
    if images:
        for img_path in images:
            with open(img_path[0], 'rb') as img_file:
                if update.message:
                    await update.message.reply_photo(photo=img_file)
                else:
                    await update.callback_query.message.reply_photo(photo=img_file)
    else:
        message = "Your personal collection is empty."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)

async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = update.message.chat_id
    message_text = update.message.text
    pattern = re.compile(r"'(.*?)'")
    args = pattern.findall(message_text)

    if len(args) < 2:
        await update.message.reply_text("Usage: /vote 'subject' 'answer1' 'answer2' ['answer3'] ... ['answerN']")
        return

    subject = args[0]
    options = args[1:]

    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO votes (channel_id, subject) VALUES (?, ?)', 
                      (channel_id, subject))
        vote_id = cursor.lastrowid

        for option in options:
            cursor.execute('INSERT INTO vote_options (vote_id, option_text) VALUES (?, ?)', 
                         (vote_id, option))

    keyboard = [[InlineKeyboardButton(f"🔹 {option}", 
                callback_data=f'vote_{vote_id}_{i}') 
                for i, option in enumerate(options)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    vote_message = await update.message.reply_text(
        f"🗳️ *Vote on:* _{subject}_\n\n" + "\n".join([f"🔹 {opt}: *0* votes" for opt in options]),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    context.bot_data[f'vote_message_{vote_id}'] = vote_message.message_id

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith('vote_'):
        return
    
    _, vote_id, option_index = query.data.split('_')
    vote_id = int(vote_id)
    option_index = int(option_index)
    user_id = query.from_user.id

    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_votes WHERE user_id = ? AND vote_id = ?', 
                         (user_id, vote_id))
            
            if cursor.fetchone():
                await query.answer("Already voted!", show_alert=True)
                return

            cursor.execute('SELECT id FROM vote_options WHERE vote_id = ? ORDER BY id', (vote_id,))
            options = cursor.fetchall()
            chosen_option_id = options[option_index][0]

            cursor.execute('INSERT INTO user_votes (user_id, vote_id, option_id) VALUES (?, ?, ?)', 
                         (user_id, vote_id, chosen_option_id))
            cursor.execute('UPDATE vote_options SET votes = votes + 1 WHERE id = ?', 
                         (chosen_option_id,))

            cursor.execute('SELECT subject FROM votes WHERE id = ?', (vote_id,))
            subject = cursor.fetchone()[0]

            cursor.execute('''
                SELECT vo.option_text, vo.votes 
                FROM vote_options vo 
                WHERE vo.vote_id = ? 
                ORDER BY vo.id
            ''', (vote_id,))
            results = cursor.fetchall()

            result_text = f"🗳️ *Vote on:* _{subject}_\n\n"
            result_text += "\n".join([f"🔹 {opt[0]}: *{opt[1]}* votes" for opt in results])

            await query.message.edit_text(
                text=result_text,
                reply_markup=query.message.reply_markup,
                parse_mode='Markdown'
            )
            await query.answer("Vote recorded!")

    except Exception as e:
        logger.error(f"Vote error: {e}")
        await query.answer("Error recording vote", show_alert=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display comprehensive help information about all available commands"""
    help_text = (
        "*Available Commands:*\n\n"
        "*Basic Commands:*\n"
        "/start - Start interacting with the bot\n"
        "/menu - Show the main menu\n"
        "/help - Show this help message\n\n"
        
        "*Image Commands:*\n"
        "/draw_me - Generate an image from prompt\n"
        "/create - Alternative for draw_me\n"
        "/draw_multiple - Create multiple images\n"
        "/edit_image - Edit existing image\n"
        "/random_boobs - Fetch random images\n\n"
        
        "*Collection Commands:*\n"
        "/set_favorite - Set your favorite image\n"
        "/add_to_collection - Add image to collection\n"
        "/add_to_group_collection - Add to group collection\n"
        "/view_personal_collection - View your collection\n"
        "/view_group_collection - View group collection\n\n"
        
        "*Utility Commands:*\n"
        "/vote - Create a new vote\n"
        "/convert - Convert crypto values\n"
        "/mines_multi - Calculate mines multiplier\n"
        "/b2b - Calculate back to back bets\n"
        "/show_times - Show times across timezones\n"
        "/bc - Process query with GPT\n"
        "/ask_gpt - Ask GPT a question\n\n"
        
        "*Social Commands:*\n"
        "/shuffle - Shuffle list of usernames\n"
        "/all - Mention all members\n"
        "/show_airdrops - Show active airdrops\n"
        "/hows - Check user mood\n\n"
        
        "*Other Features:*\n"
        "/casino - Access casino information\n"
        "/list_todos - Show todo list\n"
        "/remark - Add remarks to todos\n"
        "/show_me - Search specific content\n"
        "/gimme - Fetch specific image\n"
        "/porn - Get random movie\n"
        "/relay - Start a relay\n"
        "/join_relay - Join active relay"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def shuffle_the_usernames(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shuffle list of provided usernames"""
    message_text = update.message.text
    # Split the message and exclude the command part
    usernames = message_text.split()[1:]  # Exclude the first element which is the command itself

    # Ensure the list is not empty
    if not usernames:
        await update.message.reply_text("Please provide a list of usernames separated by spaces.")
        return

    # Shuffle the usernames
    shuffled_usernames = random.sample(usernames, len(usernames))
    shuffled_message = "🔀 *Shuffled Usernames* 🔀\n\n" + "\n".join([f"• {username}" for username in shuffled_usernames])
    await update.message.reply_text(shuffled_message, parse_mode='Markdown')