import http.client
import json
import random
import urllib.parse
import aiohttp
import os
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.logging_config import logger
from database.database import db_conn

def truncate_caption(caption, max_length=1024):
    if len(caption) > max_length:
        return caption[:max_length-3] + '...'
    return caption

async def search_pornstar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a name to search for. Usage: /show_me <name>")
        return

    await update.message.reply_text(f"🔍 Searching for pornstar: {query}...")
    result = search_pornstar(query)

    if 'data' in result:
        name = result['data'].get('name', 'Unknown')
        aka = result['data'].get('aka', 'N/A')
        rating = result['data'].get('rating', {}).get('value', 'N/A')
        votes = result['data'].get('rating', {}).get('votes', 'N/A')
        bio = result['data'].get('bio', [])
        profile_img_link = result['data'].get('profileImgLink', 'No image link available')

        bio_str = "\n".join([f"{item['name']}: {item['value']}" for item in bio])

        message = (f"*Name:* {name}\n"
                   f"*AKA:* {aka}\n"
                   f"*Rating:* {rating} {votes}\n\n"
                   f"*Bio:*\n{bio_str}")
        
        truncated_message = truncate_caption(message)
        
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=profile_img_link, caption=truncated_message, parse_mode='Markdown')
    else:
        await update.message.reply_text("No results found.")

def search_pornstar(query):
    conn = http.client.HTTPSConnection("quality-porn.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': "b3d94a48ffmsh77a9d7c5639d202p11fdc7jsn7b4229d8666e",
        'X-RapidAPI-Host': "quality-porn.p.rapidapi.com"
    }

    encoded_query = urllib.parse.quote(query)
    conn.request("GET", f"/pornstar/search?query={encoded_query}&responseProfileImage=1&responseProfileImageBase64=1&responseImages=1&responseImagesBase64=1", headers=headers)

    res = conn.getresponse()
    data = res.read()

    return json.loads(data.decode("utf-8"))

async def random_movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args) or "boobs"
    
    await update.message.reply_text(f"🔍 Searching for videos with query: {query}...")
    search_result = search_random_movie(query)

    if search_result and 'videos' in search_result:
        random_movie = random.choice(search_result['videos'])
        video_key = random_movie.get('view_key', '')
        video_details = get_video_details(video_key)

        if video_details and 'video' in video_details:
            video = video_details['video']
            title = video.get('title', 'No title available')
            duration = video.get('duration', 'No duration available')
            thumbnail = video.get('thumbnail', 'No image available')
            video_url = video.get('video_url', '')

            # Check video size before downloading
            video_size = await get_video_size(video_url)

            if video_size and video_size <= 50 * 1024 * 1024:  # 50 MB in bytes
                video_path = await download_video(video_url)
                if video_path:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=open(video_path, 'rb'), caption=f"{title}\nDuration: {duration}")
                    os.remove(video_path)
                else:
                    await update.message.reply_text("Failed to download video.")
            else:
                # Provide button to play video
                keyboard = [[InlineKeyboardButton("Play in Telegram", url=video_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=thumbnail, caption=f"{title}\nDuration: {duration}", reply_markup=reply_markup)
        else:
            await update.message.reply_text("No video details found.")
    else:
        logger.error(f"No movies found in the response: {search_result}")
        await update.message.reply_text("No movies found.")

def search_random_movie(query):
    conn = http.client.HTTPSConnection("pornhub2.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "b3d94a48ffmsh77a9d7c5639d202p11fdc7jsn7b4229d8666e",
        'x-rapidapi-host': "pornhub2.p.rapidapi.com"
    }

    encoded_query = urllib.parse.quote(query)
    conn.request("GET", f"/v1/search-videos?query={encoded_query}&page=1", headers=headers)

    res = conn.getresponse()
    data = res.read()

    response_data = json.loads(data.decode("utf-8"))
    logger.info(f"Response from API: {response_data}")
    return response_data

def get_video_details(view_key):
    conn = http.client.HTTPSConnection("pornhub2.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "b3d94a48ffmsh77a9d7c5639d202p11fdc7jsn7b4229d8666e",
        'x-rapidapi-host': "pornhub2.p.rapidapi.com"
    }

    conn.request("GET", f"/v1/video-details?view_key={view_key}", headers=headers)

    res = conn.getresponse()
    data = res.read()

    response_data = json.loads(data.decode("utf-8"))
    logger.info(f"Video details from API: {response_data}")
    return response_data

async def get_video_size(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            if response.status == 200:
                return int(response.headers.get('Content-Length', 0))
            else:
                logger.error(f"Failed to get video size: {response.status}")
                return None

async def download_video(url):
    local_filename = url.split('/')[-1]
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(local_filename, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                return local_filename
            else:
                logger.error(f"Failed to download video: {response.status}")
                return None

async def fetch_image(prompt_type='free'):
    url = 'https://girls-nude-image.p.rapidapi.com/'
    params = {'type': prompt_type}
    headers = {
        'X-RapidAPI-Key': 'b3d94a48ffmsh77a9d7c5639d202p11fdc7jsn7b4229d8666e',
        'X-RapidAPI-Host': 'girls-nude-image.p.rapidapi.com'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data['url']
            else:
                logger.error(f"Failed to fetch image: {response.status} - {response.reason}")
                return None

async def increment_cunt_counter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    with db_conn:
        db_conn.execute('INSERT INTO cunt_counter (chat_id, count) VALUES (?, 1) ON CONFLICT(chat_id) DO UPDATE SET count = count + 1', (chat_id,))
        db_conn.commit()

    cur = db_conn.cursor()
    cur.execute('SELECT count FROM cunt_counter WHERE chat_id = ?', (chat_id,))
    count = cur.fetchone()[0]

    image_url = await fetch_image('pussy')
    message = f"Cunt counter - someone or something has been called a cunt {count} times."

    truncated_message = truncate_caption(message)
    
    if image_url:
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=image_url, caption=truncated_message)
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            await context.bot.send_message(chat_id=chat_id, text=truncated_message)
    else:
        await context.bot.send_message(chat_id=chat_id, text=truncated_message)

async def fetch_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt_type = ' '.join(context.args)
    if not prompt_type:
        await update.message.reply_text("Please provide an image type. Usage: /fetch_image <type>")
        return

    await update.message.reply_text(f"🔍 Fetching image with type: {prompt_type}...")
    image_url = await fetch_image(prompt_type)

    if image_url:
        try:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url, caption=f"Image for: {prompt_type}")
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            await update.message.reply_text(f"Image for: {prompt_type}\n{image_url}")
    else:
        await update.message.reply_text("Failed to fetch image.")
