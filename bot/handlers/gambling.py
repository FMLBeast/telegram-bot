"""Gambling and casino handlers for the bot."""

import random
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..decorators.auth import auth_check
from ..services.user_service import UserService

logger = get_logger(__name__)
user_service = UserService()


@auth_check
async def casino_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /casino command for casino information and games."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    query = ' '.join(context.args) if context.args else ""
    
    if not query:
        # Show casino menu
        casino_text = (
            "🎰 **Welcome to the Casino!** 🎰\n\n"
            "Choose your game or ask a question:\n\n"
            "**Available Games:**\n"
            "🎲 Dice Roll - `/casino dice [bet]`\n"
            "🃏 Blackjack - `/casino blackjack [bet]`\n"
            "🎰 Slots - `/casino slots [bet]`\n"
            "🎯 Roulette - `/casino roulette [color/number] [bet]`\n\n"
            "**Casino Info:**\n"
            "Ask questions like:\n"
            "• `/casino vip levels`\n"
            "• `/casino bonuses`\n"
            "• `/casino rules blackjack`\n"
            "• `/casino strategy roulette`"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Dice", callback_data="casino_dice"),
                InlineKeyboardButton("🃏 Blackjack", callback_data="casino_blackjack"),
            ],
            [
                InlineKeyboardButton("🎰 Slots", callback_data="casino_slots"),
                InlineKeyboardButton("🎯 Roulette", callback_data="casino_roulette"),
            ],
            [
                InlineKeyboardButton("💰 VIP Info", callback_data="casino_vip"),
                InlineKeyboardButton("🎁 Bonuses", callback_data="casino_bonuses"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(casino_text, reply_markup=reply_markup, parse_mode="Markdown")
        return
    
    logger.info("Casino query", user_id=user_id, query=query)
    
    # Handle specific casino queries
    if "dice" in query.lower():
        await handle_dice_game(update, context, query)
    elif "blackjack" in query.lower():
        await handle_blackjack_game(update, context, query)
    elif "slots" in query.lower():
        await handle_slots_game(update, context, query)
    elif "roulette" in query.lower():
        await handle_roulette_game(update, context, query)
    elif "vip" in query.lower():
        await handle_vip_info(update, context, query)
    else:
        # General casino information using mock GPT response
        response = await get_casino_info_response(query)
        await update.message.reply_text(response, parse_mode="Markdown")


async def handle_dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """Handle dice roll game."""
    try:
        parts = query.split()
        bet_amount = 10  # Default bet
        if len(parts) > 1 and parts[1].isdigit():
            bet_amount = int(parts[1])
        
        if bet_amount < 1 or bet_amount > 1000:
            await update.message.reply_text("❌ Bet amount must be between 1 and 1000.")
            return
        
        # Roll dice
        player_roll = random.randint(1, 6)
        house_roll = random.randint(1, 6)
        
        result_text = f"🎲 **Dice Roll Game** 🎲\n\n"
        result_text += f"Your bet: {bet_amount}\n"
        result_text += f"Your roll: {player_roll}\n"
        result_text += f"House roll: {house_roll}\n\n"
        
        if player_roll > house_roll:
            winnings = bet_amount * 2
            result_text += f"🎉 **YOU WIN!** 🎉\n"
            result_text += f"Winnings: {winnings}"
        elif player_roll == house_roll:
            result_text += f"🤝 **TIE!** 🤝\n"
            result_text += f"Your bet is returned: {bet_amount}"
        else:
            result_text += f"😞 **HOUSE WINS** 😞\n"
            result_text += f"You lost: {bet_amount}"
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Play Again", callback_data=f"casino_dice_{bet_amount}"),
                InlineKeyboardButton("🏠 Casino Menu", callback_data="casino_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(result_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error in dice game", error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error playing dice game.")


async def handle_slots_game(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """Handle slots game."""
    try:
        parts = query.split()
        bet_amount = 10  # Default bet
        if len(parts) > 1 and parts[1].isdigit():
            bet_amount = int(parts[1])
        
        if bet_amount < 1 or bet_amount > 1000:
            await update.message.reply_text("❌ Bet amount must be between 1 and 1000.")
            return
        
        # Slot symbols
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
        weights = [30, 25, 20, 15, 5, 3, 2]  # Higher numbers = more common
        
        # Spin slots
        reel1 = random.choices(symbols, weights=weights)[0]
        reel2 = random.choices(symbols, weights=weights)[0]
        reel3 = random.choices(symbols, weights=weights)[0]
        
        result_text = f"🎰 **SLOT MACHINE** 🎰\n\n"
        result_text += f"Your bet: {bet_amount}\n\n"
        result_text += f"┌─────────────┐\n"
        result_text += f"│ {reel1} │ {reel2} │ {reel3} │\n"
        result_text += f"└─────────────┘\n\n"
        
        # Check for wins
        if reel1 == reel2 == reel3:
            if reel1 == "💎":
                multiplier = 50
                result_text += f"💎 **DIAMOND JACKPOT!** 💎"
            elif reel1 == "7️⃣":
                multiplier = 25
                result_text += f"7️⃣ **LUCKY SEVENS!** 7️⃣"
            elif reel1 == "⭐":
                multiplier = 10
                result_text += f"⭐ **STAR WIN!** ⭐"
            else:
                multiplier = 5
                result_text += f"🎉 **THREE IN A ROW!** 🎉"
            
            winnings = bet_amount * multiplier
            result_text += f"\nWinnings: {winnings} ({multiplier}x multiplier)"
            
        elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
            multiplier = 2
            winnings = bet_amount * multiplier
            result_text += f"🎯 **PAIR WIN!** 🎯\n"
            result_text += f"Winnings: {winnings} ({multiplier}x multiplier)"
        else:
            result_text += f"😞 **NO WIN** 😞\n"
            result_text += f"You lost: {bet_amount}"
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 Spin Again", callback_data=f"casino_slots_{bet_amount}"),
                InlineKeyboardButton("🏠 Casino Menu", callback_data="casino_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(result_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error in slots game", error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error playing slots.")


async def handle_vip_info(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """Handle VIP information queries."""
    vip_info = """
💎 **VIP LEVELS & BENEFITS** 💎

**Bronze VIP (Levels 2-7)**
• 5% cashback on losses
• Weekly bonus: $10
• Level-up bonus: $5-25

**Silver VIP (Levels 8-21)**
• 8% cashback on losses
• Weekly bonus: $25-50
• Level-up bonus: $50-200
• Priority support

**Gold VIP (Levels 22-37)**
• 12% cashback on losses
• Weekly bonus: $75-150
• Level-up bonus: $300-800
• Personal account manager

**Platinum I VIP (Levels 38-55)**
• 15% cashback on losses
• Weekly bonus: $200-500
• Level-up bonus: $1000-2500
• VIP events access

**Platinum II VIP (Levels 56-69)**
• 18% cashback on losses
• Weekly bonus: $600-1000
• Level-up bonus: $3000-5000
• Premium rewards

**Diamond I SVIP (SVIP 1-15)**
• 20% cashback on losses
• Weekly bonus: $1500-3000
• Level-up bonus: $7500-15000
• Exclusive tournaments

**Diamond II SVIP (SVIP 16-37)**
• 22% cashback on losses
• Weekly bonus: $4000-8000
• Level-up bonus: $20000-40000

**Diamond III SVIP (SVIP 38-75)**
• 25% cashback on losses
• Weekly bonus: $10000+
• Level-up bonus: $50000+
• Ultimate VIP experience
    """
    
    await update.message.reply_text(vip_info, parse_mode="Markdown")


async def get_casino_info_response(query: str) -> str:
    """Get casino information response (mock GPT integration)."""
    # Mock responses for common casino queries
    responses = {
        "bonus": "🎁 **Casino Bonuses**: New players get 100% deposit match up to $500! Daily bonuses available for active players. VIP members get exclusive weekly bonuses.",
        "rules": "📋 **Casino Rules**: All games use certified random number generators. Minimum bet: $1. Maximum bet varies by game. House edge disclosed for each game.",
        "strategy": "🎯 **Gaming Strategy**: Remember that all casino games favor the house. Set limits, play responsibly, and never bet more than you can afford to lose.",
        "support": "🆘 **Support**: 24/7 live chat available. VIP members get priority support. Email support available for all members.",
    }
    
    query_lower = query.lower()
    for keyword, response in responses.items():
        if keyword in query_lower:
            return response
    
    return f"🎰 **Casino Info**: {query}\n\nFor specific information about {query}, please contact our support team or check the VIP benefits with `/casino vip`."


async def bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /bet command for quick betting."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        bet_help = (
            "🎲 **Quick Betting** 🎲\n\n"
            "**Usage:**\n"
            "`/bet dice [amount]` - Roll dice vs house\n"
            "`/bet flip [amount] [heads/tails]` - Coin flip\n"
            "`/bet lucky [amount]` - Lucky number (1-100)\n\n"
            "**Examples:**\n"
            "`/bet dice 50` - Bet 50 on dice\n"
            "`/bet flip 25 heads` - Bet 25 on heads\n"
            "`/bet lucky 100` - Bet 100 on lucky number"
        )
        await update.message.reply_text(bet_help, parse_mode="Markdown")
        return
    
    game_type = args[0].lower()
    bet_amount = 10  # default
    
    if len(args) > 1 and args[1].isdigit():
        bet_amount = int(args[1])
    
    if bet_amount < 1 or bet_amount > 1000:
        await update.message.reply_text("❌ Bet amount must be between 1 and 1000.")
        return
    
    logger.info("Quick bet", user_id=user_id, game_type=game_type, bet_amount=bet_amount)
    
    if game_type == "dice":
        await handle_quick_dice_bet(update, bet_amount)
    elif game_type == "flip":
        choice = args[2].lower() if len(args) > 2 else "heads"
        await handle_coin_flip_bet(update, bet_amount, choice)
    elif game_type == "lucky":
        await handle_lucky_number_bet(update, bet_amount)
    else:
        await update.message.reply_text("❌ Unknown bet type. Use: dice, flip, or lucky")


async def handle_quick_dice_bet(update: Update, bet_amount: int) -> None:
    """Handle quick dice bet."""
    player_roll = random.randint(1, 6)
    house_roll = random.randint(1, 6)
    
    result = f"🎲 **Quick Dice Bet** 🎲\n\n"
    result += f"Bet: {bet_amount}\n"
    result += f"Your roll: {player_roll}\n"
    result += f"House roll: {house_roll}\n\n"
    
    if player_roll > house_roll:
        winnings = bet_amount * 2
        result += f"🎉 **YOU WIN!** Won: {winnings}"
    elif player_roll == house_roll:
        result += f"🤝 **TIE!** Bet returned: {bet_amount}"
    else:
        result += f"😞 **LOST!** Lost: {bet_amount}"
    
    await update.message.reply_text(result, parse_mode="Markdown")


async def handle_coin_flip_bet(update: Update, bet_amount: int, choice: str) -> None:
    """Handle coin flip bet."""
    flip_result = random.choice(["heads", "tails"])
    
    result = f"🪙 **Coin Flip Bet** 🪙\n\n"
    result += f"Bet: {bet_amount} on {choice}\n"
    result += f"Coin landed: {flip_result}\n\n"
    
    if choice == flip_result:
        winnings = bet_amount * 2
        result += f"🎉 **YOU WIN!** Won: {winnings}"
    else:
        result += f"😞 **LOST!** Lost: {bet_amount}"
    
    await update.message.reply_text(result, parse_mode="Markdown")


async def handle_lucky_number_bet(update: Update, bet_amount: int) -> None:
    """Handle lucky number bet."""
    player_number = random.randint(1, 100)
    winning_number = random.randint(1, 100)
    
    result = f"🍀 **Lucky Number Bet** 🍀\n\n"
    result += f"Bet: {bet_amount}\n"
    result += f"Your number: {player_number}\n"
    result += f"Winning number: {winning_number}\n\n"
    
    difference = abs(player_number - winning_number)
    
    if difference == 0:
        winnings = bet_amount * 100
        result += f"💥 **JACKPOT!** Exact match! Won: {winnings}"
    elif difference <= 5:
        winnings = bet_amount * 10
        result += f"🎯 **CLOSE WIN!** Within 5! Won: {winnings}"
    elif difference <= 10:
        winnings = bet_amount * 3
        result += f"🎉 **WIN!** Within 10! Won: {winnings}"
    else:
        result += f"😞 **LOST!** Too far (diff: {difference}). Lost: {bet_amount}"
    
    await update.message.reply_text(result, parse_mode="Markdown")


async def handle_gambling_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle gambling-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info("Gambling callback", user_id=user_id, callback_data=callback_data)
    
    try:
        if callback_data == "casino_menu":
            # Return to main casino menu
            casino_text = (
                "🎰 **Welcome to the Casino!** 🎰\n\n"
                "Choose your game or ask a question!"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🎲 Dice", callback_data="casino_dice"),
                    InlineKeyboardButton("🃏 Blackjack", callback_data="casino_blackjack"),
                ],
                [
                    InlineKeyboardButton("🎰 Slots", callback_data="casino_slots"),
                    InlineKeyboardButton("🎯 Roulette", callback_data="casino_roulette"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(casino_text, reply_markup=reply_markup, parse_mode="Markdown")
            
        elif callback_data.startswith("casino_dice"):
            if "_" in callback_data:
                bet_amount = int(callback_data.split("_")[-1])
            else:
                bet_amount = 10
            
            # Simulate dice game
            player_roll = random.randint(1, 6)
            house_roll = random.randint(1, 6)
            
            result_text = f"🎲 **Dice Roll Game** 🎲\n\n"
            result_text += f"Bet: {bet_amount} | Your roll: {player_roll} | House: {house_roll}\n\n"
            
            if player_roll > house_roll:
                winnings = bet_amount * 2
                result_text += f"🎉 **YOU WIN!** Won: {winnings}"
            else:
                result_text += f"😞 **LOST!** Lost: {bet_amount}"
            
            keyboard = [
                [
                    InlineKeyboardButton("🎲 Play Again", callback_data=f"casino_dice_{bet_amount}"),
                    InlineKeyboardButton("🏠 Casino Menu", callback_data="casino_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(result_text, reply_markup=reply_markup, parse_mode="Markdown")
            
        else:
            await query.answer("❓ Game not implemented yet", show_alert=True)
            
    except Exception as e:
        logger.error("Error handling gambling callback", user_id=user_id, callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)