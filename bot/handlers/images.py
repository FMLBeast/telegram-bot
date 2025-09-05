"""Image generation and management handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.image_service import image_service
from ..decorators.auth import auth_check
from ..core.exceptions import APIError

logger = get_logger(__name__)


@auth_check
async def draw_me_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a single image from text prompt."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    prompt = " ".join(context.args) if context.args else ""
    
    if not prompt:
        await update.message.reply_text(
            "🎨 Please provide a prompt for image generation.\n\n"
            "Usage: `/draw_me <your prompt>`\n"
            "Example: `/draw_me a cute robot in a garden`",
            parse_mode="Markdown"
        )
        return
    
    # Show typing action
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_photo"
    )
    
    try:
        # Check user stats first
        stats = await image_service.get_user_stats(user_id)
        
        if stats["remaining_today"] <= 0:
            await update.message.reply_text(
                f"🚫 You've reached your daily limit of {stats['daily_limit']} images.\n"
                f"Generated today: {stats['today_images']}/{stats['daily_limit']}\n"
                "Try again tomorrow! ⏰"
            )
            return
        
        # Show generation message
        status_message = await update.message.reply_text(
            f"🎨 Generating image...\n"
            f"Remaining today: {stats['remaining_today']}/{stats['daily_limit']}"
        )
        
        # Generate image
        result = await image_service.generate_image(
            user_id=user_id,
            prompt=prompt,
            size="1024x1024",
            quality="standard"
        )
        
        if not result:
            await status_message.edit_text(
                "❌ Failed to generate image. Please try again."
            )
            return
        
        # Create keyboard for image actions
        keyboard = [
            [
                InlineKeyboardButton("⭐ Favorite", callback_data=f"fav_{result['id']}"),
                InlineKeyboardButton("📁 Add to Collection", callback_data=f"collect_{result['id']}"),
            ],
            [
                InlineKeyboardButton("🔄 Generate Variation", callback_data=f"vary_{result['id']}"),
                InlineKeyboardButton("📊 My Stats", callback_data=f"stats_{user_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send image
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=result["url"],
            caption=(
                f"🎨 **Generated Image**\n"
                f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
                f"Size: {result['size']} | Quality: {result['quality']}"
            ),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Delete status message
        await status_message.delete()
        
        logger.info(
            "Image generated and sent",
            user_id=user_id,
            image_id=result["id"],
            prompt_length=len(prompt)
        )
        
    except APIError as e:
        await status_message.edit_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error("Error in draw_me_handler", user_id=user_id, error=str(e), exc_info=True)
        await status_message.edit_text(
            "❌ An unexpected error occurred. Please try again."
        )


@auth_check
async def draw_multiple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate multiple images from text prompt."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    # Parse arguments
    if not context.args:
        await update.message.reply_text(
            "🎨 Please provide a prompt for multiple image generation.\n\n"
            "Usage: `/draw_multiple <count> <prompt>`\n"
            "Example: `/draw_multiple 3 a cute robot`\n\n"
            "Count can be 2-4 images."
        )
        return
    
    try:
        count = int(context.args[0])
        if count < 2 or count > 4:
            raise ValueError("Count must be between 2 and 4")
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Please provide a valid count (2-4) as the first argument.\n\n"
            "Usage: `/draw_multiple <count> <prompt>`\n"
            "Example: `/draw_multiple 3 a cute robot`"
        )
        return
    
    prompt = " ".join(context.args[1:])
    if not prompt:
        await update.message.reply_text(
            "❌ Please provide a prompt after the count.\n\n"
            "Usage: `/draw_multiple <count> <prompt>`\n"
            "Example: `/draw_multiple 3 a cute robot`"
        )
        return
    
    # Show typing action
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_photo"
    )
    
    try:
        # Check user stats
        stats = await image_service.get_user_stats(user_id)
        
        if stats["remaining_today"] < count:
            await update.message.reply_text(
                f"🚫 Not enough daily quota remaining.\n"
                f"Requested: {count} images\n"
                f"Remaining today: {stats['remaining_today']}/{stats['daily_limit']}\n"
                "Try again tomorrow! ⏰"
            )
            return
        
        # Show generation message
        status_message = await update.message.reply_text(
            f"🎨 Generating {count} images...\n"
            f"This may take a moment. Please wait..."
        )
        
        # Generate multiple images
        results = await image_service.generate_multiple_images(
            user_id=user_id,
            prompt=prompt,
            count=count,
            size="1024x1024",
            quality="standard"
        )
        
        if not results:
            await status_message.edit_text(
                "❌ Failed to generate images. Please try again."
            )
            return
        
        await status_message.edit_text(
            f"✅ Generated {len(results)} images! Sending them now..."
        )
        
        # Send each image
        for i, result in enumerate(results, 1):
            keyboard = [
                [
                    InlineKeyboardButton("⭐ Favorite", callback_data=f"fav_{result['id']}"),
                    InlineKeyboardButton("📁 Collection", callback_data=f"collect_{result['id']}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=result["url"],
                caption=(
                    f"🎨 **Image {i}/{len(results)}**\n"
                    f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
                ),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
        # Delete status message
        await status_message.delete()
        
        logger.info(
            "Multiple images generated",
            user_id=user_id,
            count=len(results),
            prompt_length=len(prompt)
        )
        
    except APIError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error("Error in draw_multiple_handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An unexpected error occurred. Please try again."
        )


@auth_check
async def view_personal_collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View user's personal image collection."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        images = await image_service.get_user_images(user_id, limit=20)
        
        if not images:
            await update.message.reply_text(
                "📁 Your image collection is empty.\n"
                "Generate some images with `/draw_me <prompt>` to get started!"
            )
            return
        
        stats = await image_service.get_user_stats(user_id)
        
        message = (
            f"🖼️ **Your Image Collection**\n\n"
            f"📊 **Stats:**\n"
            f"• Total images: {stats['total_images']}\n"
            f"• Favorites: {stats['favorites_count']}\n"
            f"• Today: {stats['today_images']}/{stats['daily_limit']}\n"
            f"• Remaining: {stats['remaining_today']}\n\n"
            f"**Recent Images ({len(images)}):**\n"
        )
        
        for i, img in enumerate(images[:10], 1):
            status = "⭐" if img["is_favorite"] else "🖼️"
            prompt = img["prompt"][:50] + "..." if len(img["prompt"]) > 50 else img["prompt"]
            message += f"{status} {i}. {prompt}\n"
        
        if len(images) > 10:
            message += f"\n... and {len(images) - 10} more"
        
        keyboard = [
            [
                InlineKeyboardButton("⭐ View Favorites", callback_data=f"favs_{user_id}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"collection_{user_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error("Error viewing collection", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading your collection."
        )


@auth_check
async def view_group_collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View group's shared image collection."""
    
    if not update.message or not update.effective_chat:
        return
    
    chat_id = update.effective_chat.id
    
    # Only work in group chats
    if chat_id > 0:
        await update.message.reply_text(
            "📁 Group collections are only available in group chats."
        )
        return
    
    try:
        images = await image_service.get_collection_images(chat_id=chat_id, limit=15)
        
        if not images:
            await update.message.reply_text(
                "📁 The group collection is empty.\n"
                "Members can add images using the 📁 button on generated images!"
            )
            return
        
        message = (
            f"🖼️ **Group Image Collection**\n\n"
            f"**Shared Images ({len(images)}):**\n"
        )
        
        for i, img in enumerate(images[:10], 1):
            prompt = img["prompt"][:40] + "..." if len(img["prompt"]) > 40 else img["prompt"]
            message += f"🖼️ {i}. {prompt}\n"
        
        if len(images) > 10:
            message += f"\n... and {len(images) - 10} more"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"group_collection_{chat_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error("Error viewing group collection", chat_id=chat_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading the group collection."
        )


@auth_check
async def image_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's image generation statistics."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        stats = await image_service.get_user_stats(user_id)
        
        # Progress bar for daily usage
        used_pct = (stats["today_images"] / stats["daily_limit"]) * 100
        bar_length = 20
        filled_length = int(bar_length * used_pct // 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        message = (
            f"📊 **Your Image Statistics**\n\n"
            f"🎨 **Total Images Generated:** {stats['total_images']}\n"
            f"⭐ **Favorites:** {stats['favorites_count']}\n\n"
            f"📅 **Today's Usage:**\n"
            f"{bar} {stats['today_images']}/{stats['daily_limit']}\n"
            f"Remaining: {stats['remaining_today']} images\n\n"
            f"💡 **Tip:** Daily limits reset at midnight UTC"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error showing stats", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading your statistics."
        )