"""Integration tests for the bot."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bot.core.app import TelegramBotApp
from bot.core.config import Settings


@pytest.mark.asyncio
async def test_bot_app_setup():
    """Test bot application setup."""
    
    # Create test settings
    settings = Settings(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        database_url="sqlite:///:memory:",
        environment="testing"
    )
    
    with patch('bot.core.app.settings', settings), \
         patch('bot.core.app.db_manager') as mock_db:
        
        mock_db.create_tables = AsyncMock()
        
        app = TelegramBotApp()
        
        # Mock the ApplicationBuilder
        with patch('bot.core.app.ApplicationBuilder') as mock_builder:
            mock_application = MagicMock()
            mock_builder.return_value.token.return_value.concurrent_updates.return_value.build.return_value = mock_application
            
            await app.setup()
            
            # Verify database tables were created
            mock_db.create_tables.assert_called_once()
            
            # Verify application was built
            mock_builder.assert_called_once()
            
            # Verify handlers were registered
            assert mock_application.add_handler.call_count > 0
            assert mock_application.add_error_handler.called


@pytest.mark.asyncio
async def test_bot_app_shutdown():
    """Test bot application shutdown."""
    
    settings = Settings(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        database_url="sqlite:///:memory:",
        environment="testing"
    )
    
    with patch('bot.core.app.settings', settings), \
         patch('bot.core.app.db_manager') as mock_db:
        
        mock_db.close = AsyncMock()
        
        app = TelegramBotApp()
        
        # Mock application
        mock_application = MagicMock()
        mock_application.stop = AsyncMock()
        mock_application.shutdown = AsyncMock()
        app.application = mock_application
        
        await app.shutdown()
        
        # Verify application was stopped and shut down
        mock_application.stop.assert_called_once()
        mock_application.shutdown.assert_called_once()
        
        # Verify database connections were closed
        mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_bot_end_to_end_message():
    """Test end-to-end message handling."""
    
    # This would be a more complex integration test
    # that tests the entire flow from receiving a message
    # to sending a response
    
    settings = Settings(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        database_url="sqlite:///:memory:",
        environment="testing"
    )
    
    with patch('bot.core.app.settings', settings), \
         patch('bot.core.app.db_manager') as mock_db, \
         patch('bot.handlers.messages.openai_service') as mock_openai, \
         patch('bot.handlers.messages.user_service') as mock_user_service, \
         patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter:
        
        # Setup mocks
        mock_db.create_tables = AsyncMock()
        mock_openai.generate_response = AsyncMock(return_value="Test AI response")
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        
        # Create bot app
        app = TelegramBotApp()
        
        # Mock Telegram components
        with patch('bot.core.app.ApplicationBuilder') as mock_builder:
            mock_application = MagicMock()
            mock_builder.return_value.token.return_value.concurrent_updates.return_value.build.return_value = mock_application
            
            await app.setup()
            
            # Simulate a message update
            update = MagicMock()
            update.message = MagicMock()
            update.message.text = "Hello bot!"
            update.message.reply_text = AsyncMock()
            update.effective_user = MagicMock()
            update.effective_user.id = 123
            update.effective_user.username = "testuser"
            update.effective_chat = MagicMock()
            update.effective_chat.id = 456
            
            context = MagicMock()
            context.bot = MagicMock()
            context.bot.send_chat_action = AsyncMock()
            
            # Import and call the message handler directly
            from bot.handlers.messages import message_handler
            await message_handler(update, context)
            
            # Verify the flow
            mock_rate_limiter.check_rate_limit.assert_called_once_with(123)
            mock_user_service.create_or_update_user.assert_called_once()
            mock_user_service.log_message.assert_called_once()
            mock_openai.generate_response.assert_called_once()
            
            # Verify response was sent
            update.message.reply_text.assert_called_once_with(
                "Test AI response",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )


@pytest.mark.asyncio  
async def test_database_integration():
    """Test database operations integration."""
    
    from bot.core.database import DatabaseManager, User
    from bot.services.user_service import UserService
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    
    # Create in-memory database
    db = DatabaseManager()
    db.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    db.async_session = async_sessionmaker(db.engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables
    await db.create_tables()
    
    # Create user service with test database
    user_service = UserService()
    user_service.db_manager = db
    
    try:
        # Test user creation
        user = await user_service.create_or_update_user(
            telegram_id=123,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        assert user.telegram_id == 123
        assert user.username == "testuser"
        
        # Test user retrieval
        retrieved_user = await user_service.get_user_by_telegram_id(123)
        assert retrieved_user is not None
        assert retrieved_user.telegram_id == 123
        
        # Test user update
        updated_user = await user_service.create_or_update_user(
            telegram_id=123,
            username="newusername",
            first_name="NewTest"
        )
        
        assert updated_user.username == "newusername"
        assert updated_user.first_name == "NewTest"
        
        # Test admin setting
        result = await user_service.set_user_admin(123, True)
        assert result is True
        
        admin_user = await user_service.get_user_by_telegram_id(123)
        assert admin_user.is_admin is True
        
        # Test message logging
        message = await user_service.log_message(
            user_id=123,
            chat_id=456,
            message_text="Test message"
        )
        
        assert message is not None
        assert message.text == "Test message"
        
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_openai_service_integration():
    """Test OpenAI service integration."""
    
    # Note: This test would require actual API credentials to run
    # In practice, you might want to use VCR or similar for recording API responses
    
    from bot.services.openai_service import OpenAIService
    
    # Mock the OpenAI client to avoid real API calls
    with patch('openai.AsyncOpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response"
        mock_response.usage.total_tokens = 50
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        service = OpenAIService()
        
        response = await service.generate_response(
            message="Hello, AI!",
            user_id=123,
            username="testuser"
        )
        
        assert response == "This is a test response"
        
        # Verify conversation history was updated
        assert 123 in service.conversation_history
        history = service.conversation_history[123]
        assert len(history) == 2  # user message + AI response
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello, AI!"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "This is a test response"