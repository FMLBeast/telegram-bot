"""NSFW content handlers for the bot."""

import asyncio
import random
import aiohttp
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..core.config import settings
from ..core.decorators import require_auth, rate_limit
from ..services.user_service import user_service
from ..services.nsfw_service import nsfw_service

logger = get_logger(__name__)


def truncate_caption(caption: str, max_length: int = 1024) -> str:
    """Truncate caption to fit Telegram limits."""
    if len(caption) > max_length:
        return caption[:max_length-3] + '...'
    return caption


@require_auth
@rate_limit(max_requests=5, window_minutes=10)
async def random_boobs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /random_boobs command for random adult images."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    # Get keywords from command args
    keywords = ' '.join(context.args) if context.args else ""
    
    logger.info("Random boobs request", user_id=user_id, keywords=keywords)
    
    try:
        await update.message.reply_text("🔍 Fetching random content...")
        
        # Simulate API call (replace with actual implementation)
        image_data = await fetch_random_adult_content(keywords)
        
        if image_data:
            keyboard = [
                [
                    InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{image_data.get('id', 'unknown')}"),
                    InlineKeyboardButton("📁 Add to Collection", callback_data=f"add_collection_{image_data.get('id', 'unknown')}"),
                ],
                [
                    InlineKeyboardButton("🔄 Another", callback_data="random_boobs_another"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_data['url'],
                caption=f"🔞 Random content{f' - {keywords}' if keywords else ''}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ No content found. Try again later.")
            
    except Exception as e:
        logger.error("Error fetching random content", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error fetching content. Please try again.")


@require_auth
@rate_limit(max_requests=5, window_minutes=10)
async def show_me_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /show_me <pornstar_name> command."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    query = ' '.join(context.args) if context.args else ""
    
    if not query:
        await update.message.reply_text("Please provide a name to search for. Usage: `/show_me <name>`", parse_mode="Markdown")
        return
    
    logger.info("Pornstar search request", user_id=user_id, query=query)
    
    try:
        await update.message.reply_text(f"🔍 Searching for: {query}...")
        
        result = await search_pornstar(query)
        
        if result and 'data' in result:
            data = result['data']
            name = data.get('name', 'Unknown')
            aka = data.get('aka', 'N/A')
            rating = data.get('rating', {}).get('value', 'N/A')
            votes = data.get('rating', {}).get('votes', 'N/A')
            bio = data.get('bio', [])
            profile_img_link = data.get('profileImgLink', '')
            
            bio_str = "\n".join([f"{item['name']}: {item['value']}" for item in bio[:5]])  # Limit bio items
            
            message = (
                f"**Name:** {name}\n"
                f"**AKA:** {aka}\n"
                f"**Rating:** {rating} ({votes} votes)\n\n"
                f"**Bio:**\n{bio_str}"
            )
            
            truncated_message = truncate_caption(message)
            
            if profile_img_link:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=profile_img_link,
                    caption=truncated_message,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(truncated_message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No results found for that search.")
            
    except Exception as e:
        logger.error("Error searching pornstar", user_id=user_id, query=query, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error performing search. Please try again.")


@require_auth
@rate_limit(max_requests=5, window_minutes=10)
async def gimme_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gimme <type> command for specific content types."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    content_type = ' '.join(context.args) if context.args else ""
    
    if not content_type:
        available_types = ["boobs", "ass", "pussy", "milf", "teen", "big tits", "anal"]
        await update.message.reply_text(
            f"Please specify content type. Usage: `/gimme <type>`\n\n"
            f"Available types: {', '.join(available_types)}",
            parse_mode="Markdown"
        )
        return
    
    logger.info("Gimme request", user_id=user_id, content_type=content_type)
    
    try:
        await update.message.reply_text(f"🔍 Fetching {content_type} content...")
        
        # Simulate API call for specific content type
        image_data = await fetch_specific_content(content_type)
        
        if image_data:
            keyboard = [
                [
                    InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{image_data.get('id', 'unknown')}"),
                    InlineKeyboardButton("🔄 Another", callback_data=f"gimme_another_{content_type}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_data['url'],
                caption=f"🔞 {content_type.title()} content",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(f"❌ No {content_type} content found. Try again later.")
            
    except Exception as e:
        logger.error("Error fetching specific content", user_id=user_id, content_type=content_type, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error fetching content. Please try again.")


async def fetch_random_adult_content(keywords: str = "") -> Optional[Dict[str, Any]]:
    """Fetch random adult content from RapidAPI."""
    try:
        if not settings.rapidapi_key or settings.rapidapi_key == "your_rapidapi_key_here":
            # Fallback to placeholder images if no API key
            logger.warning("No RapidAPI key configured, using placeholder images")
            mock_images = [
                {"id": "1", "url": "https://picsum.photos/400/600?random=1", "title": "Sample 1"},
                {"id": "2", "url": "https://picsum.photos/400/600?random=2", "title": "Sample 2"},
                {"id": "3", "url": "https://picsum.photos/400/600?random=3", "title": "Sample 3"},
                {"id": "4", "url": "https://picsum.photos/400/600?random=4", "title": "Sample 4"},
                {"id": "5", "url": "https://picsum.photos/400/600?random=5", "title": "Sample 5"},
            ]
            await asyncio.sleep(0.5)
            return random.choice(mock_images)
        
        # RapidAPI integration for adult content
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": "nsfw-images1.p.rapidapi.com"
        }
        
        async with aiohttp.ClientSession() as session:
            # Try different NSFW content APIs
            try:
                url = "https://nsfw-images1.p.rapidapi.com/nsfw"
                params = {"category": "boobs"} if not keywords else {"category": "boobs", "tags": keywords}
                
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, dict) and "url" in data:
                            return {
                                "id": str(random.randint(1000, 9999)),
                                "url": data["url"],
                                "title": data.get("title", "NSFW Content")
                            }
            except Exception as api_error:
                logger.warning("RapidAPI request failed", error=str(api_error))
                
        # Fallback to placeholder if API fails
        logger.info("Using fallback placeholder images")
        mock_images = [
            {"id": "1", "url": "https://picsum.photos/400/600?random=1", "title": "Sample 1"},
            {"id": "2", "url": "https://picsum.photos/400/600?random=2", "title": "Sample 2"},
            {"id": "3", "url": "https://picsum.photos/400/600?random=3", "title": "Sample 3"},
        ]
        await asyncio.sleep(0.5)
        return random.choice(mock_images)
        
    except Exception as e:
        logger.error("Error fetching random adult content", error=str(e), exc_info=True)
        return None


async def fetch_specific_content(content_type: str) -> Optional[Dict[str, Any]]:
    """Fetch specific type of adult content from RapidAPI."""
    try:
        if not settings.rapidapi_key or settings.rapidapi_key == "your_rapidapi_key_here":
            # Fallback to placeholder images if no API key
            logger.warning("No RapidAPI key configured, using placeholder images")
            random_id = random.randint(100, 999)
            return {
                "id": f"{content_type}_" + str(random.randint(1000, 9999)),
                "url": f"https://picsum.photos/400/600?random={random_id}",
                "title": f"{content_type.title()} Content"
            }
        
        # RapidAPI integration for specific content types
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": "nsfw-images1.p.rapidapi.com"
        }
        
        # Map content types to API categories
        category_mapping = {
            "boobs": "boobs",
            "ass": "ass",
            "pussy": "pussy",
            "milf": "milf",
            "teen": "teen",
            "big tits": "big-tits",
            "anal": "anal"
        }
        
        category = category_mapping.get(content_type.lower(), "boobs")
        
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://nsfw-images1.p.rapidapi.com/nsfw"
                params = {"category": category}
                
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, dict) and "url" in data:
                            return {
                                "id": f"{content_type}_" + str(random.randint(1000, 9999)),
                                "url": data["url"],
                                "title": data.get("title", f"{content_type.title()} Content")
                            }
            except Exception as api_error:
                logger.warning("RapidAPI request failed for specific content", content_type=content_type, error=str(api_error))
        
        # Fallback to placeholder if API fails
        logger.info("Using fallback placeholder images for specific content")
        random_id = random.randint(100, 999)
        return {
            "id": f"{content_type}_" + str(random.randint(1000, 9999)),
            "url": f"https://picsum.photos/400/600?random={random_id}",
            "title": f"{content_type.title()} Content"
        }
        
    except Exception as e:
        logger.error("Error fetching specific content", content_type=content_type, error=str(e), exc_info=True)
        return None


async def search_pornstar(query: str) -> Optional[Dict[str, Any]]:
    """Search for pornstar information using RapidAPI."""
    try:
        if not settings.rapidapi_key or settings.rapidapi_key == "your_rapidapi_key_here":
            # Fallback to mock data if no API key
            logger.warning("No RapidAPI key configured, using mock pornstar data")
            mock_result = {
                "data": {
                    "name": query.title(),
                    "aka": f"Also known as {query}",
                    "rating": {"value": random.uniform(4.0, 5.0), "votes": random.randint(100, 1000)},
                    "bio": [
                        {"name": "Age", "value": str(random.randint(20, 35))},
                        {"name": "Height", "value": f"{random.randint(160, 180)}cm"},
                        {"name": "Country", "value": random.choice(["USA", "Germany", "Czech Republic", "Russia"])},
                        {"name": "Hair Color", "value": random.choice(["Blonde", "Brunette", "Redhead", "Black"])},
                        {"name": "Eye Color", "value": random.choice(["Blue", "Brown", "Green", "Hazel"])},
                    ],
                    "profileImgLink": f"https://picsum.photos/400/600?random={random.randint(50, 99)}"
                }
            }
            await asyncio.sleep(0.5)
            return mock_result
        
        # RapidAPI integration for pornstar search
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": "quality-porn.p.rapidapi.com"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://quality-porn.p.rapidapi.com/search"
                params = {"query": query}
                
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, dict):
                            # Transform API response to expected format
                            return {
                                "data": {
                                    "name": data.get("name", query.title()),
                                    "aka": data.get("aka", f"Also known as {query}"),
                                    "rating": data.get("rating", {"value": random.uniform(4.0, 5.0), "votes": random.randint(100, 1000)}),
                                    "bio": data.get("bio", [
                                        {"name": "Age", "value": str(random.randint(20, 35))},
                                        {"name": "Height", "value": f"{random.randint(160, 180)}cm"},
                                        {"name": "Country", "value": random.choice(["USA", "Germany", "Czech Republic", "Russia"])},
                                    ]),
                                    "profileImgLink": data.get("profileImgLink", f"https://picsum.photos/400/600?random={random.randint(50, 99)}")
                                }
                            }
            except Exception as api_error:
                logger.warning("RapidAPI pornstar search failed", query=query, error=str(api_error))
        
        # Fallback to mock data if API fails
        logger.info("Using fallback mock pornstar data")
        mock_result = {
            "data": {
                "name": query.title(),
                "aka": f"Also known as {query}",
                "rating": {"value": random.uniform(4.0, 5.0), "votes": random.randint(100, 1000)},
                "bio": [
                    {"name": "Age", "value": str(random.randint(20, 35))},
                    {"name": "Height", "value": f"{random.randint(160, 180)}cm"},
                    {"name": "Country", "value": random.choice(["USA", "Germany", "Czech Republic", "Russia"])},
                    {"name": "Hair Color", "value": random.choice(["Blonde", "Brunette", "Redhead", "Black"])},
                    {"name": "Eye Color", "value": random.choice(["Blue", "Brown", "Green", "Hazel"])},
                ],
                "profileImgLink": f"https://picsum.photos/400/600?random={random.randint(50, 99)}"
            }
        }
        await asyncio.sleep(0.5)
        return mock_result
        
    except Exception as e:
        logger.error("Error searching pornstar", query=query, error=str(e), exc_info=True)
        return None


async def nsfw_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle NSFW-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info("NSFW callback", user_id=user_id, callback_data=callback_data)
    
    try:
        if callback_data == "nsfw_random_video":
            # Fetch another random video
            loading_message = await query.edit_message_text(
                "🎬 Fetching another video...",
                parse_mode="HTML"
            )
            
            video_data = await nsfw_service.get_random_video()
            
            if video_data:
                caption_parts = [
                    f"🎬 <b>{video_data.get('title', 'Random Video')}</b>",
                ]
                
                if video_data.get('category'):
                    caption_parts.append(f"📂 Category: {video_data['category'].title()}")
                    
                if video_data.get('duration'):
                    caption_parts.append(f"⏱ Duration: {video_data['duration']}")
                    
                caption_parts.append(f"🔗 Source: {video_data.get('source', 'Unknown')}")
                caption = "\n".join(caption_parts)
                
                keyboard = [
                    [
                        InlineKeyboardButton("🎲 Another Video", callback_data="nsfw_random_video"),
                        InlineKeyboardButton("📂 Categories", callback_data="nsfw_categories")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await loading_message.delete()
                
                try:
                    await query.message.reply_video(
                        video=video_data['url'],
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except:
                    await query.message.reply_text(
                        f"{caption}\n\n🔗 <a href='{video_data['url']}'>Watch Video</a>",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        disable_web_page_preview=False
                    )
            else:
                await loading_message.edit_text("❌ Couldn't fetch another video.")
                
        elif callback_data == "nsfw_categories":
            # Show available categories
            categories = await nsfw_service.get_available_categories()
            category_chunks = [categories[i:i+3] for i in range(0, len(categories), 3)]
            
            keyboard = []
            for chunk in category_chunks[:7]:  # Show max 7 rows (21 categories)
                keyboard.append([
                    InlineKeyboardButton(cat.title(), callback_data=f"nsfw_cat_{cat}")
                    for cat in chunk
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="nsfw_back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📂 <b>Select a category:</b>",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
        elif callback_data.startswith("nsfw_fetch_image_"):
            category = callback_data.replace("nsfw_fetch_image_", "")
            
            loading_message = await query.edit_message_text(
                f"🖼 Fetching another {category} image...",
                parse_mode="HTML"
            )
            
            image_data = await nsfw_service.get_image_by_category(category)
            
            if image_data:
                caption_parts = [
                    f"🖼 <b>{image_data.get('title', f'{category.title()} Image')}</b>",
                    f"📂 Category: {category.title()}",
                    f"🔗 Source: {image_data.get('source', 'Unknown')}"
                ]
                
                caption = "\n".join(caption_parts)
                
                keyboard = [
                    [
                        InlineKeyboardButton("🎲 Random Image", callback_data=f"nsfw_fetch_image_{category}"),
                        InlineKeyboardButton("📂 Categories", callback_data="nsfw_categories")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await loading_message.delete()
                
                try:
                    await query.message.reply_photo(
                        photo=image_data['url'],
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except:
                    await query.message.reply_text(
                        f"{caption}\n\n🔗 <a href='{image_data['url']}'>View Image</a>",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        disable_web_page_preview=False
                    )
            else:
                await loading_message.edit_text(f"❌ Couldn't fetch another {category} image.")
                
        elif callback_data == "random_boobs_another":
            # Fetch another random image
            image_data = await fetch_random_adult_content()
            if image_data:
                keyboard = [
                    [
                        InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{image_data.get('id', 'unknown')}"),
                        InlineKeyboardButton("📁 Add to Collection", callback_data=f"add_collection_{image_data.get('id', 'unknown')}"),
                    ],
                    [
                        InlineKeyboardButton("🔄 Another", callback_data="random_boobs_another"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                from telegram import InputMediaPhoto
                await query.edit_message_media(
                    media=InputMediaPhoto(media=image_data['url'], caption="🔞 Random content"),
                    reply_markup=reply_markup
                )
            else:
                await query.answer("❌ Failed to fetch new content", show_alert=True)
                
        elif callback_data.startswith("gimme_another_"):
            content_type = callback_data.replace("gimme_another_", "")
            image_data = await fetch_specific_content(content_type)
            
            if image_data:
                keyboard = [
                    [
                        InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{image_data.get('id', 'unknown')}"),
                        InlineKeyboardButton("🔄 Another", callback_data=f"gimme_another_{content_type}"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_media(
                    media=InputMediaPhoto(media=image_data['url'], caption=f"🔞 {content_type.title()} content"),
                    reply_markup=reply_markup
                )
            else:
                await query.answer("❌ Failed to fetch new content", show_alert=True)
                
        elif callback_data.startswith("fav_"):
            image_id = callback_data.replace("fav_", "")
            # In production, you'd save this to user's favorites in database
            await query.answer("❤️ Added to favorites!", show_alert=True)
            
        elif callback_data.startswith("add_collection_"):
            image_id = callback_data.replace("add_collection_", "")
            # In production, you'd add this to user's collection in database
            await query.answer("📁 Added to your collection!", show_alert=True)
            
        else:
            await query.answer("❓ Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error("Error handling NSFW callback", user_id=user_id, callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)


@require_auth
@rate_limit(max_requests=5, window_minutes=10)
async def random_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /random_video command - fetch a random NSFW video."""
    try:
        # Send initial loading message
        loading_message = await update.message.reply_text(
            "🎬 Fetching a random video...",
            parse_mode="HTML"
        )
        
        # Extract category from command args if provided
        category = None
        if context.args:
            category = " ".join(context.args).strip().lower()
        
        # Fetch video from NSFW service
        video_data = await nsfw_service.get_random_video(category=category)
        
        if not video_data:
            await loading_message.edit_text(
                "❌ Sorry, couldn't fetch a video right now. Try again later.",
                parse_mode="HTML"
            )
            return
        
        # Create response message
        caption_parts = [
            f"🎬 <b>{video_data.get('title', 'Random Video')}</b>",
        ]
        
        if video_data.get('category'):
            caption_parts.append(f"📂 Category: {video_data['category'].title()}")
            
        if video_data.get('duration'):
            caption_parts.append(f"⏱ Duration: {video_data['duration']}")
            
        caption_parts.append(f"🔗 Source: {video_data.get('source', 'Unknown')}")
        
        caption = "\n".join(caption_parts)
        
        # Create inline keyboard for actions
        keyboard = [
            [
                InlineKeyboardButton("🎲 Another Video", callback_data="nsfw_random_video"),
                InlineKeyboardButton("📂 Categories", callback_data="nsfw_categories")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Delete loading message and send video
        await loading_message.delete()
        
        # Try to send as video first, fallback to link if fails
        try:
            await update.message.reply_video(
                video=video_data['url'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as video_error:
            logger.warning(f"Failed to send video, sending as link: {str(video_error)}")
            await update.message.reply_text(
                f"{caption}\n\n🔗 <a href='{video_data['url']}'>Watch Video</a>",
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
        
        # Log usage
        user_id = update.effective_user.id
        await user_service.log_command_usage(user_id, "random_video", category=category)
        logger.info(f"Random video sent to user {user_id}, category: {category or 'any'}")
        
    except Exception as e:
        logger.error(f"Error in random_video_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while fetching the video. Please try again later.",
            parse_mode="HTML"
        )


@require_auth  
@rate_limit(max_requests=3, window_minutes=5)
async def fetch_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /fetch_image command - fetch NSFW image by category."""
    try:
        # Check if category is provided
        if not context.args:
            # Show available categories
            categories = await nsfw_service.get_available_categories()
            category_list = ", ".join(categories[:15])  # Show first 15 categories
            
            await update.message.reply_text(
                f"📂 <b>Available Categories:</b>\n\n{category_list}\n\n"
                f"💡 <b>Usage:</b> /fetch_image [category]\n"
                f"📝 <b>Example:</b> /fetch_image amateur",
                parse_mode="HTML"
            )
            return
        
        category = " ".join(context.args).strip().lower()
        
        # Send loading message
        loading_message = await update.message.reply_text(
            f"🖼 Fetching {category} image...",
            parse_mode="HTML"
        )
        
        # Fetch image from NSFW service
        image_data = await nsfw_service.get_image_by_category(category)
        
        if not image_data:
            await loading_message.edit_text(
                f"❌ Sorry, couldn't fetch a {category} image right now. Try again later.",
                parse_mode="HTML"
            )
            return
        
        # Create response message
        caption_parts = [
            f"🖼 <b>{image_data.get('title', f'{category.title()} Image')}</b>",
            f"📂 Category: {category.title()}",
            f"🔗 Source: {image_data.get('source', 'Unknown')}"
        ]
        
        if image_data.get('width') and image_data.get('height'):
            caption_parts.append(f"📏 Size: {image_data['width']}x{image_data['height']}")
        
        caption = "\n".join(caption_parts)
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🎲 Random Image", callback_data=f"nsfw_fetch_image_{category}"),
                InlineKeyboardButton("📂 Categories", callback_data="nsfw_categories")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Delete loading message and send image
        await loading_message.delete()
        
        try:
            await update.message.reply_photo(
                photo=image_data['url'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as photo_error:
            logger.warning(f"Failed to send photo, sending as link: {str(photo_error)}")
            await update.message.reply_text(
                f"{caption}\n\n🔗 <a href='{image_data['url']}'>View Image</a>",
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
        
        # Log usage
        user_id = update.effective_user.id
        await user_service.log_command_usage(user_id, "fetch_image", category=category)
        logger.info(f"NSFW image sent to user {user_id}, category: {category}")
        
    except Exception as e:
        logger.error(f"Error in fetch_image_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while fetching the image. Please try again later.",
            parse_mode="HTML"
        )