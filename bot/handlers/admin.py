"""Admin command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.auth_service import auth_service
from ..decorators.auth import auth_check, admin_only

logger = get_logger(__name__)


@auth_check
@admin_only
async def grant_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grant bot access to a channel or user."""
    
    if not update.message or not context.args:
        await update.message.reply_text(
            "Usage: /grant_access <channel_id> [channel_name]\n"
            "Example: /grant_access -1001234567890 \"My Channel\""
        )
        return
    
    try:
        channel_id = int(context.args[0])
        channel_name = " ".join(context.args[1:]) if len(context.args) > 1 else None
        granted_by = update.effective_user.id
        
        success = await auth_service.authorize_channel(channel_id, channel_name, granted_by)
        
        if success:
            message = f"✅ Access granted to channel {channel_id}"
            if channel_name:
                message += f" ({channel_name})"
            
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                f"⚠️ Channel {channel_id} is already authorized."
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid channel ID. Please provide a numeric channel ID."
        )
    except Exception as e:
        logger.error("Error granting access", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while granting access."
        )


@auth_check
@admin_only
async def revoke_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revoke bot access from a channel."""
    
    if not update.message or not context.args:
        await update.message.reply_text(
            "Usage: /revoke_access <channel_id>\n"
            "Example: /revoke_access -1001234567890"
        )
        return
    
    try:
        channel_id = int(context.args[0])
        
        success = await auth_service.revoke_channel(channel_id)
        
        if success:
            await update.message.reply_text(
                f"✅ Access revoked from channel {channel_id}"
            )
        else:
            await update.message.reply_text(
                f"⚠️ Channel {channel_id} was not authorized."
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid channel ID. Please provide a numeric channel ID."
        )
    except Exception as e:
        logger.error("Error revoking access", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while revoking access."
        )


@auth_check
@admin_only
async def list_authorized_channels_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all authorized channels."""
    
    try:
        channels = await auth_service.get_authorized_channels()
        
        if not channels:
            await update.message.reply_text("📝 No authorized channels found.")
            return
        
        message = "📋 **Authorized Channels:**\n\n"
        
        for channel in channels:
            channel_info = f"• `{channel['channel_id']}`"
            if channel['channel_name']:
                channel_info += f" - {channel['channel_name']}"
            channel_info += f" (authorized by {channel['authorized_by']})"
            message += channel_info + "\n"
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error listing channels", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while listing channels."
        )


@auth_check
@admin_only
async def ban_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ban a user from using the bot."""
    
    if not update.message or not context.args:
        await update.message.reply_text(
            "Usage: /ban_user <user_id>\n"
            "Example: /ban_user 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
        banned_by = update.effective_user.id
        
        # Don't allow banning admins
        if await auth_service.is_user_admin(user_id):
            await update.message.reply_text(
                "❌ Cannot ban an admin user."
            )
            return
        
        success = await auth_service.grant_user_permission(
            user_id, "banned", banned_by
        )
        
        if success:
            await update.message.reply_text(
                f"🚫 User {user_id} has been banned."
            )
        else:
            await update.message.reply_text(
                "❌ Failed to ban user."
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please provide a numeric user ID."
        )
    except Exception as e:
        logger.error("Error banning user", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while banning user."
        )


@auth_check
@admin_only
async def unban_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unban a user."""
    
    if not update.message or not context.args:
        await update.message.reply_text(
            "Usage: /unban_user <user_id>\n"
            "Example: /unban_user 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        success = await auth_service.revoke_user_permission(user_id, "banned")
        
        if success:
            await update.message.reply_text(
                f"✅ User {user_id} has been unbanned."
            )
        else:
            await update.message.reply_text(
                f"⚠️ User {user_id} was not banned."
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please provide a numeric user ID."
        )
    except Exception as e:
        logger.error("Error unbanning user", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while unbanning user."
        )


@auth_check
@admin_only
async def make_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Make a user an admin."""
    
    if not update.message or not context.args:
        await update.message.reply_text(
            "Usage: /make_admin <user_id>\n"
            "Example: /make_admin 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
        granted_by = update.effective_user.id
        
        success = await auth_service.grant_user_permission(
            user_id, "admin", granted_by
        )
        
        if success:
            await update.message.reply_text(
                f"👑 User {user_id} is now an admin."
            )
        else:
            await update.message.reply_text(
                "❌ Failed to make user admin."
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please provide a numeric user ID."
        )
    except Exception as e:
        logger.error("Error making admin", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while making user admin."
        )


async def request_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Request access to use the bot (no auth required)."""
    
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    # Log the request
    logger.info(
        "Access request",
        user_id=user.id,
        username=user.username or user.first_name,
        chat_id=chat.id,
        chat_title=chat.title or "Private"
    )
    
    message = (
        "📝 **Access Request Submitted**\n\n"
        f"User: {user.first_name} (@{user.username or 'no username'})\n"
        f"User ID: `{user.id}`\n"
        f"Chat: {chat.title or 'Private Chat'}\n"
        f"Chat ID: `{chat.id}`\n\n"
        "Your request has been logged. An administrator will review it shortly.\n\n"
        "💡 **Tip:** If you're an admin, you can authorize yourself with:\n"
        f"`/grant_access {chat.id}`"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")