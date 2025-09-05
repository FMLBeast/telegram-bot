import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from boob_bot.bot_handlers import random_tiddies

async def wen_coco_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    coco_times = [
        now.replace(hour=9, minute=45, second=0, microsecond=0),
        now.replace(hour=15, minute=45, second=0, microsecond=0),
        now.replace(hour=21, minute=45, second=0, microsecond=0),
        now.replace(hour=3, minute=45, second=0, microsecond=0) + timedelta(days=1),
    ]

    # Ensure all times are in the future
    coco_times = [time if time > now else time + timedelta(days=1) for time in coco_times]
    coco_times = sorted(coco_times, key=lambda x: x)

    response = "🕰️ The next 4 Coco times are:\n"
    for time in coco_times[:4]:
        delta = time - now
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        response += f"- {time.strftime('%H:%M')} (in {hours} hours and {minutes} minutes)\n"

    await update.message.reply_text(response)

async def wen_rish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username
    responses = [
        f"💰 {user}, getting rich is just a matter of time... and maybe a bit of luck! 💸",
        f"💵 {user}, remember: wealth is a state of mind! 🧠",
        f"😂 Hey {user}, even if you don't get rich, you're still awesome! 🌟",
        f"🏦 {user}, keep hustling and one day you'll be swimming in cash! 🏊‍♂️",
        f"🚲 {user}, they say money can't buy happiness, but it's more comfortable to cry in a BMW than on a bicycle! 🚗"
    ]
    await update.message.reply_text(random.choice(responses))

async def wen_tits_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await random_tiddies(update, context)

async def wen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    beast_time = now.replace(hour=23, minute=15, second=0, microsecond=0)
    if now > beast_time:
        beast_time += timedelta(days=1)
    delta = beast_time - now
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    response = f"Beasts reload of $95 is due in {hours} hours and {minutes} minutes. Possible starter's kit available for the group if all goes well."
    await update.message.reply_text(response)
