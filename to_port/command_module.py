import re
import sqlite3
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram_madness.database.database import db_conn
from telegram_madness.config.logging_config import logger  # Import the logging configuration

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

    cur = db_conn.cursor()
    cur.execute('INSERT INTO votes (channel_id, subject) VALUES (?, ?)', (channel_id, subject))
    db_conn.commit()

    vote_id = cur.lastrowid
    for option in options:
        cur.execute('INSERT INTO vote_options (vote_id, option_text) VALUES (?, ?)', (vote_id, option))
    db_conn.commit()

    keyboard = [[InlineKeyboardButton(f"🔹 {option}", callback_data=f'vote_{vote_id}_{i+1}_{channel_id}') for i, option in enumerate(options)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"🗳️ *Vote on:* _{subject}_", reply_markup=reply_markup, parse_mode='Markdown')

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    vote_id = int(data[1])
    chosen_option_index = int(data[2]) - 1
    channel_id = data[-1]

    try:
        user_id = query.from_user.id

        cur = db_conn.cursor()
        cur.execute('SELECT * FROM user_votes WHERE user_id = ? AND vote_id = ?', (user_id, vote_id))
        if cur.fetchone():
            already_voted_message = await query.message.reply_text("You have already voted.")
            await asyncio.sleep(3)
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=already_voted_message.message_id)
            return
        else:
            cur.execute('SELECT id FROM vote_options WHERE vote_id = ?', (vote_id,))
            options = cur.fetchall()
            chosen_option_id = options[chosen_option_index][0]

            cur.execute('INSERT INTO user_votes (user_id, vote_id, option_id) VALUES (?, ?, ?)', (user_id, vote_id, chosen_option_id))
            cur.execute('UPDATE vote_options SET votes = votes + 1 WHERE id = ?', (chosen_option_id,))
            db_conn.commit()

        cur.execute('SELECT subject FROM votes WHERE id = ? AND channel_id = ?', (vote_id, channel_id))
        subject = cur.fetchone()[0]

        cur.execute('SELECT option_text, votes FROM vote_options WHERE vote_id = ?', (vote_id,))
        options = cur.fetchall()
        result_text = f"📊 *Results for:* _{subject}_\n\n"
        result_text += "\n".join([f"🔹 {opt[0]}: *{opt[1]}* votes" for opt in options])

        result_message_id = context.bot_data.get(f'result_message_{vote_id}')
        if result_message_id:
            await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=result_message_id, text=result_text, parse_mode='Markdown')
        else:
            result_message = await query.message.reply_text(result_text, parse_mode='Markdown')
            context.bot_data[f'result_message_{vote_id}'] = result_message.message_id

    except Exception as e:
        print(f"ERROR: {e}")
        await query.message.reply_text("An error occurred while processing your vote. Please try again later.")
