"""Mines casino game multiplier calculator handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.mines_service import mines_service
from ..decorators.auth import auth_check

logger = get_logger(__name__)


@auth_check
async def mines_calculator_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calculate Mines game multipliers and odds."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "💎 **Mines Game Calculator**\n\n"
            "Usage:\n"
            "• `/mines <multiplier>` - Find mines/diamonds for target multiplier\n"
            "• `/mines <mines> <diamonds>` - Calculate multiplier and odds\n\n"
            "**Examples:**\n"
            "• `/mines 2.5` - Find combinations for 2.5x multiplier\n"
            "• `/mines 5 3` - 5 mines, 3 diamonds to pick\n"
            "• `/mines 10 2` - 10 mines, 2 diamonds to pick\n\n"
            "**Game Rules:**\n"
            "• 5×5 grid = 25 total tiles\n"
            "• Set number of mines (bombs)\n"
            "• Pick diamonds without hitting mines\n"
            "• Each diamond increases multiplier\n"
            "• Hit a mine = lose everything",
            parse_mode="Markdown"
        )
        return
    
    try:
        if len(context.args) == 1:
            # Mode 1: Find combinations for target multiplier
            target_multiplier = float(context.args[0])
            
            if target_multiplier <= 1.0:
                await update.message.reply_text("❌ Multiplier must be greater than 1.0")
                return
            
            combinations = await mines_service.find_combinations_for_multiplier(target_multiplier)
            
            if not combinations:
                await update.message.reply_text("❌ Unable to find combinations for that multiplier.")
                return
            
            response = f"💎 **Searching for multipliers close to {target_multiplier}x**\n\n"
            
            for i, (mines, diamonds, result) in enumerate(combinations, 1):
                response += f"🔹 **{i}.** {mines} mines and {diamonds} diamonds: **{result}x**\n"
            
            await update.message.reply_text(response, parse_mode="Markdown")
            
            logger.info("Mines target multiplier search", user_id=user_id, 
                       target_multiplier=target_multiplier)
        
        elif len(context.args) == 2:
            # Mode 2: Calculate multiplier from mines and diamonds
            mines = int(context.args[0])
            diamonds = int(context.args[1])
            
            result = await mines_service.calculate_multiplier_from_mines_diamonds(mines, diamonds)
            
            if not result:
                await update.message.reply_text(
                    "❌ Invalid combination!\n\n"
                    "• Mines and diamonds total must be ≤ 25\n"
                    "• Both must be greater than 0"
                )
                return
            
            multiplier = result["multiplier"]
            winning_chance = result["winning_chance"]
            close_multipliers = result["close_multipliers"]
            
            response = (
                f"💎 **Multiplier for {mines} mines and {diamonds} diamonds: {multiplier}x**\n"
                f"🎲 **Winning Chance: {winning_chance}%**\n\n"
                f"🔍 **Close multipliers:**\n"
            )
            
            for mines_close, diamonds_close, mult_close in close_multipliers:
                response += f"🔹 {mines_close} mines and {diamonds_close} diamonds: **{mult_close}x**\n"
            
            await update.message.reply_text(response, parse_mode="Markdown")
            
            logger.info("Mines multiplier calculation", user_id=user_id, 
                       mines=mines, diamonds=diamonds, multiplier=multiplier)
        
        else:
            await update.message.reply_text(
                "❌ Invalid usage!\n\n"
                "Use:\n"
                "• `/mines <multiplier>` - Find combinations\n"
                "• `/mines <mines> <diamonds>` - Calculate multiplier"
            )
    
    except ValueError:
        await update.message.reply_text("❌ Please provide valid numbers.")
    except Exception as e:
        logger.error("Error in Mines calculation", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred during calculation. Please try again."
        )


# Keep the old compare handler for backward compatibility but redirect to main handler
@auth_check
async def mines_compare_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Redirect to main mines calculator."""
    await update.message.reply_text(
        "💎 **Mines Calculator**\n\n"
        "Use `/mines` command instead:\n"
        "• `/mines <multiplier>` - Find combinations for target multiplier\n"
        "• `/mines <mines> <diamonds>` - Calculate multiplier and odds",
        parse_mode="Markdown"
    )


async def handle_mines_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle mines-related callback queries."""
    
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    try:
        # Future callback handling can be added here
        await query.answer("❓ Unknown action", show_alert=True)
        
    except Exception as e:
        logger.error("Error handling mines callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)