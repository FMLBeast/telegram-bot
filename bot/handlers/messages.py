"""Message handlers for the bot."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.openai_service import OpenAIService
from ..services.user_service import UserService
from ..services.mines_service import mines_service
from ..services.b2b_service import b2b_service
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
    
    # Check if user is expecting input for specific functionality
    if context.user_data.get('expecting_image_prompt'):
        await handle_image_prompt_input(update, context, message_text)
        return
    elif context.user_data.get('expecting_mines_calc'):
        await handle_mines_calc_input(update, context, message_text)
        return
    elif context.user_data.get('expecting_b2b_calc'):
        await handle_b2b_calc_input(update, context, message_text)
        return
    
    # Default: AI response for regular messages
    await handle_ai_response(update, context, message_text)


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


# New handler functions for interactive menu inputs
async def handle_image_prompt_input(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Handle image generation prompt input."""
    # Clear the expectation flag
    context.user_data['expecting_image_prompt'] = False
    
    await update.message.reply_text("🎨 Generating your image...")
    
    try:
        from ..handlers.images import draw_me_handler
        # Simulate the draw_me command with the provided text
        context.args = message_text.split()
        await draw_me_handler(update, context)
    except Exception as e:
        logger.error("Error generating image from prompt", error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error generating image. Please try again later.")


async def handle_mines_calc_input(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Handle mines calculator input."""
    # Clear the expectation flag
    context.user_data['expecting_mines_calc'] = False
    
    try:
        parts = message_text.strip().split()
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Invalid format. Please use: [mines] [diamonds]\n"
                "Example: 5 3"
            )
            return
        
        mines = int(parts[0])
        diamonds = int(parts[1])
        
        result = await mines_service.calculate_multiplier_from_mines_diamonds(mines, diamonds)
        
        if result:
            calc_text = f"💎 <b>Mines Calculator Result</b>\n\n"
            calc_text += f"⛏️ Mines: {result['mines']}\n"
            calc_text += f"💎 Diamonds: {result['diamonds']}\n"
            calc_text += f"🎯 Multiplier: {result['multiplier']}x\n"
            calc_text += f"📊 Win Chance: {result['winning_chance']}%\n\n"
            
            if result.get('close_multipliers'):
                calc_text += "<b>Similar combinations:</b>\n"
                for mines_alt, diamonds_alt, mult_alt in result['close_multipliers'][:3]:
                    calc_text += f"• {mines_alt}M/{diamonds_alt}D = {mult_alt}x\n"
            
            await update.message.reply_text(calc_text, parse_mode="HTML")
        else:
            await update.message.reply_text("❌ Invalid combination. Please try different values.")
    
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter valid numbers.\n"
            "Format: [mines] [diamonds]\n"
            "Example: 5 3"
        )
    except Exception as e:
        logger.error("Error calculating mines", error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error calculating. Please try again.")


async def handle_b2b_calc_input(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Handle B2B calculator input."""
    # Clear the expectation flag
    context.user_data['expecting_b2b_calc'] = False
    
    try:
        parts = message_text.strip().split()
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Invalid format. Please use: [base_bet] [multiplier] [increase_%]\n"
                "Example: 100 2.0 10"
            )
            return
        
        base_bet = float(parts[0])
        multiplier = float(parts[1])
        increase_percentage = float(parts[2])
        
        bets, net_results, total = await b2b_service.calculate_bets(
            base_bet, multiplier, increase_percentage
        )
        
        if bets:
            calc_text = f"💰 <b>B2B Calculator Result</b>\n\n"
            calc_text += f"💵 Base bet: {b2b_service.format_number(base_bet)}\n"
            calc_text += f"📈 Multiplier: {multiplier}x\n"
            calc_text += f"📊 Increase: {increase_percentage}%\n\n"
            calc_text += f"<b>First 10 rounds:</b>\n"
            
            for i in range(min(10, len(bets))):
                bet = bets[i]
                calc_text += f"{i+1:2d}. Bet: {b2b_service.format_number(bet)}\n"
            
            calc_text += f"\n🎯 Total potential: {b2b_service.format_number(total)}"
            
            await update.message.reply_text(calc_text, parse_mode="HTML")
        else:
            await update.message.reply_text("❌ Error calculating progression. Please try different values.")
    
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter valid numbers.\n"
            "Format: [base_bet] [multiplier] [increase_%]\n"
            "Example: 100 2.0 10"
        )
    except Exception as e:
        logger.error("Error calculating B2B", error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error calculating. Please try again.")


async def handle_ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Handle AI response for regular messages."""
    user = update.effective_user
    
    # Check rate limiting
    if not await rate_limiter.check_rate_limit(user.id):
        await update.message.reply_text(
            "⚠️ You're sending messages too quickly. Please slow down a bit!"
        )
        return
    
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