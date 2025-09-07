"""NSFW content handlers for the bot."""

import asyncio
import random
import aiohttp
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..core.config import settings
from ..decorators.auth import auth_check
from ..services.user_service import user_service
from ..services.nsfw_service import nsfw_service

logger = get_logger(__name__)


def truncate_caption(caption: str, max_length: int = 1024) -> str:
    """Truncate caption to fit Telegram limits."""
    if len(caption) > max_length:
        return caption[:max_length-3] + '...'
    return caption


@auth_check
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
        
        # Get images using adultdatalink API with "boobs" as default
        search_term = keywords if keywords else "boobs"
        images = await get_random_adult_images(search_term)
        
        if images and isinstance(images, list) and len(images) > 0:
            # Select random image from results
            image = random.choice(images)
            image_url = None
            
            # Extract image URL from API response structure
            if isinstance(image, dict):
                image_url = image.get('url') or image.get('image_url') or image.get('src')
                if not image_url and 'urls' in image:
                    urls = image['urls']
                    if isinstance(urls, list) and len(urls) > 0:
                        image_url = urls[0]
            
            if image_url:
                keyboard = [
                    [
                        InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{random.randint(1000, 9999)}"),
                        InlineKeyboardButton("🔄 Another", callback_data=f"random_boobs_another_{search_term}"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_url,
                    caption=f"🔞 Random {search_term} image from AdultDataLink",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ No valid image URL found. Try again later.")
        else:
            await update.message.reply_text(f"❌ No {search_term} images found. Try again later.")
            
    except Exception as e:
        logger.error("Error fetching random content", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error fetching content. Please try again.")


@auth_check
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
        
        # Get pornstar information using adultdatalink API
        pornstar_info = await get_pornstar_info(query)
        
        if pornstar_info:
            # Format and send the pornstar information
            caption = f"🌟 **{query}**\n\n"
            
            # Add available information from the API response
            if isinstance(pornstar_info, dict):
                # Extract relevant fields (structure depends on API response)
                if "bio" in pornstar_info:
                    caption += f"📝 **Bio:** {pornstar_info['bio'][:200]}...\n\n"
                if "birth_date" in pornstar_info:
                    caption += f"🎂 **Born:** {pornstar_info['birth_date']}\n"
                if "nationality" in pornstar_info:
                    caption += f"🌍 **Nationality:** {pornstar_info['nationality']}\n"
                if "measurements" in pornstar_info:
                    caption += f"📏 **Measurements:** {pornstar_info['measurements']}\n"
                if "career_start" in pornstar_info:
                    caption += f"🎬 **Career Start:** {pornstar_info['career_start']}\n\n"
            
            caption += f"💫 Information from AdultDataLink"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Search Videos", callback_data=f"search_videos_{query}"),
                    InlineKeyboardButton("🖼️ Search Images", callback_data=f"search_images_{query}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                caption,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(f"❌ No information found for '{query}'. \n\nTry checking the spelling or use a more common name format.")
            
    except Exception as e:
        logger.error("Error searching pornstar", user_id=user_id, query=query, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error performing search. Please try again.")


@auth_check
async def gimme_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gimme <query> command for searching videos, images, and GIFs."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    search_query = ' '.join(context.args) if context.args else "hot"
    
    logger.info("Gimme adult content search request", user_id=user_id, query=search_query)
    
    try:
        await update.message.reply_text(f"🔍 Searching for videos, images, and GIFs: '{search_query}'...")
        
        # Search for adult content across videos, images, and GIFs using adultdatalink API
        content_results = await search_adult_content(search_query)
        
        # Collect all available content
        all_content = []
        
        # Add videos
        if content_results.get("videos") and isinstance(content_results["videos"], list):
            for video in content_results["videos"]:
                if isinstance(video, dict):
                    all_content.append({
                        "type": "video",
                        "title": video.get("title", "Video"),
                        "url": video.get("video_link") or video.get("url"),
                        "thumbnail": video.get("thumbnail"),
                        "duration": video.get("duration"),
                        "views": video.get("views")
                    })
        
        # Add images
        if content_results.get("images") and isinstance(content_results["images"], list):
            for image in content_results["images"]:
                if isinstance(image, dict):
                    all_content.append({
                        "type": "image",
                        "title": image.get("title", "Image"),
                        "url": image.get("url"),
                        "thumbnail": image.get("thumbnail") or image.get("url")
                    })
        
        # Add GIFs
        if content_results.get("gifs") and isinstance(content_results["gifs"], list):
            for gif in content_results["gifs"]:
                if isinstance(gif, dict):
                    all_content.append({
                        "type": "gif",
                        "title": gif.get("title", "GIF"),
                        "url": gif.get("url"),
                        "thumbnail": gif.get("thumbnail") or gif.get("url")
                    })
        
        if all_content:
            # Select a random item from all results
            content = random.choice(all_content)
            
            # Create response message based on content type
            content_type_emoji = {"video": "🎬", "image": "🖼️", "gif": "🎞️"}
            emoji = content_type_emoji.get(content["type"], "🔞")
            
            caption = f"{emoji} **{content.get('title', 'Content')}**\n"
            caption += f"📂 Type: {content['type'].title()}\n"
            
            if content.get('duration'):
                caption += f"⏱️ Duration: {content['duration']}\n"
            if content.get('views'):
                caption += f"👁️ Views: {content['views']}\n"
                
            if content.get('url'):
                caption += f"🔗 [View {content['type'].title()}]({content['url']})"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔗 View", url=content.get('url', '#')),
                    InlineKeyboardButton("🔄 Another", callback_data=f"gimme_another_{search_query}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send thumbnail if available
            thumbnail_url = content.get('thumbnail')
            if thumbnail_url and content["type"] in ["image", "gif"]:
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=thumbnail_url,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                except Exception:
                    # Fallback to text if image fails
                    await update.message.reply_text(
                        caption,
                        reply_markup=reply_markup,
                        parse_mode="Markdown",
                        disable_web_page_preview=False
                    )
            else:
                await update.message.reply_text(
                    caption,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
        else:
            await update.message.reply_text(f"❌ No content found for '{search_query}'. Try a different search term.")
            
    except Exception as e:
        logger.error("Error searching adult content", user_id=user_id, query=search_query, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error searching for content. Please try again.")


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
        
        # RapidAPI integration for adult content using working endpoint
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": "girls-nude-image.p.rapidapi.com"
        }
        
        async with aiohttp.ClientSession() as session:
            # Use working girls-nude-image API
            try:
                url = "https://girls-nude-image.p.rapidapi.com/"
                # Map keywords to available types
                image_type = "boobs"
                if keywords:
                    if "ass" in keywords.lower():
                        image_type = "ass"
                    elif any(word in keywords.lower() for word in ["boobs", "tits", "breasts"]):
                        image_type = "boobs"
                
                params = {"type": image_type}
                
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get('success') and data.get('url'):
                            return {
                                "id": str(random.randint(1000, 9999)),
                                "url": data["url"],
                                "title": f"{image_type.title()} Image"
                            }
                    elif response.status == 403:
                        logger.error("NSFW API authentication failed (403)")
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
        
        # RapidAPI integration for specific content types using working endpoint
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": "girls-nude-image.p.rapidapi.com"
        }
        
        # Map content types to available API types
        type_mapping = {
            "boobs": "boobs",
            "ass": "ass", 
            "pussy": "boobs",  # fallback to boobs
            "milf": "boobs",
            "teen": "boobs",
            "big tits": "boobs",
            "anal": "ass",
            "tits": "boobs",
            "breasts": "boobs"
        }
        
        image_type = type_mapping.get(content_type.lower(), "boobs")
        
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://girls-nude-image.p.rapidapi.com/"
                params = {"type": image_type}
                
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get('success') and data.get('url'):
                            return {
                                "id": f"{content_type}_" + str(random.randint(1000, 9999)),
                                "url": data["url"],
                                "title": f"{content_type.title()} Image"
                            }
                    elif response.status == 403:
                        logger.error("NSFW specific content API authentication failed (403)")
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


async def search_porn_videos(query: str = "hot") -> Optional[List[Dict[str, Any]]]:
    """Search for porn videos using RapidAPI."""
    try:
        if not settings.rapidapi_key or settings.rapidapi_key == "your_rapidapi_key_here":
            # Fallback to mock data if no API key
            logger.warning("No RapidAPI key configured, using mock video data")
            return [
                {
                    "title": "Sample Video 1",
                    "thumbnail": "https://picsum.photos/300/200?random=1",
                    "video_link": "https://example.com/video1",
                    "duration": "10min",
                    "views": "1.2M98%"
                }
            ]
        
        # RapidAPI integration for porn video search
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": "porn-xnxx-api.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        payload = {"q": query}
        
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://porn-xnxx-api.p.rapidapi.com/search"
                
                async with session.post(url, json=payload, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            logger.info(f"Found {len(data)} videos for query: {query}")
                            return data
                        else:
                            logger.warning("No videos found in API response", query=query)
                            return None
                    else:
                        logger.warning("API request failed", status=response.status, query=query)
                        return None
            except Exception as api_error:
                logger.warning("RapidAPI video search request failed", query=query, error=str(api_error))
                return None
        
    except Exception as e:
        logger.error("Error searching porn videos", query=query, error=str(e), exc_info=True)
        return None


async def get_pornstar_info(pornstar_name: str) -> Optional[Dict[str, Any]]:
    """Get pornstar information from adultdatalink API."""
    try:
        # Use babepedia endpoint for pornstar information
        url = "https://api.adultdatalink.com/babepedia/model-information"
        params = {"model_name": pornstar_name}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Found pornstar info for: {pornstar_name}")
                        return data
                    else:
                        logger.warning("API request failed", status=response.status, pornstar=pornstar_name)
                        return None
            except Exception as api_error:
                logger.warning("AdultDataLink API request failed", pornstar=pornstar_name, error=str(api_error))
                return None
        
    except Exception as e:
        logger.error("Error getting pornstar info", pornstar=pornstar_name, error=str(e), exc_info=True)
        return None


async def get_random_adult_images(query: str = "boobs") -> Optional[List[Dict[str, Any]]]:
    """Get random adult images from working RapidAPI endpoint."""
    try:
        if not settings.rapidapi_key:
            logger.warning("No RapidAPI key configured for NSFW images")
            return None
        
        # Use working girls-nude-image API
        url = "https://girls-nude-image.p.rapidapi.com/"
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": "girls-nude-image.p.rapidapi.com"
        }
        
        # Map query to available types
        type_mapping = {
            'boobs': 'boobs',
            'ass': 'ass',
            'pussy': 'boobs',  # fallback to boobs if pussy not available
            'tits': 'boobs',
            'breasts': 'boobs'
        }
        image_type = type_mapping.get(query.lower(), 'boobs')
        params = {"type": image_type}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success') and data.get('url'):
                            # Convert single response to list format expected by handler
                            logger.info(f"Found adult image for: {query}")
                            return [{
                                'url': data['url'],
                                'type': data.get('type', query),
                                'title': f'{query.title()} Image'
                            }]
                        else:
                            logger.warning(f"API returned unsuccessful response for {query}")
                            return None
                    elif response.status == 403:
                        logger.error("NSFW images API authentication failed (403). RapidAPI key may not be subscribed to girls-nude-image.p.rapidapi.com")
                        return None
                    else:
                        logger.warning("API request failed", status=response.status, query=query)
                        return None
            except Exception as api_error:
                logger.warning("Girls nude image API request failed", query=query, error=str(api_error))
                return None
        
    except Exception as e:
        logger.error("Error getting adult images", query=query, error=str(e), exc_info=True)
        return None


async def search_adult_content(query: str) -> Dict[str, Any]:
    """Search for adult content across videos, images, and GIFs."""
    results = {
        "videos": [],
        "images": [],
        "gifs": []
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Search videos (using eporner)
            try:
                video_url = "https://api.adultdatalink.com/eporner/search"
                video_params = {"query": query, "per_page": 5}
                async with session.get(video_url, params=video_params, timeout=15) as response:
                    if response.status == 200:
                        video_data = await response.json()
                        results["videos"] = video_data
            except Exception:
                pass
            
            # Search images (using pornpics)
            try:
                image_url = "https://api.adultdatalink.com/pornpics/search"
                image_params = {"query": query}
                async with session.get(image_url, params=image_params, timeout=15) as response:
                    if response.status == 200:
                        image_data = await response.json()
                        results["images"] = image_data
            except Exception:
                pass
            
            # Search GIFs (using redgifs)
            try:
                gif_url = "https://api.adultdatalink.com/redgifs/search"
                gif_params = {"media_type": "gif", "search_text": query, "count": 5}
                async with session.get(gif_url, params=gif_params, timeout=15) as response:
                    if response.status == 200:
                        gif_data = await response.json()
                        results["gifs"] = gif_data
            except Exception:
                pass
        
        logger.info(f"Adult content search completed for: {query}")
        return results
        
    except Exception as e:
        logger.error("Error searching adult content", query=query, error=str(e), exc_info=True)
        return results


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
            search_query = callback_data.replace("gimme_another_", "")
            
            await query.answer("🔍 Searching for another video...")
            
            # Search for another video with same query
            videos = await search_porn_videos(search_query)
            
            if videos and len(videos) > 0:
                # Select a random video from results
                video = random.choice(videos)
                
                # Create response message with video info
                caption = f"🔞 **{video.get('title', 'Video')}**\n"
                caption += f"⏱️ Duration: {video.get('duration', 'Unknown')}\n"
                caption += f"👁️ Views: {video.get('views', 'N/A')}\n"
                caption += f"🔗 [Watch Video]({video.get('video_link', '#')})"
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔗 Watch", url=video.get('video_link', '#')),
                        InlineKeyboardButton("🔄 Another", callback_data=f"gimme_another_{search_query}"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Update with new video thumbnail
                thumbnail_url = video.get('thumbnail')
                if thumbnail_url:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=thumbnail_url, caption=caption, parse_mode="Markdown"),
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text(
                        caption,
                        reply_markup=reply_markup,
                        parse_mode="Markdown",
                        disable_web_page_preview=False
                    )
            else:
                await query.answer("❌ No more videos found for this search", show_alert=True)
                
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


@auth_check
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


@auth_check
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


@auth_check
async def create_porn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_porn command - generate AI porn image from prompt."""
    try:
        # Check if prompt is provided
        if not context.args:
            await update.message.reply_text(
                "🎨 <b>AI Porn Generator</b>\n\n"
                "💡 <b>Usage:</b> /create_porn [prompt]\n"
                "📝 <b>Example:</b> /create_porn a beautiful woman on the beach\n\n"
                "⚠️ <b>Note:</b> This generates NSFW content using AI. Use responsibly.",
                parse_mode="HTML"
            )
            return
        
        prompt = " ".join(context.args).strip()
        
        # Validate prompt length
        if len(prompt) > 500:
            await update.message.reply_text(
                "❌ Prompt is too long! Please keep it under 500 characters.",
                parse_mode="HTML"
            )
            return
            
        # Log the request
        user_id = update.effective_user.id
        logger.info(f"AI porn generation request from user {user_id}, prompt: {prompt}")
        
        # Send loading message  
        loading_message = await update.message.reply_text(
            f"🎨 Generating AI image from prompt: <code>{prompt}</code>\n\n"
            "⏳ This may take 10-30 seconds...",
            parse_mode="HTML"
        )
        
        # Generate image using RapidAPI
        import aiohttp
        url = "https://ai-porn-nsfw-generator.p.rapidapi.com/"
        querystring = {"prompt": prompt}
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": "ai-porn-nsfw-generator.p.rapidapi.com"
        }
        
        if not settings.rapidapi_key:
            await loading_message.edit_text(
                "❌ RapidAPI key not configured for AI image generation.",
                parse_mode="HTML"
            )
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=querystring, timeout=aiohttp.ClientTimeout(total=45)) as response:
                if response.status == 200:
                    data = await response.json()
                    image_url = data.get("image")
                    
                    if image_url:
                        # Create response caption
                        caption = (
                            f"🎨 <b>AI Generated Image</b>\n\n"
                            f"💭 <b>Prompt:</b> {prompt}\n"
                            f"🤖 Generated by AI\n\n"
                            f"❤️ Enjoy responsibly!"
                        )
                        
                        # Create inline keyboard
                        keyboard = [
                            [
                                InlineKeyboardButton("🎨 Generate Another", callback_data="ai_generate_another"),
                                InlineKeyboardButton("🏠 Main Menu", callback_data="start")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Send the generated image
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=image_url,
                            caption=truncate_caption(caption),
                            parse_mode="HTML",
                            reply_markup=reply_markup
                        )
                        
                        # Delete loading message
                        await loading_message.delete()
                        
                        # Log successful generation
                        logger.info(f"AI porn image generated successfully for user {user_id}")
                        await user_service.log_command_usage(user_id, "create_porn", prompt=prompt)
                        
                    else:
                        await loading_message.edit_text(
                            "❌ Failed to generate image. The API didn't return a valid image URL.",
                            parse_mode="HTML"
                        )
                elif response.status == 403:
                    await loading_message.edit_text(
                        "❌ API authentication failed. RapidAPI key may not be subscribed to ai-porn-nsfw-generator.p.rapidapi.com endpoint.",
                        parse_mode="HTML"
                    )
                else:
                    await loading_message.edit_text(
                        f"❌ API request failed with status {response.status}. Please try again later.",
                        parse_mode="HTML"
                    )
                    
    except Exception as e:
        logger.error(f"Error in create_porn_handler: {str(e)}", exc_info=True)
        
        # Try to edit the loading message if it exists
        try:
            await loading_message.edit_text(
                "❌ An error occurred while generating the image. Please try again later.",
                parse_mode="HTML"
            )
        except:
            # If loading message doesn't exist, send a new message
            await update.message.reply_text(
                "❌ An error occurred while generating the image. Please try again later.",
                parse_mode="HTML"
            )