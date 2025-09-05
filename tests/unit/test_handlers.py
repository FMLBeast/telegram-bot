"""Unit tests for bot handlers."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bot.handlers.commands import start_handler, help_handler
from bot.handlers.messages import message_handler
from bot.handlers.callbacks import callback_handler


@pytest.mark.asyncio
async def test_start_handler(mock_telegram_update, mock_telegram_context):
    """Test start command handler."""
    
    with patch('bot.handlers.commands.user_service') as mock_user_service:
        mock_user_service.create_or_update_user = AsyncMock()
        
        await start_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify user creation was called
        mock_user_service.create_or_update_user.assert_called_once()
        
        # Verify message reply was called
        mock_telegram_update.message.reply_text.assert_called_once()
        
        # Check that the reply contains welcome text
        reply_args = mock_telegram_update.message.reply_text.call_args
        assert "Welcome" in reply_args[0][0]


@pytest.mark.asyncio
async def test_help_handler(mock_telegram_update, mock_telegram_context):
    """Test help command handler."""
    
    await help_handler(mock_telegram_update, mock_telegram_context)
    
    # Verify message reply was called
    mock_telegram_update.message.reply_text.assert_called_once()
    
    # Check that the reply contains help text
    reply_args = mock_telegram_update.message.reply_text.call_args
    assert "Commands Help" in reply_args[0][0]


@pytest.mark.asyncio
async def test_message_handler_success(mock_telegram_update, mock_telegram_context):
    """Test message handler with successful AI response."""
    
    with patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter, \
         patch('bot.handlers.messages.user_service') as mock_user_service, \
         patch('bot.handlers.messages.openai_service') as mock_openai_service:
        
        # Setup mocks
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        mock_openai_service.generate_response = AsyncMock(return_value="AI response")
        
        await message_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify all services were called
        mock_rate_limiter.check_rate_limit.assert_called_once()
        mock_user_service.create_or_update_user.assert_called_once()
        mock_user_service.log_message.assert_called_once()
        mock_openai_service.generate_response.assert_called_once()
        
        # Verify typing action was sent
        mock_telegram_context.bot.send_chat_action.assert_called_once()
        
        # Verify reply was sent
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "AI response",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


@pytest.mark.asyncio
async def test_message_handler_rate_limited(mock_telegram_update, mock_telegram_context):
    """Test message handler with rate limiting."""
    
    with patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter:
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=False)
        
        await message_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify rate limit message was sent
        reply_args = mock_telegram_update.message.reply_text.call_args
        assert "too quickly" in reply_args[0][0]


@pytest.mark.asyncio
async def test_message_handler_ai_error(mock_telegram_update, mock_telegram_context):
    """Test message handler with AI service error."""
    
    with patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter, \
         patch('bot.handlers.messages.user_service') as mock_user_service, \
         patch('bot.handlers.messages.openai_service') as mock_openai_service:
        
        # Setup mocks
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        mock_openai_service.generate_response = AsyncMock(side_effect=Exception("AI Error"))
        
        await message_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify error message was sent
        reply_args = mock_telegram_update.message.reply_text.call_args
        assert "encountered an error" in reply_args[0][0]


@pytest.mark.asyncio
async def test_callback_handler_help(mock_telegram_update, mock_telegram_context):
    """Test callback handler for help action."""
    
    # Setup callback query
    mock_telegram_update.callback_query = MagicMock()
    mock_telegram_update.callback_query.data = "help"
    mock_telegram_update.callback_query.answer = AsyncMock()
    mock_telegram_update.callback_query.edit_message_text = AsyncMock()
    
    await callback_handler(mock_telegram_update, mock_telegram_context)
    
    # Verify callback was answered
    mock_telegram_update.callback_query.answer.assert_called_once()
    
    # Verify message was edited
    mock_telegram_update.callback_query.edit_message_text.assert_called_once()
    
    # Check that help text was included
    edit_args = mock_telegram_update.callback_query.edit_message_text.call_args
    assert "Quick Help" in edit_args[0][0]


@pytest.mark.asyncio
async def test_callback_handler_unknown(mock_telegram_update, mock_telegram_context):
    """Test callback handler for unknown action."""
    
    # Setup callback query
    mock_telegram_update.callback_query = MagicMock()
    mock_telegram_update.callback_query.data = "unknown_action"
    mock_telegram_update.callback_query.answer = AsyncMock()
    mock_telegram_update.callback_query.edit_message_text = AsyncMock()
    
    await callback_handler(mock_telegram_update, mock_telegram_context)
    
    # Verify callback was answered
    mock_telegram_update.callback_query.answer.assert_called_once()
    
    # Verify unknown command message was sent
    edit_args = mock_telegram_update.callback_query.edit_message_text.call_args
    assert "Unknown command" in edit_args[0][0]


@pytest.mark.asyncio
async def test_handler_with_no_user():
    """Test handler behavior when no effective user is present."""
    
    update = MagicMock()
    update.message = MagicMock()
    update.effective_user = None
    context = MagicMock()
    
    # Should return early without doing anything
    await start_handler(update, context)
    
    # Verify no reply was sent
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handler_with_no_message():
    """Test handler behavior when no message is present."""
    
    update = MagicMock()
    update.message = None
    update.effective_user = MagicMock()
    context = MagicMock()
    
    # Should return early without doing anything
    await start_handler(update, context)
    
    # No assertions needed - just ensuring no exceptions are raised