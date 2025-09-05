"""Cryptocurrency betting and tracking handlers."""

import re
from datetime import datetime, timedelta
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.crypto_service import crypto_service
from ..decorators.auth import auth_check
from ..core.exceptions import APIError

logger = get_logger(__name__)


def format_currency(amount: float) -> str:
    """Format currency amount."""
    return f"${amount:,.2f}"


def format_price(price: float, symbol: str) -> str:
    """Format crypto price with appropriate decimals."""
    if symbol in ["BTC", "ETH", "BNB", "LTC", "BCH"]:
        return f"${price:,.2f}"
    else:
        return f"${price:.4f}"


@auth_check
async def crypto_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show cryptocurrency prices."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    # Get specific coin or show popular coins
    symbol = None
    if context.args:
        symbol = context.args[0].upper()
    
    try:
        if symbol:
            # Show specific coin
            price_data = await crypto_service.get_crypto_price(symbol)
            
            if not price_data:
                await update.message.reply_text(
                    f"❌ Cryptocurrency `{symbol}` not supported.\n\n"
                    f"Supported coins: BTC, ETH, BNB, ADA, DOT, LINK, LTC, BCH, XRP, DOGE",
                    parse_mode="Markdown"
                )
                return
            
            change_emoji = "📈" if price_data["change_percent"] > 0 else "📉"
            change_sign = "+" if price_data["change_percent"] > 0 else ""
            
            message = (
                f"💰 **{price_data['name']} ({symbol})**\n\n"
                f"💵 **Price:** {format_price(price_data['price'], symbol)}\n"
                f"{change_emoji} **24h Change:** {change_sign}{price_data['change_percent']:.2f}% "
                f"({change_sign}{format_currency(price_data['change_24h'])})\n"
                f"📊 **Volume 24h:** {format_currency(price_data['volume_24h'])}\n"
                f"💎 **Market Cap:** {format_currency(price_data['market_cap'])}\n\n"
                f"🎲 Ready to bet? Use `/bet {symbol.lower()} up 10 1h`"
            )
            
            # Add betting buttons
            keyboard = [
                [
                    InlineKeyboardButton(f"📈 Bet UP", callback_data=f"bet_{symbol}_up_10_60"),
                    InlineKeyboardButton(f"📉 Bet DOWN", callback_data=f"bet_{symbol}_down_10_60"),
                ],
                [
                    InlineKeyboardButton(f"🎯 Exact Price", callback_data=f"bet_{symbol}_exact"),
                    InlineKeyboardButton(f"💰 Balance", callback_data="crypto_balance"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        else:
            # Show popular coins overview
            popular_coins = ["BTC", "ETH", "BNB", "ADA", "DOGE"]
            message = "💰 **Cryptocurrency Prices**\n\n"
            
            for coin in popular_coins:
                price_data = await crypto_service.get_crypto_price(coin)
                if price_data:
                    change_emoji = "📈" if price_data["change_percent"] > 0 else "📉"
                    change_sign = "+" if price_data["change_percent"] > 0 else ""
                    
                    message += (
                        f"**{coin}** {format_price(price_data['price'], coin)} "
                        f"{change_emoji} {change_sign}{price_data['change_percent']:.2f}%\n"
                    )
            
            message += (
                f"\n💡 **Usage:**\n"
                f"• `/price BTC` - Get detailed price\n"
                f"• `/bet btc up 50 2h` - Place a bet\n"
                f"• `/balance` - Check your balance"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error showing crypto prices", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while fetching cryptocurrency prices."
        )


@auth_check
async def crypto_bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Place a cryptocurrency bet."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "🎲 **Place a Crypto Bet**\n\n"
            "Usage: `/bet <symbol> <direction> <amount> [duration]`\n\n"
            "**Examples:**\n"
            "`/bet BTC up 50` - Bet $50 that BTC goes up (1h)\n"
            "`/bet ETH down 25 2h` - Bet $25 that ETH goes down (2h)\n"
            "`/bet BTC exact 65000 30m` - Bet BTC hits exactly $65,000\n\n"
            "**Directions:** up, down, exact\n"
            "**Durations:** 15m, 30m, 1h, 2h, 4h, 24h",
            parse_mode="Markdown"
        )
        return
    
    try:
        symbol = context.args[0].upper()
        bet_type = context.args[1].lower()
        amount = float(context.args[2])
        
        # Parse duration
        duration_minutes = 60  # Default 1 hour
        target_price = None
        
        if len(context.args) > 3:
            duration_arg = context.args[3].lower()
            
            # Parse duration formats
            if duration_arg.endswith('m'):
                duration_minutes = int(duration_arg[:-1])
            elif duration_arg.endswith('h'):
                duration_minutes = int(duration_arg[:-1]) * 60
            elif duration_arg.endswith('d'):
                duration_minutes = int(duration_arg[:-1]) * 1440
            else:
                # Might be exact price target
                try:
                    target_price = float(duration_arg)
                except ValueError:
                    pass
        
        # For exact bets, next arg might be target price
        if bet_type == "exact" and len(context.args) > 4:
            try:
                target_price = float(context.args[4])
            except ValueError:
                pass
        
        # Validate inputs
        if amount < 1:
            await update.message.reply_text("❌ Minimum bet amount is $1.")
            return
        
        if amount > 1000:
            await update.message.reply_text("❌ Maximum bet amount is $1,000.")
            return
        
        if duration_minutes < 15:
            await update.message.reply_text("❌ Minimum bet duration is 15 minutes.")
            return
        
        if duration_minutes > 1440:  # 24 hours
            await update.message.reply_text("❌ Maximum bet duration is 24 hours.")
            return
        
        # Place the bet
        bet_result = await crypto_service.place_bet(
            user_id=user_id,
            chat_id=chat_id,
            symbol=symbol,
            bet_type=bet_type,
            amount=amount,
            duration_minutes=duration_minutes,
            target_price=target_price
        )
        
        if bet_result:
            direction_emoji = {"up": "📈", "down": "📉", "exact": "🎯"}[bet_type]
            
            message = (
                f"🎲 **Bet Placed!**\n\n"
                f"{direction_emoji} **Direction:** {bet_type.upper()}\n"
                f"💰 **Symbol:** {symbol}\n"
                f"💵 **Amount:** {format_currency(amount)}\n"
                f"📊 **Current Price:** {format_price(bet_result['current_price'], symbol)}\n"
            )
            
            if target_price:
                message += f"🎯 **Target Price:** {format_price(target_price, symbol)}\n"
            
            message += (
                f"⏱️ **Duration:** {duration_minutes} minutes\n"
                f"💎 **Potential Payout:** {format_currency(bet_result['potential_payout'])}\n"
                f"🕐 **Expires:** {bet_result['expires_at'].strftime('%H:%M:%S')}\n\n"
                f"**Bet ID:** `{bet_result['bet_id']}`\n\n"
                f"Good luck! 🍀"
            )
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("💰 Balance", callback_data="crypto_balance"),
                    InlineKeyboardButton("📊 My Bets", callback_data="crypto_my_bets"),
                ],
                [
                    InlineKeyboardButton(f"📈 Price Update", callback_data=f"price_update_{symbol}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
    except APIError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid bet format. Use: `/bet <symbol> <direction> <amount> [duration]`"
        )
    except Exception as e:
        logger.error("Error placing crypto bet", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while placing your bet."
        )


@auth_check
async def crypto_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's crypto betting balance and stats."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        balance_data = await crypto_service.get_user_balance(user_id)
        
        # Progress bar for win rate
        win_rate = balance_data["win_rate"]
        bar_length = 15
        filled_length = int(bar_length * win_rate // 100)
        win_bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Profit/Loss emoji
        pl_emoji = "📈" if balance_data["profit_loss"] >= 0 else "📉"
        pl_sign = "+" if balance_data["profit_loss"] >= 0 else ""
        
        message = (
            f"💰 **Your Crypto Balance**\n\n"
            f"💵 **Current Balance:** {format_currency(balance_data['balance'])}\n"
            f"💎 **Total Wagered:** {format_currency(balance_data['total_wagered'])}\n"
            f"💚 **Total Won:** {format_currency(balance_data['total_won'])}\n"
            f"💔 **Total Lost:** {format_currency(balance_data['total_lost'])}\n\n"
            f"{pl_emoji} **Profit/Loss:** {pl_sign}{format_currency(balance_data['profit_loss'])}\n"
            f"🎯 **Win Rate:** {win_rate:.1f}%\n"
            f"{win_bar} {win_rate:.1f}%\n\n"
            f"🔥 **Current Streak:** {balance_data['win_streak']}\n"
            f"🏆 **Best Streak:** {balance_data['best_streak']}\n"
            f"📊 **Total Bets:** {balance_data['total_bets']}\n\n"
        )
        
        # Add daily bonus info
        bonus_amount = await crypto_service.give_daily_bonus(user_id)
        if bonus_amount:
            message += f"🎁 **Daily Bonus:** +{format_currency(bonus_amount)} claimed!"
        else:
            message += "🎁 **Daily Bonus:** Already claimed today"
        
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton("📊 My Bets", callback_data="crypto_my_bets"),
                InlineKeyboardButton("🏆 Leaderboard", callback_data="crypto_leaderboard"),
            ],
            [
                InlineKeyboardButton("💰 Prices", callback_data="crypto_prices"),
                InlineKeyboardButton("🎲 Quick Bet", callback_data="crypto_quick_bet"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error("Error showing crypto balance", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading your balance."
        )


@auth_check
async def crypto_bets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's betting history."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        # Parse arguments
        status_filter = None
        if context.args and context.args[0].lower() in ["pending", "won", "lost"]:
            status_filter = context.args[0].lower()
        
        bets = await crypto_service.get_user_bets(user_id, status=status_filter, limit=10)
        
        if not bets:
            filter_text = f" {status_filter}" if status_filter else ""
            await update.message.reply_text(
                f"📊 No{filter_text} bets found.\n\n"
                f"Place your first bet with `/bet BTC up 10`!",
                parse_mode="Markdown"
            )
            return
        
        status_emoji = {"pending": "⏳", "won": "✅", "lost": "❌"}
        direction_emoji = {"up": "📈", "down": "📉", "exact": "🎯"}
        
        message = f"📊 **Your Crypto Bets**\n\n"
        
        for i, bet in enumerate(bets[:8], 1):
            status_icon = status_emoji.get(bet["status"], "❓")
            direction_icon = direction_emoji.get(bet["bet_type"], "🎲")
            
            if bet["status"] == "pending":
                time_left = bet["expires_at"] - datetime.utcnow()
                if time_left.total_seconds() > 0:
                    minutes_left = int(time_left.total_seconds() / 60)
                    time_info = f"⏰ {minutes_left}m left"
                else:
                    time_info = "⏰ Resolving..."
            else:
                if bet["status"] == "won":
                    profit = bet["payout"] - bet["amount"]
                    time_info = f"💰 +{format_currency(profit)}"
                else:
                    time_info = f"💸 -{format_currency(bet['amount'])}"
            
            message += (
                f"{status_icon} **#{bet['id']}** {direction_icon} {bet['symbol']} "
                f"{bet['bet_type'].upper()} {format_currency(bet['amount'])}\n"
                f"   {format_price(bet['current_price'], bet['symbol'])}"
            )
            
            if bet["final_price"]:
                message += f" → {format_price(bet['final_price'], bet['symbol'])}"
            
            message += f" | {time_info}\n\n"
        
        if len(bets) > 8:
            message += f"... and {len(bets) - 8} more bets\n\n"
        
        # Add filter buttons
        keyboard = [
            [
                InlineKeyboardButton("⏳ Pending", callback_data="crypto_bets_pending"),
                InlineKeyboardButton("✅ Won", callback_data="crypto_bets_won"),
                InlineKeyboardButton("❌ Lost", callback_data="crypto_bets_lost"),
            ],
            [
                InlineKeyboardButton("💰 Balance", callback_data="crypto_balance"),
                InlineKeyboardButton("🔄 Refresh", callback_data="crypto_bets_all"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error("Error showing crypto bets", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading your bets."
        )


@auth_check
async def crypto_leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show crypto betting leaderboard."""
    
    if not update.message or not update.effective_user:
        return
    
    try:
        leaderboard = await crypto_service.get_leaderboard(limit=10)
        
        if not leaderboard:
            await update.message.reply_text(
                "🏆 **Leaderboard Empty**\n\n"
                "Be the first to start betting!",
                parse_mode="Markdown"
            )
            return
        
        message = "🏆 **Crypto Betting Leaderboard**\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user in enumerate(leaderboard, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            
            # Anonymize user IDs (show only last 3 digits)
            user_display = f"User{str(user['user_id'])[-3:]}"
            
            message += (
                f"{medal} **{user_display}**\n"
                f"   💰 {format_currency(user['balance'])} | "
                f"🔥 {user['win_streak']} | "
                f"🎲 {user['total_bets']} bets\n\n"
            )
        
        message += "💡 Climb the ranks by smart betting!"
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error showing leaderboard", error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading the leaderboard."
        )


async def handle_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle crypto-related callback queries."""
    
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    callback_data = query.data
    
    try:
        if callback_data == "crypto_balance":
            # Show balance inline
            balance_data = await crypto_service.get_user_balance(user_id)
            
            balance_text = (
                f"💰 Balance: {format_currency(balance_data['balance'])}\n"
                f"📊 P/L: {'+' if balance_data['profit_loss'] >= 0 else ''}"
                f"{format_currency(balance_data['profit_loss'])}\n"
                f"🎯 Win Rate: {balance_data['win_rate']:.1f}%"
            )
            
            await query.answer(balance_text, show_alert=True)
        
        elif callback_data.startswith("bet_"):
            # Quick bet: bet_BTC_up_10_60
            parts = callback_data.split("_")
            if len(parts) >= 5:
                symbol = parts[1]
                bet_type = parts[2]
                amount = float(parts[3])
                duration = int(parts[4])
                
                try:
                    bet_result = await crypto_service.place_bet(
                        user_id=user_id,
                        chat_id=chat_id,
                        symbol=symbol,
                        bet_type=bet_type,
                        amount=amount,
                        duration_minutes=duration
                    )
                    
                    if bet_result:
                        direction_emoji = {"up": "📈", "down": "📉", "exact": "🎯"}[bet_type]
                        
                        success_text = (
                            f"🎲 Bet Placed!\n"
                            f"{direction_emoji} {symbol} {bet_type.upper()} "
                            f"{format_currency(amount)}\n"
                            f"⏰ {duration}m | ID: {bet_result['bet_id']}"
                        )
                        
                        await query.answer(success_text, show_alert=True)
                
                except APIError as e:
                    await query.answer(f"❌ {str(e)}", show_alert=True)
        
        elif callback_data.startswith("crypto_bets_"):
            status = callback_data.replace("crypto_bets_", "")
            if status == "all":
                status = None
            
            # This would normally update the message, simplified for callback
            await query.answer(f"Filtering bets: {status or 'all'}")
        
        elif callback_data.startswith("convert_"):
            # Handle quick conversion: convert_1_BTC_USD
            parts = callback_data.split("_")
            if len(parts) == 4:
                try:
                    amount = float(parts[1])
                    from_symbol = parts[2]
                    to_symbol = parts[3]
                    
                    conversion_result = await crypto_service.convert_crypto(from_symbol, to_symbol, amount)
                    
                    if conversion_result:
                        converted_amount = conversion_result["converted_amount"]
                        
                        if conversion_result["is_fiat"]:
                            if to_symbol in ["USD", "EUR", "GBP", "AUD", "CAD", "CHF"]:
                                to_display = format_currency(converted_amount)
                            elif to_symbol in ["JPY", "CNY", "INR"]:
                                to_display = f"{converted_amount:,.0f} {to_symbol}"
                            else:
                                to_display = f"{converted_amount:,.8f} {to_symbol}"
                        else:
                            to_display = f"{converted_amount:,.8f} {to_symbol}"
                        
                        success_text = (
                            f"💱 Conversion Result\n"
                            f"{amount} {from_symbol} = {to_display}"
                        )
                        
                        await query.answer(success_text, show_alert=True)
                    else:
                        await query.answer("❌ Conversion failed", show_alert=True)
                        
                except Exception as e:
                    logger.error("Error in conversion callback", error=str(e))
                    await query.answer("❌ Conversion error", show_alert=True)
        
        else:
            await query.answer("❓ Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error("Error handling crypto callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)


@auth_check
async def crypto_convert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert between cryptocurrencies and fiat currencies."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "💱 **Crypto Converter**\n\n"
            "Usage: `/convert <amount> <from> <to>`\n\n"
            "**Examples:**\n"
            "• `/convert 1 BTC USD` - Convert 1 BTC to USD\n"
            "• `/convert 100 USD BTC` - Convert $100 to BTC\n"
            "• `/convert 1 BTC ETH` - Convert 1 BTC to ETH\n"
            "• `/convert 1000 EUR BTC` - Convert €1000 to BTC\n\n"
            "**Supported Cryptocurrencies:**\n"
            "BTC, ETH, BNB, ADA, DOT, LINK, LTC, BCH, XRP, DOGE\n\n"
            "**Supported Fiat Currencies:**\n"
            "USD, EUR, GBP, JPY, AUD, CAD, CHF, CNY, INR",
            parse_mode="Markdown"
        )
        return
    
    try:
        amount = float(context.args[0])
        from_symbol = context.args[1].upper()
        to_symbol = context.args[2].upper()
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be greater than zero.")
            return
        
        # Perform conversion
        conversion_result = await crypto_service.convert_crypto(from_symbol, to_symbol, amount)
        
        if not conversion_result:
            await update.message.reply_text(
                f"❌ Unable to convert `{from_symbol}` to `{to_symbol}`.\n\n"
                f"Please check that both symbols are supported.",
                parse_mode="Markdown"
            )
            return
        
        # Format the result
        from_amount = conversion_result["from_amount"]
        converted_amount = conversion_result["converted_amount"]
        from_price = conversion_result["from_price"]
        to_price = conversion_result["to_price"]
        
        # Format amounts based on currency type
        if conversion_result["is_fiat"]:
            if from_symbol in ["USD", "EUR", "GBP", "AUD", "CAD", "CHF"]:
                from_display = format_currency(from_amount)
            elif from_symbol in ["JPY", "CNY", "INR"]:
                from_display = f"{from_amount:,.0f} {from_symbol}"
            else:
                from_display = f"{from_amount:,.8f} {from_symbol}"
            
            if to_symbol in ["USD", "EUR", "GBP", "AUD", "CAD", "CHF"]:
                to_display = format_currency(converted_amount)
            elif to_symbol in ["JPY", "CNY", "INR"]:
                to_display = f"{converted_amount:,.0f} {to_symbol}"
            else:
                to_display = f"{converted_amount:,.8f} {to_symbol}"
        else:
            # Crypto to crypto
            from_display = f"{from_amount:,.8f} {from_symbol}"
            to_display = f"{converted_amount:,.8f} {to_symbol}"
        
        # Create conversion message
        conversion_rate = converted_amount / from_amount
        
        message = (
            f"💱 **Crypto Conversion**\n\n"
            f"📊 **{from_display}**\n"
            f"🔄 **= {to_display}**\n\n"
            f"📈 **Current Prices:**\n"
            f"• {from_symbol}: {format_price(from_price, from_symbol)}\n"
            f"• {to_symbol}: {format_price(to_price, to_symbol) if not conversion_result['is_fiat'] else f'{to_price:.4f}'}\n\n"
            f"⚡ **Conversion Rate:**\n"
            f"1 {from_symbol} = {conversion_rate:,.8f} {to_symbol}"
        )
        
        # Add conversion buttons for quick operations
        popular_pairs = [
            ("BTC", "USD"), ("ETH", "USD"), ("BNB", "USD"),
            ("BTC", "EUR"), ("ETH", "EUR"), ("USD", "BTC")
        ]
        
        keyboard = []
        for i in range(0, len(popular_pairs), 2):
            row = []
            for j in range(2):
                if i + j < len(popular_pairs):
                    from_curr, to_curr = popular_pairs[i + j]
                    row.append(InlineKeyboardButton(
                        f"{from_curr}→{to_curr}", 
                        callback_data=f"convert_1_{from_curr}_{to_curr}"
                    ))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        logger.info("Crypto conversion", user_id=user_id, from_symbol=from_symbol, 
                   to_symbol=to_symbol, amount=amount, converted_amount=converted_amount)
        
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid numeric amount.")
    except Exception as e:
        logger.error("Error converting crypto", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while converting. Please try again."
        )