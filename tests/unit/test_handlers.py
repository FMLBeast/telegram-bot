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
    assert "Complete Bot Commands Guide" in reply_args[0][0]


@pytest.mark.asyncio
async def test_message_handler_success(mock_telegram_update, mock_telegram_context):
    """Test message handler basic functionality."""
    
    with patch('bot.handlers.messages.user_service') as mock_user_service:
        
        # Setup mocks
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        
        await message_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify user and message services were called
        mock_user_service.create_or_update_user.assert_called_once()
        mock_user_service.log_message.assert_called_once()
        
        # Message handler doesn't send replies by default (only for keywords)
        # Since test message is "Hello, World!" it should not trigger keyword responses


@pytest.mark.asyncio
async def test_message_handler_keyword_trigger(mock_telegram_update, mock_telegram_context):
    """Test message handler with keyword trigger."""
    
    # Setup message with keyword
    mock_telegram_update.message.text = "wen coco"
    
    with patch('bot.handlers.messages.user_service') as mock_user_service:
        mock_user_service.create_or_update_user = AsyncMock()
        mock_user_service.log_message = AsyncMock()
        
        await message_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify keyword response was sent
        reply_args = mock_telegram_update.message.reply_text.call_args
        assert "Next Coco times" in reply_args[0][0]


@pytest.mark.asyncio 
async def test_ask_gpt_handler_with_error(mock_telegram_update, mock_telegram_context):
    """Test ask_gpt_handler with AI service error."""
    
    from bot.handlers.messages import ask_gpt_handler
    
    # Setup context with args
    mock_telegram_context.args = ["test", "question"]
    
    with patch('bot.handlers.messages.rate_limiter') as mock_rate_limiter, \
         patch('bot.handlers.messages.openai_service') as mock_openai_service:
        
        # Setup mocks
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        mock_openai_service.generate_response = AsyncMock(side_effect=Exception("AI Error"))
        
        await ask_gpt_handler(mock_telegram_update, mock_telegram_context)
        
        # Verify error message was sent (should be the last call)
        reply_calls = mock_telegram_update.message.reply_text.call_args_list
        error_call = reply_calls[-1]
        assert "encountered an error" in error_call[0][0]


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