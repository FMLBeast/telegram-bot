import os
import io
from openai import OpenAI
from config import OPENAI_API_KEY
from PIL import Image, ImageOps, ImageDraw
from io import BytesIO
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db_conn
from config.logging_config import logger
import requests
import base64

client = OpenAI(api_key=OPENAI_API_KEY)

IMAGE_DIR = "received_images"
GROUP_IMAGE_DIR = "group_images"
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(GROUP_IMAGE_DIR, exist_ok=True)

WAITING_FOR_IMAGE = 0

async def handle_draw_me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_input = ' '.join(context.args)

    if not user_input:
        await update.message.reply_text("Please provide a prompt. Usage: /draw_me <your prompt>")
        return

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM draw_requests WHERE user_id = ? AND timestamp >= ?', 
                      (user_id, today_start))
        count = cursor.fetchone()[0]

        if count >= 25:
            await update.message.reply_text("You've reached the daily limit of 25 images. Try again tomorrow.")
            return

        await update.message.reply_text("Generating image, please wait...")

        try:
            response = client.images.generate(
                prompt=user_input,
                model="dall-e-3",
                n=1,
                size="1024x1024",
                response_format="url",
                quality="standard",
                style="vivid"
            )

            image_url = response.data[0].url
            cursor.execute('INSERT INTO draw_requests (user_id, timestamp) VALUES (?, ?)', 
                         (user_id, datetime.now()))

            await update.message.reply_photo(photo=image_url)
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            await update.message.reply_text(f"Failed to generate image: {e}")

async def handle_draw_multiple_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = ' '.join(context.args)
    
    if not user_input:
        await update.message.reply_text("Please provide a prompt. Usage: /draw_multiple <your prompt>")
        return

    await update.message.reply_text("Generating images, please wait...")

    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        data = {
            "prompt": user_input,
            "model": "dall-e-2",
            "n": 3,
            "size": "1024x1024",
            "response_format": "url"
        }

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            response_data = response.json()
            for image_data in response_data['data']:
                await update.message.reply_photo(photo=image_data['url'])
            await update.message.reply_text("Images generated successfully!")
        else:
            await update.message.reply_text(f"Generation failed: {response.status_code} - {response.text}")
    except Exception as e:
        await update.message.reply_text(f"Error occurred: {e}")

async def handle_edit_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Reply to an image with /edit_image <your prompt>")
        return

    user_input = ' '.join(context.args)
    
    if not user_input:
        await update.message.reply_text("Provide editing prompt. Usage: /edit_image <your prompt>")
        return

    await update.message.reply_text("Editing image, please wait...")

    try:
        photo_file = await update.message.reply_to_message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(image_bytes))

        if image.width != image.height:
            image = ImageOps.fit(image, (max(image.width, image.height), max(image.width, image.height)), Image.ANTIALIAS)

        image = image.convert('RGBA')
        if not image.info.get("transparency", False):
            transparent_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
            image = Image.alpha_composite(transparent_layer, image)

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_bytes = buffered.getvalue()

        if len(image_bytes) > 4 * 1024 * 1024:
            image.thumbnail((1024, 1024))
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_bytes = buffered.getvalue()

        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        files = {"image": ("image.png", image_bytes, "image/png")}
        data = {
            "prompt": user_input,
            "model": "dall-e-2",
            "n": 1,
            "size": "1024x1024",
            "response_format": "url"
        }

        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers=headers,
            files=files,
            data=data
        )

        if response.status_code == 200:
            image_url = response.json()['data'][0]['url']
            await update.message.reply_photo(photo=image_url)
            await update.message.reply_text("Image edited successfully!")
        else:
            await update.message.reply_text(f"Edit failed: {response.status_code} - {response.text}")
    except Exception as e:
        await update.message.reply_text(f"Error occurred: {e}")

async def handle_image_variation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'show_variations' not in context.user_data:
        await update.message.reply_text("Upload an image first.")
        return

    n_variations = context.user_data.get('n', 1)
    size = context.user_data.get('size', '1024x1024')
    model = context.user_data.get('model', 'dall-e-2')
    response_format = context.user_data.get('response_format', 'url')

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        files = {"image": ("image.png", photo_bytes, "image/png")}
        data = {"n": n_variations, "size": size, "model": model}

        response = requests.post(
            "https://api.openai.com/v1/images/variations",
            headers=headers,
            files=files,
            data=data
        )

        if response.status_code == 200:
            response_data = response.json()
            for image_data in response_data['data']:
                if response_format == 'url':
                    await update.message.reply_photo(photo=image_data['url'])
                else:
                    image_b64 = image_data['b64_json']
                    image = Image.open(BytesIO(base64.b64decode(image_b64)))
                    buffered = BytesIO()
                    image.save(buffered, format="PNG")
                    await update.message.reply_photo(photo=buffered.getvalue())
        else:
            await update.message.reply_text(f"Variation failed: {response.status_code} - {response.text}")
    except Exception as e:
        await update.message.reply_text(f"Error occurred: {e}")

async def set_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id if update.message else update.callback_query.from_user.id
    message = update.message if update.message else update.callback_query.message

    if message.reply_to_message and message.reply_to_message.photo:
        photo_file = await message.reply_to_message.photo[-1].get_file()
    elif message.photo:
        photo_file = await message.photo[-1].get_file()
    else:
        await message.reply_text("Send a photo to set as favorite.")
        return

    photo_file_path = os.path.join(IMAGE_DIR, f"{photo_file.file_id}.jpg")
    os.makedirs(os.path.dirname(photo_file_path), exist_ok=True)
    await photo_file.download_to_drive(photo_file_path)

    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO images (file_path) VALUES (?)', (photo_file_path,))
        image_id = cursor.lastrowid if cursor.lastrowid != 0 else cursor.execute(
            'SELECT id FROM images WHERE file_path = ?', (photo_file_path,)
        ).fetchone()[0]
        cursor.execute('REPLACE INTO users (id, favorite_image_id) VALUES (?, ?)', 
                      (user_id, image_id))
        cursor.execute('INSERT OR IGNORE INTO user_images (user_id, image_id) VALUES (?, ?)', 
                      (user_id, image_id))

    await update.message.reply_text("Favorite image set and added to collection.")
    context.user_data.pop('set_favorite', None)

async def add_to_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_to_message = update.message.reply_to_message

    if not reply_to_message or not reply_to_message.photo:
        await update.message.reply_text("Reply to an image to add to collection.")
        return

    photo_file = await reply_to_message.photo[-1].get_file()
    photo_file_path = os.path.join(IMAGE_DIR, f"{photo_file.file_id}.jpg")
    os.makedirs(os.path.dirname(photo_file_path), exist_ok=True)
    await photo_file.download_to_drive(photo_file_path)

    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO images (file_path) VALUES (?)', (photo_file_path,))
        image_id = cursor.lastrowid
        cursor.execute('INSERT OR IGNORE INTO user_images (user_id, image_id) VALUES (?, ?)', 
                      (update.message.chat_id, image_id))

    await update.message.reply_text("Image added to personal collection.")
    context.user_data.pop('add_to_collection', None)

async def add_to_group_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_to_message = update.message.reply_to_message
    if not reply_to_message or not reply_to_message.photo:
        await update.message.reply_text("Reply to an image to add to group collection.")
        return

    photo_file = await reply_to_message.photo[-1].get_file()
    photo_file_path = os.path.join(GROUP_IMAGE_DIR, f"{photo_file.file_id}.jpg")
    os.makedirs(os.path.dirname(photo_file_path), exist_ok=True)
    await photo_file.download_to_drive(photo_file_path)

    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO images (file_path) VALUES (?)', (photo_file_path,))
        image_id = cursor.lastrowid
        cursor.execute('INSERT OR IGNORE INTO group_images (channel_id, image_id) VALUES (?, ?)', 
                      (update.message.chat_id, image_id))

    await update.message.reply_text("Image added to group collection.")
    context.user_data.pop('add_to_group_collection', None)

async def view_personal_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT images.file_path FROM images
            INNER JOIN user_images ON images.id = user_images.image_id
            WHERE user_images.user_id = ?
        ''', (user_id,))
        images = cursor.fetchall()

    if images:
        for image in images:
            with open(image[0], 'rb') as photo:
                await update.message.reply_photo(photo=photo)
    else:
        await update.message.reply_text("No images in personal collection.")

async def view_group_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = update.message.chat_id
    
    with db_conn.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT images.file_path FROM images
            INNER JOIN group_images ON images.id = group_images.image_id
            WHERE group_images.channel_id = ?
        ''', (channel_id,))
        images = cursor.fetchall()

    if images:
        for image in images:
            with open(image[0], 'rb') as photo:
                await update.message.reply_photo(photo=photo)
    else:
        await update.message.reply_text("No images in group collection.")