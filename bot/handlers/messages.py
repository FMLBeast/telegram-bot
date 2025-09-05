"""Message handlers for the bot."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.openai_service import OpenAIService
from ..services.user_service import UserService
from ..utils.rate_limiter import RateLimiter

logger = get_logger(__name__)
openai_service = OpenAIService()
user_service = UserService()
rate_limiter = RateLimiter()


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    if not update.message or not update.effective_user or not update.message.text:
        return
    
    user = update.effective_user
    message_text = update.message.text.strip()
    
    logger.info(
        "Message received",
        user_id=user.id,
        username=user.username,
        message_length=len(message_text)
    )
    
    # Check rate limiting
    if not await rate_limiter.check_rate_limit(user.id):
        await update.message.reply_text(
            "⚠️ You're sending messages too quickly. Please slow down a bit!"
        )
        return
    
    # Register or update user
    await user_service.create_or_update_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    
    # Log message to database
    await user_service.log_message(
        user_id=user.id,
        chat_id=update.effective_chat.id if update.effective_chat else 0,
        message_text=message_text,
    )
    
    try:
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Generate AI response
        response = await openai_service.generate_response(
            message=message_text,
            user_id=user.id,
            username=user.username or user.first_name or str(user.id)
        )
        
        # Send response
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        
        logger.info(
            "AI response sent",
            user_id=user.id,
            response_length=len(response)
        )
        
    except Exception as e:
        logger.error(
            "Error generating AI response",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        
        await update.message.reply_text(
            "🤖 Sorry, I encountered an error while processing your message. "
            "Please try again later!"
        )