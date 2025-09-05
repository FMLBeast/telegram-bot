import openai
import logging
import asyncio
import random
import re          # Imported for regular expressions
import copy        # Imported for deep copying
from config import OPENAI_API_KEY
from telegram import Bot
from telegram.error import TelegramError

# Initialize OpenAI client
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

# Initialize Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Telegram Bot Initialization
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # Replace with your actual token
bot = Bot(token=TELEGRAM_TOKEN)

vip_data = {
    "Bronze": {
        "VIP 2-7": {
            "Level Up Bonus": {"VIP 2": 0.04, "VIP 3": 0.05, "VIP 4": 0.1, "VIP 5": 0.2, "VIP 6": 0.3, "VIP 7": 0.35},
            "XP Requirements": {"VIP 2": 100, "VIP 3": 200, "VIP 4": 1000, "VIP 5": 2000, "VIP 6": 3000, "VIP 7": 4000},
            "Raining": "Rain algorithm rewards for highly active players in chat.",
            "Coin Drops": "Create a coin drop for friends in the chat."
        }
    },
    "Silver": {
        "VIP 8-21": {
            "Level Up Bonus": {"VIP 8": 0.7, "VIP 9": 0.8, "VIP 10": 0.9, "VIP 11": 1.0, "VIP 12": 1.1, "VIP 13": 1.2, "VIP 14": 1.3, "VIP 15": 1.4, "VIP 16": 1.5, "VIP 17": 1.6, "VIP 18": 1.7, "VIP 19": 1.8, "VIP 20": 1.9, "VIP 21": 2.0},
            "XP Requirements": {"VIP 8": 5000, "VIP 9": 7000, "VIP 10": 9000, "VIP 11": 11000, "VIP 12": 13000, "VIP 13": 15000, "VIP 14": 17000, "VIP 15": 21000, "VIP 16": 25000, "VIP 17": 29000, "VIP 18": 33000, "VIP 19": 37000, "VIP 20": 41000, "VIP 21": 45000},
            "Tips": "Show appreciation for other players by sending them tips.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up."
        }
    },
    "Gold": {
        "VIP 22-37": {
            "Level Up Bonus": {"VIP 22": 3.0, "VIP 23": 4.0, "VIP 24": 5.0, "VIP 25": 6.0, "VIP 26": 7.0, "VIP 27": 8.0, "VIP 28": 9.0, "VIP 29": 10.0, "VIP 30": 12.0, "VIP 31": 14.0, "VIP 32": 16.0, "VIP 33": 18.0, "VIP 34": 20.0, "VIP 35": 22.0, "VIP 36": 24.0, "VIP 37": 26.0},
            "XP Requirements": {"VIP 22": 49000, "VIP 23": 59000, "VIP 24": 69000, "VIP 25": 79000, "VIP 26": 89000, "VIP 27": 99000, "VIP 28": 109000, "VIP 29": 119000, "VIP 30": 129000, "VIP 31": 153000, "VIP 32": 177000, "VIP 33": 201000, "VIP 34": 225000, "VIP 35": 249000, "VIP 36": 273000, "VIP 37": 297000},
            "Recharge": "Activate your Recharge and claim 10-16% bonus of wager*1% for 7 days in a row.",
            "Weekly Cashback": "Receive your weekly bonus of Wager*0.0005 approximately based on your wager amount.",
            "Monthly Cashback": "Receive your monthly bonus of Wager*0.0003 approximately based on your wager amount.",
            "Sports Weekly Bonus": "Additional rewards and benefits for sports bettors.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up."
        }
    },
    "Platinum I": {
        "VIP 38-55": {
            "Level Up Bonus": {"VIP 38": 30.0, "VIP 39": 35.0, "VIP 40": 40.0, "VIP 41": 50.0, "VIP 42": 60.0, "VIP 43": 70.0, "VIP 44": 80.0, "VIP 45": 90.0, "VIP 46": 100.0, "VIP 47": 110.0, "VIP 48": 120.0, "VIP 49": 130.0, "VIP 50": 140.0, "VIP 51": 150.0, "VIP 52": 160.0, "VIP 53": 170.0, "VIP 54": 180.0, "VIP 55": 190.0},
            "XP Requirements": {"VIP 38": 321000, "VIP 39": 377000, "VIP 40": 433000, "VIP 41": 489000, "VIP 42": 545000, "VIP 43": 601000, "VIP 44": 657000, "VIP 45": 713000, "VIP 46": 769000, "VIP 47": 897000, "VIP 48": 1025000, "VIP 49": 1153000, "VIP 50": 1281000, "VIP 51": 1409000, "VIP 52": 1537000, "VIP 53": 1665000, "VIP 54": 1793000, "VIP 55": 2081000},
            "Recharge": "Activate your Recharge and claim 12-18% bonus of wager*1% for 7 days in a row.",
            "Weekly Cashback": "Receive your weekly bonus of Wager**0.0008 approximately based on your wager amount.",
            "Monthly Cashback": "Receive your monthly bonus of Wager**0.00035 approximately based on your wager amount.",
            "Sports Weekly Bonus": "Additional rewards and benefits for sports bettors.",
            "No-fee Withdrawal": "Seamless withdrawals with zero fees for cryptocurrency.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up."
        }
    },
    "Platinum II": {
        "VIP 56-69": {
            "Level Up Bonus": {"VIP 56": 200.0, "VIP 57": 220.0, "VIP 58": 240.0, "VIP 59": 260.0, "VIP 60": 280.0, "VIP 61": 300.0, "VIP 62": 350.0, "VIP 63": 400.0, "VIP 64": 450.0, "VIP 65": 500.0, "VIP 66": 550.0, "VIP 67": 600.0, "VIP 68": 700.0, "VIP 69": 800.0},
            "XP Requirements": {"VIP 56": 2369000, "VIP 57": 2657000, "VIP 58": 2945000, "VIP 59": 3233000, "VIP 60": 3521000, "VIP 61": 3809000, "VIP 62": 4097000, "VIP 63": 4737000, "VIP 64": 5377000, "VIP 65": 6017000, "VIP 66": 6657000, "VIP 67": 7297000, "VIP 68": 7937000, "VIP 69": 8577000},
            "Recharge": "Activate your Recharge and claim 14-20% bonus of wager*1% for 7 days in a row.",
            "Weekly Cashback": "Receive your weekly bonus of Wager*0.0008 approximately based on your wager amount.",
            "Monthly Cashback": "Receive your monthly bonus of Wager*0.0004 approximately based on your wager amount.",
            "Sports Weekly Bonus": "Additional rewards and benefits for sports bettors.",
            "No-fee Withdrawal": "Seamless withdrawals with zero fees for cryptocurrency.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up."
        }
    },
    "Diamond I": {
        "SVIP 1-15": {
            "Level Up Bonus": {"SVIP 1": 1200.0, "SVIP 2": 1300.0, "SVIP 3": 1400.0, "SVIP 4": 1500.0, "SVIP 5": 1600.0, "SVIP 6": 1700.0, "SVIP 7": 1800.0, "SVIP 8": 2000.0, "SVIP 9": 2200.0, "SVIP 10": 2300.0, "SVIP 11": 2500.0, "SVIP 12": 2600.0, "SVIP 13": 2700.0, "SVIP 14": 2800.0, "SVIP 15": 3000.0},
            "XP Requirements": {"SVIP 1": 9217000, "SVIP 2": 10625000, "SVIP 3": 12033000, "SVIP 4": 13441000, "SVIP 5": 14849000, "SVIP 6": 16257000, "SVIP 7": 17665000, "SVIP 8": 19073000, "SVIP 9": 20481000, "SVIP 10": 23553000, "SVIP 11": 26625000, "SVIP 12": 29697000, "SVIP 13": 32769000, "SVIP 14": 35841000, "SVIP 15": 38913000},
            "Recharge": "Activate your Recharge and claim 16-22% bonus of wager*1% for 7 days in a row.",
            "Weekly Cashback": "Receive your weekly bonus of Wager**0.0008 approximately based on your wager amount.",
            "Monthly Cashback": "Receive your monthly bonus of Wager*0.0005 approximately based on your wager amount.",
            "Sports Weekly Bonus": "Additional rewards and benefits for sports bettors.",
            "Exclusive SVIP perks": "Uncover unimaginable surprises as our Diamond VIP.",
            "Luxury giveaway": "Join for an exclusive chance to win marvelous surprises.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up.",
            "VIP Host": "Enjoy on-demand service and exclusive benefits."
        }
    },
    "Diamond II": {
        "SVIP 16-37": {
            "Level Up Bonus": {"SVIP 16": 3200.0, "SVIP 17": 3600.0, "SVIP 18": 4000.0, "SVIP 19": 4500.0, "SVIP 20": 5000.0, "SVIP 21": 5500.0, "SVIP 22": 6000.0, "SVIP 23": 7000.0, "SVIP 24": 8000.0, "SVIP 25": 9000.0, "SVIP 26": 10000.0, "SVIP 27": 11000.0, "SVIP 28": 12000.0, "SVIP 29": 13000.0, "SVIP 30": 15000.0, "SVIP 31": 18000.0, "SVIP 32": 20000.0, "SVIP 33": 23000.0, "SVIP 34": 26000.0, "SVIP 35": 28000.0, "SVIP 36": 31000.0, "SVIP 37": 35000.0},
            "XP Requirements": {"SVIP 16": 41985000, "SVIP 17": 45057000, "SVIP 18": 51713000, "SVIP 19": 58369000, "SVIP 20": 65025000, "SVIP 21": 71681000, "SVIP 22": 78337000, "SVIP 23": 84993000, "SVIP 24": 91649000, "SVIP 25": 98305000, "SVIP 26": 112641000, "SVIP 27": 126977000, "SVIP 28": 141313000, "SVIP 29": 155649000, "SVIP 30": 169985000, "SVIP 31": 184321000, "SVIP 32": 198657000, "SVIP 33": 212993000, "SVIP 34": 243713000, "SVIP 35": 274433000, "SVIP 36": 305153000, "SVIP 37": 335873000},
            "Recharge": "Activate your Recharge and claim 18-24% bonus of wager*1% for 7 days in a row.",
            "Weekly Cashback": "Receive your weekly bonus of Wager*0.0008 approximately based on your wager amount.",
            "Monthly Cashback": "Receive your monthly bonus of Wager*0.0005 approximately based on your wager amount.",
            "Sports Weekly Bonus": "Additional rewards and benefits for sports bettors.",
            "Exclusive SVIP perks": "Uncover unimaginable surprises as our Diamond VIP.",
            "Luxury giveaway": "Join for an exclusive chance to win marvelous surprises.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up.",
            "VIP Host": "Enjoy on-demand service and exclusive benefits."
        }
    },
    "Diamond III": {
        "SVIP 38-75": {
            "Level Up Bonus": {"SVIP 38": 38000.0, "SVIP 39": 40000.0, "SVIP 40": 42000.0, "SVIP 41": 45000.0, "SVIP 42": 48000.0, "SVIP 43": 50000.0, "SVIP 44": 53000.0, "SVIP 45": 56000.0, "SVIP 46": 60000.0, "SVIP 47": 65000.0, "SVIP 48": 70000.0, "SVIP 49": 75000.0, "SVIP 50": 80000.0, "SVIP 51": 90000.0, "SVIP 52": 100000.0, "SVIP 53": 120000.0, "SVIP 54": 140000.0, "SVIP 55": 160000.0, "SVIP 56": 180000.0, "SVIP 57": 200000.0, "SVIP 58": 220000.0, "SVIP 59": 240000.0, "SVIP 60": 260000.0, "SVIP 61": 280000.0, "SVIP 62": 300000.0, "SVIP 63": 320000.0, "SVIP 64": 340000.0, "SVIP 65": 360000.0, "SVIP 66": 380000.0, "SVIP 67": 400000.0, "SVIP 68": 420000.0, "SVIP 69": 440000.0, "SVIP 70": 460000.0, "SVIP 71": 480000.0, "SVIP 72": 500000.0, "SVIP 73": 520000.0, "SVIP 74": 540000.0, "SVIP 75": 560000.0},
            "XP Requirements": {"SVIP 38": 366593000, "SVIP 39": 397313000, "SVIP 40": 428033000, "SVIP 41": 458753000, "SVIP 42": 524289000, "SVIP 43": 589825000, "SVIP 44": 655361000, "SVIP 45": 720897000, "SVIP 46": 786433000, "SVIP 47": 851969000, "SVIP 48": 917505000, "SVIP 49": 983041000, "SVIP 50": 1122305000, "SVIP 51": 1261569000, "SVIP 52": 1400833000, "SVIP 53": 1540097000, "SVIP 54": 1679361000, "SVIP 55": 1818625000, "SVIP 56": 1957889000, "SVIP 57": 2097153000, "SVIP 58": 2392065000, "SVIP 59": 2686977000, "SVIP 60": 2981889000, "SVIP 61": 3276801000, "SVIP 62": 3571713000, "SVIP 63": 3866625000, "SVIP 64": 4161537000, "SVIP 65": 4456449000, "SVIP 66": 5079041000, "SVIP 67": 5701633000, "SVIP 68": 6324225000, "SVIP 69": 6946817000, "SVIP 70": 7569409000, "SVIP 71": 8192001000, "SVIP 72": 8814593000, "SVIP 73": 9437185000, "SVIP 74": 10747905000, "SVIP 75": 12058625000},
            "Recharge": "Activate your Recharge and claim 20-25% bonus of wager*1% for 7 days in a row.",
            "Weekly Cashback": "Receive your weekly bonus of Wager*0.0008 approximately based on your wager amount.",
            "Monthly Cashback": "Receive your monthly bonus of Wager**0.0005 approximately based on your wager amount.",
            "Sports Weekly Bonus": "Additional rewards and benefits for sports bettors.",
            "Exclusive SVIP perks": "Uncover unimaginable surprises as our Diamond VIP.",
            "Luxury giveaway": "Join for an exclusive chance to win marvelous surprises.",
            "VIP Spin": "Starting from VIP level 8, you will receive an extra lucky spin with each level-up.",
            "VIP Host": "Enjoy on-demand service and exclusive benefits."
        }
    },
    "General information": {
        "EXCLUSIVE VIP BENEFITS": "Join our VIP Club now and get ready to be showered with gifts, giveaways, and amazing features! Experience the thrill of higher cash back and exclusive rewards that are sure to leave you amazed.",
        "NO-FEE WITHDRAWAL FOR CRYPTOCURRENCY": "Unlock the No-fee withdrawal for Cryptocurrency perks at VIP 38 and withdraw your winnings with ease and no additional charges.",
        "REWARDING LUCKY SPIN": "Spin the wheel and receive bigger prizes with our exciting Lucky Spin as you level up.",
        "DEDICATED VIP HOST": "Unlock the No-fee withdrawal perks at VIP 38 and enjoy your VIP host’s personalized attention and exclusive benefits.",
        "AMAZING LEVEL UP BONUS": "A surprise reward awaits and gets unlocked multiple times as you level up.",
        "FUN TIPS & RAINING": "Show appreciation with Tips, or get lucky with Coin Drops for a chance to win rewards.",
        "Sports Weekly Bonus": "In addition to our existing Weekly Bonus for VIP level 22+ players, we are now introducing the BC Sports Club weekly bonus as an additional perk for sports bettors. The new Sport bonus is specific only to Sport Wager and is calculated based on the player's wagering amount from Saturday to Friday, and distributed automatically every Saturday. With the introduction of the BC Sports Club bonuses, our VIP level 22+ players can now enjoy even more rewards and a thrilling sports betting experience! BC Sports Club offers a range of weekend bonuses based on your weekly wager amount in our Sportsbook. Wager $500 or more from Saturday to Friday and receive a $5 Weekend Bonus! Wager $2,500 or more and receive a $30 Weekend Bonus! Wager $5,000 or more and receive a $70 Weekend Bonus! Wager $10,000 or more and receive a $150 Weekend Bonus! These bonuses apply to all markets and odds in our Sportsbook, giving you more opportunities to win big! The weekly wager is calculated from the previous Saturday 00:00hrs to Friday 23:59hrs (UTC)."
    }
}

def escape_markdown(text):
    """
    Escapes special characters for Telegram MarkdownV2.
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

# Sanitize vip_data to escape MarkdownV2 characters
sanitized_vip_data = copy.deepcopy(vip_data)

for category, details in sanitized_vip_data.items():
    if not isinstance(details, dict):
        continue  # Skip if details is not a dict
    for vip_range, vip_info in details.items():
        if not isinstance(vip_info, dict):
            continue  # Skip if vip_info is not a dict
        for key, value in vip_info.items():
            if isinstance(value, str):
                sanitized_vip_data[category][vip_range][key] = escape_markdown(value)

async def process_message_with_gpt(message):
    context = {
        "vip_data": sanitized_vip_data,
        "message": message
    }
    prompt = f"""
You are a helpful assistant with a friendly and professional tone. You have the following information to answer questions from users:
{context}

User query: {message}

Please provide the answer in a concise, friendly, and engaging manner, including appropriate emojis and clear formatting where necessary.
Ensure all calculations are precise and correctly formatted. If the information is not available in the provided context, respond with "I don't have the information you are looking for."
"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            completion = await client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a friendly and professional assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            chatgpt_answer = completion.choices[0].message.content.strip()
            # Escape the response before sending
            chatgpt_answer = escape_markdown(chatgpt_answer)
            return chatgpt_answer
        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + (random.randint(0, 1000) / 1000)
                logger.info(f"Retrying in {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)
            else:
                logger.error("Max retries exceeded for RateLimitError.")
                raise
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

async def send_message(chat_id, text):
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='MarkdownV2'  # Ensure this matches the escaping
        )
    except TelegramError as e:
        logger.error(f"Failed to send message: {e}")

# Example Usage
async def handle_user_message(chat_id, user_message):
    try:
        gpt_response = await process_message_with_gpt(user_message)
        await send_message(chat_id, gpt_response)
    except Exception as e:
        logger.err
