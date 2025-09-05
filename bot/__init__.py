"""Modern Telegram Bot Package."""

__version__ = "2.0.0"
__author__ = "Bot Developer"
__email__ = "dev@example.com"

from .core.app import TelegramBotApp
from .core.config import settings

__all__ = ["TelegramBotApp", "settings"]