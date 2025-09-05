"""Callback handlers for image interactions."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.image_service import image_service

logger = get_logger(__name__)


async def handle_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image-related callback queries."""
    
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        # Parse callback data
        if callback_data.startswith("fav_"):
            # Toggle favorite
            image_id = int(callback_data.split("_")[1])
            success = await image_service.set_favorite(user_id, image_id, True)
            
            if success:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n⭐ Added to favorites!",
                    parse_mode="Markdown"
                )
            else:
                await query.answer("❌ Failed to add to favorites", show_alert=True)
        
        elif callback_data.startswith("collect_"):
            # Add to personal collection
            image_id = int(callback_data.split("_")[1])
            success = await image_service.add_to_collection(user_id, image_id, "default")
            
            if success:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n📁 Added to your collection!",
                    parse_mode="Markdown"
                )
            else:
                await query.answer("❌ Failed to add to collection", show_alert=True)
        
        elif callback_data.startswith("group_collect_"):
            # Add to group collection
            image_id = int(callback_data.split("_")[2])
            chat_id = update.effective_chat.id if update.effective_chat else None
            
            if chat_id and chat_id < 0:  # Group chat
                success = await image_service.add_to_collection(
                    user_id, image_id, "default", chat_id
                )
                
                if success:
                    await query.edit_message_caption(
                        caption=query.message.caption + "\n📁 Added to group collection!",
                        parse_mode="Markdown"
                    )
                else:
                    await query.answer("❌ Failed to add to group collection", show_alert=True)
            else:
                await query.answer("❌ Group collections only work in groups", show_alert=True)
        
        elif callback_data.startswith("stats_"):
            # Show user stats
            target_user_id = int(callback_data.split("_")[1])
            
            if target_user_id != user_id:
                await query.answer("❌ You can only view your own stats", show_alert=True)
                return
            
            stats = await image_service.get_user_stats(user_id)
            
            # Progress bar for daily usage
            used_pct = (stats["today_images"] / stats["daily_limit"]) * 100
            bar_length = 15
            filled_length = int(bar_length * used_pct // 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            stats_message = (
                f"📊 **Your Stats**\n"
                f"🎨 Total: {stats['total_images']}\n"
                f"⭐ Favorites: {stats['favorites_count']}\n"
                f"📅 Today: {bar} {stats['today_images']}/{stats['daily_limit']}\n"
                f"Remaining: {stats['remaining_today']}"
            )
            
            await query.answer(stats_message, show_alert=True)
        
        elif callback_data.startswith("favs_"):
            # Show favorites (placeholder - would need pagination)
            await query.answer("⭐ Favorites view - coming soon!", show_alert=True)
        
        elif callback_data.startswith("collection_"):
            # Refresh personal collection (placeholder)
            await query.answer("🔄 Collection refreshed!", show_alert=True)
        
        elif callback_data.startswith("group_collection_"):
            # Refresh group collection (placeholder)
            await query.answer("🔄 Group collection refreshed!", show_alert=True)
        
        else:
            await query.answer("❓ Unknown action", show_alert=True)
            
    except ValueError as e:
        logger.error("Invalid callback data", callback_data=callback_data, error=str(e))
        await query.answer("❌ Invalid data", show_alert=True)
    except Exception as e:
        logger.error("Error handling image callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)