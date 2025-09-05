import logging
import os
from pathlib import Path
from typing import Optional, Set

from telegram.ext import (
    Application, PicklePersistence
)

from config import TIDDIES_AND_TITS_BOT_TOKEN
from database import db_conn, load_authorized_channels
from config.logging_config import logger
from .casino_handler import CasinoHandler

class BaseTelegramBot:
    def __init__(self):
        # Core attributes
        self.token = TIDDIES_AND_TITS_BOT_TOKEN
        self.casino_handler = None
        self.authorized_channels: Set[int] = set()
        self.persistence = None
        self.application: Optional[Application] = None
        
        # Paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.LOCAL_MP4_PATH = 'C:\\Users\\Administrator\\scripts\\telegram_madness\\telegram_media\\spit_hawk.mp4'
        self.GIF_PATH = 'C:\\Users\\Administrator\\scripts\\telegram_madness\\telegram_media\\war.gif'
        
        # Constants
        self.USER_ID = 6921082971
        self.KEYWORDS = ['hawk', 'spit', 'hawk tuag', 'thang']
        self.KEYWORDS2 = ['jerk', 'soggybiscuit', 'cookie', 'war']
        
        # Initialize components
        self._init_logging()
        self._init_persistence()
        self._load_authorized_channels()
        
    def _init_logging(self) -> None:
        """Initialize logging configuration"""
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('apscheduler').setLevel(logging.WARNING)
        logging.getLogger('telegram').setLevel(logging.WARNING)
        
    def _init_persistence(self) -> None:
        """Initialize bot persistence"""
        persistence_path = Path(self.script_dir) / 'bot_persistence'
        persistence_path.mkdir(exist_ok=True)
        
        self.persistence = PicklePersistence(
            filepath=str(persistence_path / 'conversation_states.pickle'),
            store_data=True
        )
        
    def _load_authorized_channels(self) -> None:
        """Load authorized channels from database"""
        self.authorized_channels = load_authorized_channels()
        
    def _init_application(self) -> None:
        """Initialize the application with proper configuration"""
        if not self.token:
            raise ValueError("No TIDDIES_AND_TITS_BOT_TOKEN found in environment variables")

        self.application = (
            Application.builder()
            .token(self.token)
            .persistence(self.persistence)
            .build()
        )
        
        # Initialize casino handler
        self.casino_handler = CasinoHandler(db_conn)

# Keep original global variables for compatibility
casino_handler = None
USER_ID = 6921082971