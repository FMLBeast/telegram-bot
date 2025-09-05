"""Authorization decorators for bot handlers."""

import functools
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

from ..services.auth_service import auth_service
from ..core.logging import get_logger

logger = get_logger(__name__)


def auth_check(handler_func: Callable) -> Callable:
    """
    Decorator that checks authorization before executing handler.
    Logs all command attempts and blocks unauthorized access.
    """
    
    @functools.wraps(handler_func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        try:
            # Extract user and chat info
            user = update.effective_user
            chat = update.effective_chat
            
            if not user or not chat:
                logger.warning("Handler called without user or chat context")
                return
            
            user_id = user.id
            chat_id = chat.id
            username = user.username or user.first_name or str(user_id)
            
            # Log command attempt
            command = "unknown"
            if update.message and update.message.text:
                command = update.message.text.split()[0]
                args = update.message.text.split()[1:]
                logger.info(
                    "Command attempt",
                    command=command,
                    args=args,
                    user_id=user_id,
                    username=username,
                    chat_id=chat_id
                )
            
            # Check access
            has_access = await auth_service.check_access(user_id, chat_id)
            
            if not has_access:
                # Check specific denial reasons for better messages
                if await auth_service.is_user_banned(user_id):
                    message = "🚫 You are banned from using this bot."
                elif not await auth_service.is_channel_authorized(chat_id):
                    message = (
                        "❌ This bot is not authorized in this channel.\n"
                        "Please use /request_access to request authorization."
                    )
                else:
                    message = "❌ You are not authorized to use this bot."
                
                logger.warning(
                    "Unauthorized access attempt",
                    user_id=user_id,
                    username=username,
                    chat_id=chat_id,
                    command=command
                )
                
                if update.message:
                    await update.message.reply_text(message)
                elif update.callback_query:
                    await update.callback_query.answer(message, show_alert=True)
                
                return
            
            # Execute handler
            return await handler_func(update, context)
            
        except Exception as e:
            logger.error(
                "Error in auth decorator",
                handler=handler_func.__name__,
                error=str(e),
                exc_info=True
            )
            
            error_message = "🤖 An error occurred while processing your request."
            
            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)
    
    return wrapper


def require_auth(handler_func: Callable) -> Callable:
    """Alias for auth_check for backwards compatibility."""
    return auth_check(handler_func)


def admin_only(handler_func: Callable) -> Callable:
    """
    Decorator that restricts access to admin users only.
    Should be used in combination with auth_check.
    """
    
    @functools.wraps(handler_func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        user = update.effective_user
        
        if not user:
            logger.warning("Admin handler called without user context")
            return
        
        user_id = user.id
        username = user.username or user.first_name or str(user_id)
        
        # Check if user is admin
        is_admin = await auth_service.is_user_admin(user_id)
        
        if not is_admin:
            message = "🔒 This command is restricted to administrators only."
            
            logger.warning(
                "Non-admin attempted admin command",
                user_id=user_id,
                username=username,
                handler=handler_func.__name__
            )
            
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
            
            return
        
        # User is admin, proceed with handler
        logger.info(
            "Admin command executed",
            user_id=user_id,
            username=username,
            handler=handler_func.__name__
        )
        
        return await handler_func(update, context)
    
    return wrapper