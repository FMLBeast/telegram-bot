import requests
import time
from config import RAPIDAPI_KEY
from config.logging_config import logger    

# Global variables for caching
fiat_rates = None
crypto_rates = {}
last_fiat_fetch = 0
last_crypto_fetch = {}
FIAT_REFRESH_INTERVAL = 3600  # 1 hour in seconds
CRYPTO_REFRESH_INTERVAL = 300  # 5 minutes in seconds

def fetch_crypto_price(symbol):
    if symbol == 'USDT':
        return 1.00  # Fixed price for stablecoin USDT
        
    current_time = time.time()
    if symbol in crypto_rates and (current_time - last_crypto_fetch.get(symbol, 0)) < CRYPTO_REFRESH_INTERVAL:
        return crypto_rates[symbol]
        
    url = "https://binance43.p.rapidapi.com/ticker/24hr"
    querystring = {"symbol": f"{symbol}USDT"}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "binance43.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code != 200 or 'lastPrice' not in response.json():
        return None
        
    price = float(response.json()['lastPrice'])
    crypto_rates[symbol] = price
    last_crypto_fetch[symbol] = current_time
    return price

def fetch_fiat_rates():
    global fiat_rates, last_fiat_fetch
    current_time = time.time()
    
    if fiat_rates is None or (current_time - last_fiat_fetch) > FIAT_REFRESH_INTERVAL:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url)
        response.raise_for_status()
        fiat_rates = response.json()['rates']
        last_fiat_fetch = current_time
    
    return fiat_rates

def format_number(number):
    """Format number with appropriate decimal places based on its magnitude."""
    if abs(number) < 0.01:
        return f"{number:.8f}"
    elif abs(number) < 1:
        return f"{number:.4f}"
    else:
        return f"{number:,.2f}"

async def convert_crypto(update, context):
    logger.info(f"Received /convert command with args: {context.args}")
    
    if len(context.args) not in [2, 3]:
        await update.message.reply_text(
            "ℹ️ *Usage:*\n" +
            "• `/convert <amount> <from_symbol>` (converts to USD)\n" +
            "• `/convert <amount> <from_symbol> <to_symbol>`\n\n" +
            "_Examples:_\n" +
            "• `/convert 100 BTC`\n" +
            "• `/convert 1.5 ETH BTC`\n" +
            "• `/convert 1000 USD EUR`",
            parse_mode='Markdown'
        )
        return

    try:
        amount = float(context.args[0])
        symbol_from = context.args[1].upper()
        symbol_to = context.args[2].upper() if len(context.args) == 3 else 'USD'

        # Get fiat rates
        fiat_rates = fetch_fiat_rates()
        
        # Initialize variables for conversion
        usd_value = None
        final_value = None
        
        # Convert from currency to USD first
        if symbol_from in fiat_rates:
            usd_value = amount / fiat_rates[symbol_from]
        else:
            price_from = fetch_crypto_price(symbol_from)
            if price_from is None:
                await update.message.reply_text(
                    f"❌ Unable to fetch price for {symbol_from}",
                    parse_mode='Markdown'
                )
                return
            usd_value = amount * price_from

        # Convert USD to target currency
        if symbol_to == 'USD':
            final_value = usd_value
        elif symbol_to in fiat_rates:
            final_value = usd_value * fiat_rates[symbol_to]
        else:
            price_to = fetch_crypto_price(symbol_to)
            if price_to is None:
                await update.message.reply_text(
                    f"❌ Unable to fetch price for {symbol_to}",
                    parse_mode='Markdown'
                )
                return
            final_value = usd_value / price_to

        # Build response
        response = (
            f"💱 *Currency Conversion*\n\n"
            f"*From:* `{format_number(amount)} {symbol_from}`\n"
            f"*To:* `{format_number(final_value)} {symbol_to}`"
        )

        # Add USD value if converting between non-USD currencies
        if symbol_from != 'USD' and symbol_to != 'USD':
            response += f"\n*USD Value:* `${format_number(usd_value)}`"

        # Add PHP conversion for specific chat
        if update.message.chat_id == -1002153368935:
            php_value = usd_value * fiat_rates['PHP']
            response += f"\n*PHP Value:* `₱{format_number(php_value)}`"
        
        response += ""
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please provide a valid amount.",
            parse_mode='Markdown'
        )
    except requests.RequestException as e:
        logger.error(f"Error fetching prices: {e}")
        await update.message.reply_text(
            f"❌ Error fetching prices: {str(e)}",
            parse_mode='Markdown'
        )