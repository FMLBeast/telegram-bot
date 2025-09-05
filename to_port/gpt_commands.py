import openai
import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes
from config.logging_config import logger
from config import OPENAI_API_KEY

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

async def process_message_with_gpt(message):
    prompt = f"{message}"
    max_retries = 5
    for attempt in range(max_retries):
        try:
            completion = await client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            chatgpt_answer = completion.choices[0].message.content.strip()
            return chatgpt_answer
        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep((2 ** attempt) + (random.randint(0, 1000) / 1000))
            else:
                raise
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

async def ask_gpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a query to ask. Usage: /ask_gpt <your question>")
        return

    logger.info(f"Asking GPT-4: {query}")
    await update.message.reply_text(f"🤖 Asking GPT-4: {query}...")
    gpt_response = await process_message_with_gpt(query)

    # Ensure the response fits within Telegram's message limit
    if len(gpt_response) > 4096:
        gpt_response = gpt_response[:4093] + "..."

    await update.message.reply_text(gpt_response)
