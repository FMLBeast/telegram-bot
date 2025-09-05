from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

def format_number(n):
    """Format number with appropriate suffixes."""
    if abs(n) >= 1e9:
        return f"{n/1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"{n/1e6:.2f}M"
    if abs(n) >= 1e3:
        return f"{n/1e3:.2f}K"
    return f"{n:.2f}"

def calculate_bets(base_bet, multiplier, increase_percentage, iterations=20):
    bets = [base_bet]
    net_results = []
    total = 0

    for i in range(1, iterations + 20):
        net_result = bets[-1] * multiplier
        total += net_result
        next_bet = bets[-1] * (1 + increase_percentage / 100)
        
        bets.append(next_bet)
        net_results.append(net_result)

    return bets[:iterations], net_results, total

async def calculate_bets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        base_bet = float(context.args[0].replace(",", "."))
        multiplier = float(context.args[1].replace(",", "."))
        increase_percentage = float(context.args[2].replace(",", "."))
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Usage: /b2b <base_bet> <multiplier> <increase_percentage>",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    bets, net_results, total = calculate_bets(base_bet, multiplier, increase_percentage)

    # Create header and table with monospace formatting
    result_message = (
        "🎲 *Betting Progression Analysis* 🎲\n\n"
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
            f"│ {str(i):<8}│ {format_number(bet):<10}│ {format_number(net_result):<10}│ "
            f"{format_number(current_total):<10}│\n"
        )

    # Close table
    result_message += (
        "└─────────┴───────────┴───────────┴───────────┘\n"
        "```\n\n"
    )

    # Add summary
    summary = (
        f"📈 *Initial Bet:* `{base_bet}`\n"
        f"📊 *Multiplier:* `{multiplier:.1f}x`\n"
        f"📋 *Increase:* `{increase_percentage:.1f}%`"
    )

    # Send message with proper markdown parsing
    await update.message.reply_text(
        result_message + summary,
        parse_mode=ParseMode.MARKDOWN_V2
    )