"""Main entry point for the Telegram bot."""

import asyncio
import signal
import sys
from typing import NoReturn

from bot.core.app import TelegramBotApp
from bot.core.config import settings
from bot.core.logging import configure_logging, get_logger

# Configure logging first
configure_logging()
logger = get_logger(__name__)


async def main() -> NoReturn:
    """Main function to run the bot."""
    
    logger.info(
        "Starting Telegram Bot",
        version="2.0.0",
        environment=settings.environment,
        python_version=sys.version.split()[0]
    )
    
    # Create bot application
    bot_app = TelegramBotApp()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum: int, frame) -> None:
        logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(bot_app.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Setup the bot
        await bot_app.setup()
        
        # Choose running mode based on configuration
        if settings.webhook_url:
            logger.info("Running bot with webhooks", webhook_url=settings.webhook_url)
            await bot_app.run_webhook(settings.webhook_url, settings.webhook_port)
        else:
            logger.info("Running bot with polling")
            await bot_app.run_polling()
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error in bot", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        await bot_app.shutdown()


def cli_main() -> None:
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user interrupt")
    except Exception as e:
        logger.error("Failed to start bot", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()