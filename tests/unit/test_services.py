"""Unit tests for bot services."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import openai

from bot.services.openai_service import OpenAIService
from bot.services.user_service import UserService
from bot.core.exceptions import APIError, DatabaseError


class TestOpenAIService:
    """Tests for OpenAI service."""
    
    @pytest.fixture
    def openai_service(self):
        """Create OpenAI service instance."""
        return OpenAIService()
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, openai_service):
        """Test successful response generation."""
        
        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test AI response"
        mock_response.usage.total_tokens = 100
        
        with patch.object(openai_service.client.chat.completions, 'create', 
                         new_callable=AsyncMock, return_value=mock_response):
            
            result = await openai_service.generate_response(
                message="Hello",
                user_id=123,
                username="testuser"
            )
            
            assert result == "Test AI response"
            assert 123 in openai_service.conversation_history
            assert len(openai_service.conversation_history[123]) == 2  # user + assistant
    
    @pytest.mark.asyncio
    async def test_generate_response_rate_limit(self, openai_service):
        """Test response generation with rate limit error."""
        
        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock, 
                         side_effect=openai.RateLimitError("Rate limited", None, None)):
            
            result = await openai_service.generate_response(
                message="Hello",
                user_id=123,
                username="testuser"
            )
            
            assert "high demand" in result
    
    @pytest.mark.asyncio
    async def test_generate_response_auth_error(self, openai_service):
        """Test response generation with authentication error."""
        
        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock,
                         side_effect=openai.AuthenticationError("Auth failed", None, None)):
            
            result = await openai_service.generate_response(
                message="Hello",
                user_id=123,
                username="testuser"
            )
            
            assert "Authentication error" in result
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self, openai_service):
        """Test successful image generation."""
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].url = "https://example.com/image.jpg"
        
        with patch.object(openai_service.client.images, 'generate',
                         new_callable=AsyncMock, return_value=mock_response):
            
            result = await openai_service.generate_image(
                prompt="A cute robot",
                user_id=123
            )
            
            assert result == "https://example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_generate_image_error(self, openai_service):
        """Test image generation with error."""
        
        with patch.object(openai_service.client.images, 'generate',
                         new_callable=AsyncMock,
                         side_effect=Exception("Image generation failed")):
            
            with pytest.raises(APIError):
                await openai_service.generate_image(
                    prompt="A cute robot",
                    user_id=123
                )
    
    def test_clear_conversation_history(self, openai_service):
        """Test clearing conversation history."""
        
        # Add some history
        openai_service.conversation_history[123] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        
        openai_service.clear_conversation_history(123)
        
        assert 123 not in openai_service.conversation_history
    
    def test_get_conversation_length(self, openai_service):
        """Test getting conversation length."""
        
        # Add some history
        openai_service.conversation_history[123] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        
        length = openai_service.get_conversation_length(123)
        assert length == 2
        
        # Test with non-existent user
        length = openai_service.get_conversation_length(999)
        assert length == 0
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_success(self, openai_service):
        """Test successful sentiment analysis."""
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"sentiment": "positive", "confidence": 0.8, "explanation": "Happy text"}'
        
        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock, return_value=mock_response):
            
            result = await openai_service.analyze_sentiment("I'm happy!")
            
            assert result["sentiment"] == "positive"
            assert result["confidence"] == 0.8
            assert result["explanation"] == "Happy text"


class TestUserService:
    """Tests for User service."""
    
    @pytest.mark.asyncio
    async def test_create_new_user(self, user_service, test_db):
        """Test creating a new user."""
        
        with patch.object(user_service, 'db_manager', test_db):
            user = await user_service.create_or_update_user(
                telegram_id=123,
                username="testuser",
                first_name="Test",
                last_name="User"
            )
            
            assert user.telegram_id == 123
            assert user.username == "testuser"
            assert user.first_name == "Test"
            assert user.last_name == "User"
    
    @pytest.mark.asyncio
    async def test_update_existing_user(self, user_service, test_db):
        """Test updating an existing user."""
        
        with patch.object(user_service, 'db_manager', test_db):
            # Create user first
            await user_service.create_or_update_user(
                telegram_id=123,
                username="testuser",
                first_name="Test"
            )
            
            # Update user
            user = await user_service.create_or_update_user(
                telegram_id=123,
                username="newusername",
                first_name="NewTest",
                last_name="User"
            )
            
            assert user.username == "newusername"
            assert user.first_name == "NewTest"
            assert user.last_name == "User"
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id(self, user_service, test_db):
        """Test getting user by Telegram ID."""
        
        with patch.object(user_service, 'db_manager', test_db):
            # Create user first
            await user_service.create_or_update_user(
                telegram_id=123,
                username="testuser"
            )
            
            # Get user
            user = await user_service.get_user_by_telegram_id(123)
            
            assert user is not None
            assert user.telegram_id == 123
            assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, user_service, test_db):
        """Test getting non-existent user."""
        
        with patch.object(user_service, 'db_manager', test_db):
            user = await user_service.get_user_by_telegram_id(999)
            assert user is None
    
    @pytest.mark.asyncio
    async def test_set_user_admin(self, user_service, test_db):
        """Test setting user admin status."""
        
        with patch.object(user_service, 'db_manager', test_db):
            # Create user first
            await user_service.create_or_update_user(
                telegram_id=123,
                username="testuser"
            )
            
            # Set admin
            result = await user_service.set_user_admin(123, True)
            assert result is True
            
            # Verify admin status
            user = await user_service.get_user_by_telegram_id(123)
            assert user.is_admin is True
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, test_db):
        """Test deactivating a user."""
        
        with patch.object(user_service, 'db_manager', test_db):
            # Create user first
            await user_service.create_or_update_user(
                telegram_id=123,
                username="testuser"
            )
            
            # Deactivate user
            result = await user_service.deactivate_user(123)
            assert result is True
            
            # Verify deactivation
            user = await user_service.get_user_by_telegram_id(123)
            assert user.is_active is False
    
    @pytest.mark.asyncio
    async def test_log_message(self, user_service, test_db):
        """Test logging a message."""
        
        with patch.object(user_service, 'db_manager', test_db):
            message = await user_service.log_message(
                user_id=123,
                chat_id=456,
                message_text="Test message",
                message_type="text"
            )
            
            assert message is not None
            assert message.user_id == 123
            assert message.chat_id == 456
            assert message.text == "Test message"
            assert message.message_type == "text"
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_service, test_db):
        """Test getting user statistics."""
        
        with patch.object(user_service, 'db_manager', test_db):
            # Create user first
            await user_service.create_or_update_user(
                telegram_id=123,
                username="testuser"
            )
            
            # Get stats
            stats = await user_service.get_user_stats(123)
            
            assert stats["telegram_id"] == 123
            assert stats["username"] == "testuser"
            assert "message_count" in stats
            assert "created_at" in stats