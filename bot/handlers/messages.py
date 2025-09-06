"""Message handlers for the bot."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.openai_service import OpenAIService
from ..services.user_service import UserService
from ..services.profanity_service import profanity_service
from ..utils.rate_limiter import RateLimiter

logger = get_logger(__name__)
openai_service = OpenAIService()
user_service = UserService()
rate_limiter = RateLimiter()


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages - only for logging and keyword triggers."""
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
    
    # Monitor profanity in the message
    try:
        profanity_found = await profanity_service.check_and_count_profanity(
            user_id=user.id,
            chat_id=update.effective_chat.id if update.effective_chat else 0,
            text=message_text
        )
        
        # Optional: React to profanity with emojis (but don't send messages)
        if profanity_found:
            logger.debug("Profanity detected in message", 
                        user_id=user.id, 
                        words=list(profanity_found.keys()),
                        total_count=sum(profanity_found.values()))
    except Exception as e:
        logger.error("Error monitoring profanity", error=str(e), exc_info=True)
    
    # Handle keyword triggers (like in original bot)
    await handle_keyword_triggers(update, context, message_text)


async def handle_keyword_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Handle specific keyword triggers from original bot."""
    message_lower = message_text.lower()
    
    # Check for specific keywords that should trigger responses
    keyword_responses = {
        "wen coco": "🥥 Next Coco times: 9:45, 15:45, 21:45, 3:45",
        "wen rish": "💰 Keep grinding! Wealth comes to those who persist!",
        "wen tits": "🔞 Random tiddies requested...",
    }
    
    for keyword, response in keyword_responses.items():
        if keyword in message_lower:
            await update.message.reply_text(response)
            return


async def ask_gpt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask_gpt command for direct AI queries."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    query = ' '.join(context.args) if context.args else ""
    
    if not query:
        await update.message.reply_text(
            "Please provide a query to ask. Usage: `/ask_gpt <your question>`",
            parse_mode="Markdown"
        )
        return
    
    # Check rate limiting
    if not await rate_limiter.check_rate_limit(user.id):
        await update.message.reply_text(
            "⚠️ You're sending messages too quickly. Please slow down a bit!"
        )
        return
    
    logger.info("GPT query", user_id=user.id, query=query)
    
    try:
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        await update.message.reply_text(f"🤖 Asking GPT-4: {query[:50]}...")
        
        # Generate AI response
        response = await openai_service.generate_response(
            message=query,
            user_id=user.id,
            username=user.username or user.first_name or str(user.id)
        )
        
        # Ensure response fits within Telegram's limit
        if len(response) > 4096:
            response = response[:4093] + "..."
        
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