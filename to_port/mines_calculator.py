import math
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def mines_multi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) == 2:
        try:
            m = int(args[0])
            d = int(args[1])
        except ValueError:
            await update.message.reply_text("Please provide valid numbers for mines and diamonds.")
            return

        if m + d > 25 or m <= 0 or d <= 0:
            await update.message.reply_text("Mines and diamonds total must be less than or equal to 25, and both must be greater than 0.")
            return

        n = 25
        x = 25 - m

        def combination(n, d):
            return math.comb(n, d)

        first = combination(n, d)
        second = combination(x, d)
        result = 0.99 * (first / second)
        result = round(result, 2)
        win = result
        loss = round(100 / (result - 1), 2)
        chance = round(99 / result, 5)

        response = (
            f"💎 *Multiplier for {m} mines and {d} diamonds is: {result}x*\n"
            f"🎲 *Winning Chance is: {chance}%*\n\n"
            f"🔍 *Close multipliers:*\n"
        )

        close_multipliers = []

        for i in range(max(1, m - 1), min(25, m + 2)):
            for j in range(max(1, d - 1), min(25 - i + 1, d + 2)):
                if i == m and j == d:
                    continue
                close_result = combination(25, j) / (combination(25 - i, j))
                close_result = round(0.99 * close_result, 2)
                close_multipliers.append((i, j, close_result))

        close_multipliers.sort(key=lambda x: abs(x[2] - result))

        for cm in close_multipliers[:4]:
            response += f"🔹 {cm[0]} mines and {cm[1]} diamonds: {cm[2]}x\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    elif len(args) == 1:
        try:
            target_multiplier = float(args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid multiplier.")
            return

        def calculate_multiplier(m, d):
            n = 25
            x = 25 - m
            first = math.comb(n, d)
            second = math.comb(x, d)
            result = 0.99 * (first / second)
            return round(result, 2)

        multipliers = []
        for m in range(1, 25):
            for d in range(1, 25 - m + 1):
                result = calculate_multiplier(m, d)
                multipliers.append((m, d, result))

        multipliers.sort(key=lambda x: abs(x[2] - target_multiplier))

        response = f"💎 *Searching for multipliers close to {target_multiplier}x*\n\n"

        for i, (m, d, result) in enumerate(multipliers[:5]):
            response += f"🔹 {m} mines and {d} diamonds: {result}x\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    else:
        await update.message.reply_text("Usage: /mines_multi <multiplier> or /mines_multi <mines> <diamonds>")

