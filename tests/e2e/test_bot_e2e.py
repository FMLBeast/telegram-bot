"""End-to-end tests for the Telegram bot.

These tests simulate real user interactions with the bot
without requiring an actual Telegram connection.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from bot.core.app import TelegramBotApp
from bot.core.config import Settings


@pytest.mark.asyncio
async def test_full_bot_workflow():
    """Test a complete bot workflow from startup to message handling."""
    
    # Create test environment
    settings = Settings(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        database_url="sqlite:///:memory:",
        environment="testing"
    )
    
    with patch('bot.core.app.settings', settings), \
         patch('bot.core.app.db_manager') as mock_db, \
         patch('bot.core.app.auth_service') as mock_auth:
        
        # Mock all external dependencies
        mock_db.create_tables = AsyncMock()
        mock_db.close = AsyncMock()
        mock_auth.load_authorizations = AsyncMock()
        
        # Create and setup bot
        bot = TelegramBotApp()
        
        with patch('bot.core.app.ApplicationBuilder') as mock_builder:
            mock_application = MagicMock()
            mock_application.add_handler = MagicMock()
            mock_application.add_error_handler = MagicMock()
            
            mock_builder.return_value.token.return_value.concurrent_updates.return_value.build.return_value = mock_application
            
            # Setup bot
            await bot.setup()
            
            # Verify bot was setup correctly
            assert bot.application is not None
            assert mock_db.create_tables.called
            assert mock_auth.load_authorizations.called
            
            # Verify handlers were registered
            assert mock_application.add_handler.call_count > 10  # We have many handlers
            assert mock_application.add_error_handler.called
            
            # Shutdown
            mock_application.stop = AsyncMock()
            mock_application.shutdown = AsyncMock()
            await bot.shutdown()


@pytest.mark.asyncio
async def test_complete_user_journey():
    """Test a complete user journey through various bot features."""
    
    # Mock all services
    with patch('bot.handlers.messages.openai_service') as mock_openai, \
         patch('bot.handlers.messages.user_service') as mock_user_service, \
         patch('bot.handlers.activity.activity_service') as mock_activity, \
         patch('bot.handlers.mood.mood_service') as mock_mood, \
         patch('bot.handlers.synonyms.synonym_service') as mock_synonym:
        
        # Setup service mocks
        mock_openai.generate_response = AsyncMock(return_value="Hello! How can I help you today?")
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        
        mock_activity.track_message = AsyncMock()
        mock_activity.get_user_activity_stats = AsyncMock(return_value={
            'total_messages': 42,
            'messages_today': 5,
            'streak_days': 3
        })
        
        mock_mood.analyze_user_mood = AsyncMock(return_value={
            'success': True,
            'mood': 'happy',
            'confidence': 0.85,
            'suggestions': ['Keep up the positive energy!']
        })
        
        mock_synonym.add_synonym = AsyncMock(return_value={
            'success': True,
            'word': 'awesome',
            'synonym': 'amazing',
            'total_synonyms': 1
        })
        
        # Create mock user and chat
        user = MagicMock()
        user.id = 123
        user.first_name = "TestUser"
        user.username = "testuser"
        
        chat = MagicMock()
        chat.id = 456
        chat.type = "group"
        
        # Simulate user journey
        
        # 1. User sends a regular message
        from bot.handlers.messages import message_handler
        
        update1 = MagicMock()
        update1.message = MagicMock()
        update1.message.text = "Hello bot!"
        update1.message.reply_text = AsyncMock()
        update1.effective_user = user
        update1.effective_chat = chat
        
        context1 = MagicMock()
        context1.bot.send_chat_action = AsyncMock()
        
        with patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
            await message_handler(update1, context1)
            
            # Verify message was handled
            mock_openai.generate_response.assert_called_once()
            update1.message.reply_text.assert_called_once()
        
        # 2. User checks their activity
        from bot.handlers.activity import my_activity_handler
        
        update2 = MagicMock()
        update2.message = MagicMock()
        update2.message.reply_text = AsyncMock()
        update2.effective_user = user
        update2.effective_chat = chat
        
        context2 = MagicMock()
        context2.args = []
        
        with patch('bot.handlers.activity.auth_check', lambda func: func):
            await my_activity_handler(update2, context2)
            
            # Verify activity was checked
            mock_activity.get_user_activity_stats.assert_called_once()
            update2.message.reply_text.assert_called_once()
        
        # 3. User analyzes their mood
        from bot.handlers.mood import mood_analysis_handler
        
        update3 = MagicMock()
        update3.message = MagicMock()
        update3.message.reply_text = AsyncMock()
        update3.effective_user = user
        update3.effective_chat = chat
        
        context3 = MagicMock()
        context3.args = []
        
        with patch('bot.handlers.mood.auth_check', lambda func: func):
            await mood_analysis_handler(update3, context3)
            
            # Verify mood was analyzed
            mock_mood.analyze_user_mood.assert_called_once()
            update3.message.reply_text.assert_called_once()
        
        # 4. User adds a synonym
        from bot.handlers.synonyms import add_synonym_handler
        
        update4 = MagicMock()
        update4.message = MagicMock()
        update4.message.reply_text = AsyncMock()
        update4.effective_user = user
        update4.effective_chat = chat
        
        context4 = MagicMock()
        context4.args = ['awesome', 'amazing']
        
        with patch('bot.handlers.synonyms.auth_check', lambda func: func):
            await add_synonym_handler(update4, context4)
            
            # Verify synonym was added
            mock_synonym.add_synonym.assert_called_once_with(
                word='awesome',
                synonym='amazing', 
                user_id=123,
                chat_id=456
            )
            update4.message.reply_text.assert_called_once()
        
        print("✅ Complete user journey test passed!")


@pytest.mark.asyncio 
async def test_error_handling_e2e():
    """Test end-to-end error handling and recovery."""
    
    with patch('bot.handlers.messages.openai_service') as mock_openai, \
         patch('bot.handlers.messages.user_service') as mock_user_service:
        
        # Setup service to fail
        mock_openai.generate_response = AsyncMock(side_effect=Exception("API Error"))
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        
        from bot.handlers.messages import message_handler
        
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "Hello bot!"
        update.message.reply_text = AsyncMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123
        update.effective_chat = MagicMock()
        update.effective_chat.id = 456
        
        context = MagicMock()
        context.bot.send_chat_action = AsyncMock()
        
        with patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
            
            # Should not raise exception, should handle gracefully
            await message_handler(update, context)
            
            # Should still reply with error message
            update.message.reply_text.assert_called()
            
            # Check that error message was sent
            call_args = update.message.reply_text.call_args[0][0]
            assert "sorry" in call_args.lower() or "error" in call_args.lower()


@pytest.mark.asyncio
async def test_performance_under_load():
    """Test bot performance under simulated load."""
    
    with patch('bot.handlers.messages.openai_service') as mock_openai, \
         patch('bot.handlers.messages.user_service') as mock_user_service, \
         patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter:
        
        # Setup fast mocks
        mock_openai.generate_response = AsyncMock(return_value="Quick response")
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        
        from bot.handlers.messages import message_handler
        
        async def simulate_message(user_id: int):
            """Simulate a single message."""
            update = MagicMock()
            update.message = MagicMock()
            update.message.text = f"Message from user {user_id}"
            update.message.reply_text = AsyncMock()
            update.effective_user = MagicMock()
            update.effective_user.id = user_id
            update.effective_chat = MagicMock()
            update.effective_chat.id = 456
            
            context = MagicMock()
            context.bot.send_chat_action = AsyncMock()
            
            await message_handler(update, context)
        
        # Simulate 50 concurrent messages
        import time
        start_time = time.time()
        
        tasks = [simulate_message(i) for i in range(50)]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        # Should handle 50 messages in under 5 seconds (very generous)
        assert duration < 5.0, f"Took too long to handle 50 messages: {duration:.2f}s"
        
        # Verify all messages were handled
        assert mock_openai.generate_response.call_count == 50
        
        print(f"✅ Handled 50 concurrent messages in {duration:.3f}s")


if __name__ == "__main__":
    # Run the tests if called directly
    pytest.main([__file__, "-v"])