"""Pytest configuration and fixtures."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from bot.core.config import Settings
from bot.core.database import DatabaseManager, Base
from bot.services.openai_service import OpenAIService
from bot.services.user_service import UserService
from bot.services.activity_service import ActivityService
from bot.services.mood_service import MoodService
from bot.services.synonym_service import SynonymService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        database_url="sqlite:///:memory:",
        environment="testing",
        log_level="DEBUG",
    )


@pytest.fixture
async def test_db(test_settings) -> AsyncGenerator[DatabaseManager, None]:
    """Create test database manager."""
    db = DatabaseManager()
    db.engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    db.async_session = async_sessionmaker(
        db.engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield db
    
    # Cleanup
    await db.close()


@pytest.fixture
def mock_telegram_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "test message"
    update.message.reply_text = AsyncMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.effective_chat = MagicMock()
    update.effective_chat.id = 67890
    return update


@pytest.fixture
def mock_telegram_context():
    """Create mock Telegram context."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.send_chat_action = AsyncMock()
    return context


@pytest.fixture
def mock_openai_service():
    """Create mock OpenAI service."""
    service = MagicMock(spec=OpenAIService)
    service.generate_response = AsyncMock(return_value="Test AI response")
    service.generate_image = AsyncMock(return_value="https://example.com/image.jpg")
    service.analyze_sentiment = AsyncMock(return_value={
        "sentiment": "positive",
        "confidence": 0.8,
        "explanation": "Test analysis"
    })
    return service


@pytest.fixture
async def user_service(test_db):
    """Create user service with test database."""
    service = UserService()
    service.db_manager = test_db
    return service


@pytest.fixture
async def activity_service(test_db):
    """Create activity service with test database."""
    service = ActivityService()
    service.db_manager = test_db
    return service


@pytest.fixture
async def mood_service(mock_openai_service, test_db):
    """Create mood service with test database and mock OpenAI service."""
    service = MoodService()
    service.openai_service = mock_openai_service
    service.db_manager = test_db
    return service


@pytest.fixture
def synonym_service():
    """Create synonym service with temporary data file."""
    import tempfile
    import os
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.write('{}')
    temp_file.close()
    
    service = SynonymService()
    service.data_file = temp_file.name
    
    yield service
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


# Auto-use fixtures for common mocks
@pytest.fixture(autouse=True)
def mock_structlog():
    """Mock structlog for tests."""
    import structlog
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr(structlog, "get_logger", lambda name: logger)
        yield logger