"""Back-to-back betting progression calculator handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.b2b_service import b2b_service
from ..decorators.auth import auth_check

logger = get_logger(__name__)


@auth_check
async def b2b_calculator_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calculate betting progression for gambling strategy."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "🎲 **Betting Progression Calculator**\n\n"
            "Usage: `/b2b <base_bet> <multiplier> <increase_percentage>`\n\n"
            "**Examples:**\n"
            "• `/b2b 100 2.0 10` - Base bet 100, 2x multiplier, 10% increase per round\n"
            "• `/b2b 50 1.5 5` - Base bet 50, 1.5x multiplier, 5% increase per round\n"
            "• `/b2b 1000 3.0 15` - Base bet 1000, 3x multiplier, 15% increase per round\n\n"
            "**Parameters:**\n"
            "• `base_bet` - Starting bet amount\n"
            "• `multiplier` - Payout multiplier (e.g., 2.0 = 2x payout)\n"
            "• `increase_percentage` - How much to increase bet each round (%)",
            parse_mode="Markdown"
        )
        return
    
    try:
        base_bet = float(context.args[0].replace(",", "."))
        multiplier = float(context.args[1].replace(",", "."))
        increase_percentage = float(context.args[2].replace(",", "."))
        
        if base_bet <= 0 or multiplier <= 0 or increase_percentage < 0:
            await update.message.reply_text("❌ Please provide valid positive values.")
            return
        
        # Calculate betting progression
        bets, net_results, total = await b2b_service.calculate_bets(
            base_bet, multiplier, increase_percentage
        )
        
        if not bets or not net_results:
            await update.message.reply_text("❌ Error calculating betting progression.")
            return
        
        # Create header and table with monospace formatting
        result_message = (
            "🎲 **Betting Progression Analysis** 🎲\n\n"
            "```\n"
            "┌─────────┬───────────┬───────────┬───────────┐\n"
            "│  Round  │ Bet Size  │  Result   │   Total   │\n"
            "├─────────┼───────────┼───────────┼───────────┤\n"
        )
        
        # Add table rows
        current_total = 0
        for i, (bet, net_result) in enumerate(zip(bets, net_results), start=1):
            current_total += net_result
            result_message += (
                f"│ {str(i):<8}│ {b2b_service.format_number(bet):<10}│ "
                f"{b2b_service.format_number(net_result):<10}│ "
                f"{b2b_service.format_number(current_total):<10}│\n"
            )
        
        # Close table
        result_message += (
            "└─────────┴───────────┴───────────┴───────────┘\n"
            "```\n\n"
        )
        
        # Add summary
        summary = (
            f"📈 **Initial Bet:** `{base_bet}`\n"
            f"📊 **Multiplier:** `{multiplier:.1f}x`\n"
            f"📋 **Increase:** `{increase_percentage:.1f}%`\n\n"
            f"💰 **Total After 20 Rounds:** `{b2b_service.format_number(current_total)}`"
        )
        
        # Send message
        await update.message.reply_text(
            result_message + summary,
            parse_mode="Markdown"
        )
        
        logger.info("B2B calculation", user_id=user_id, base_bet=base_bet, 
                   multiplier=multiplier, increase_percentage=increase_percentage)
        
    except ValueError:
        await update.message.reply_text("❌ Please provide valid numeric values.")
    except Exception as e:
        logger.error("Error in B2B calculation", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred during calculation. Please try again."
        )


async def handle_b2b_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle B2B-related callback queries."""
    
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    try:
        # Future callback handling can be added here
        await query.answer("❓ Unknown action", show_alert=True)
        
    except Exception as e:
        logger.error("Error handling B2B callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)