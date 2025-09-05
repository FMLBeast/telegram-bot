"""Error handlers for the bot."""

import traceback
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import (
    Forbidden,
    BadRequest,
    TimedOut,
    NetworkError,
    TelegramError,
)

from ..core.logging import get_logger

logger = get_logger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors that occur during bot operation."""
    
    # Get error details
    error = context.error
    error_traceback = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    
    # Log the error with context
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "update_type": type(update).__name__ if update else None,
    }
    
    if isinstance(update, Update):
        if update.effective_user:
            error_context["user_id"] = update.effective_user.id
            error_context["username"] = update.effective_user.username
        if update.effective_chat:
            error_context["chat_id"] = update.effective_chat.id
            error_context["chat_type"] = update.effective_chat.type
    
    logger.error(
        "Bot error occurred",
        **error_context,
        traceback=error_traceback
    )
    
    # Handle specific error types
    try:
        if isinstance(error, Forbidden):
            await _handle_forbidden_error(update, context)
        elif isinstance(error, BadRequest):
            await _handle_bad_request_error(update, context)
        elif isinstance(error, TimedOut):
            await _handle_timeout_error(update, context)
        elif isinstance(error, NetworkError):
            await _handle_network_error(update, context)
        else:
            await _handle_generic_error(update, context)
            
    except Exception as e:
        logger.error(
            "Error in error handler",
            error=str(e),
            original_error=str(error),
            exc_info=True
        )


async def _handle_forbidden_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Forbidden errors (bot blocked, kicked from chat, etc.)."""
    if isinstance(update, Update) and update.effective_chat:
        chat_id = update.effective_chat.id
        logger.warning(
            "Bot forbidden in chat - user may have blocked bot or bot was removed",
            chat_id=chat_id
        )
        # Could update database to mark user/chat as inactive


async def _handle_bad_request_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle BadRequest errors (invalid parameters, etc.)."""
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Sorry, there was an issue with your request. Please try again."
            )
        except Exception:
            pass  # Ignore if we can't send the error message


async def _handle_timeout_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle timeout errors."""
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏱️ Request timed out. Please try again in a moment."
            )
        except Exception:
            pass


async def _handle_network_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle network-related errors."""
    logger.warning("Network error occurred - this usually resolves automatically")
    # Network errors are often temporary and don't require user notification


async def _handle_generic_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generic errors."""
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🤖 Oops! Something went wrong. Our team has been notified. Please try again later."
            )
        except Exception:
            pass