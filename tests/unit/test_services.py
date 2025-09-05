"""Unit tests for bot services."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import openai

from bot.services.openai_service import OpenAIService
from bot.services.user_service import UserService
from bot.services.activity_service import ActivityService
from bot.services.mood_service import MoodService
from bot.services.synonym_service import SynonymService
from bot.core.exceptions import APIError, DatabaseError
import json
import tempfile
import os
from datetime import datetime, timedelta


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


class TestActivityService:
    """Tests for Activity service."""
    
    @pytest.fixture
    def activity_service(self, test_db):
        """Create activity service instance."""
        service = ActivityService()
        service.db_manager = test_db
        return service
    
    @pytest.mark.asyncio
    async def test_track_message(self, activity_service):
        """Test message tracking."""
        
        # Mock database operations
        with patch.object(activity_service, '_store_activity') as mock_store:
            await activity_service.track_message(
                user_id=123,
                chat_id=456,
                message_type="text",
                timestamp=datetime.now()
            )
            
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_night_owls(self, activity_service):
        """Test getting night owls."""
        
        # Mock database query
        mock_results = [
            {'user_id': 123, 'message_count': 50, 'username': 'testuser'},
            {'user_id': 124, 'message_count': 30, 'username': 'testuser2'}
        ]
        
        with patch.object(activity_service, '_query_night_activity', return_value=mock_results):
            result = await activity_service.get_night_owls(chat_id=456)
            
            assert len(result) == 2
            assert result[0]['user_id'] == 123
            assert result[0]['message_count'] == 50
    
    @pytest.mark.asyncio
    async def test_get_most_active_users(self, activity_service):
        """Test getting most active users."""
        
        mock_results = [
            {'user_id': 123, 'message_count': 100, 'username': 'testuser'},
            {'user_id': 124, 'message_count': 80, 'username': 'testuser2'}
        ]
        
        with patch.object(activity_service, '_query_user_activity', return_value=mock_results):
            result = await activity_service.get_most_active_users(chat_id=456)
            
            assert len(result) == 2
            assert result[0]['message_count'] >= result[1]['message_count']  # Check ordering
    
    @pytest.mark.asyncio
    async def test_get_user_activity_stats(self, activity_service):
        """Test getting user activity statistics."""
        
        mock_stats = {
            'total_messages': 150,
            'messages_today': 20,
            'most_active_hour': 14,
            'night_messages': 30,
            'streak_days': 5
        }
        
        with patch.object(activity_service, '_calculate_user_stats', return_value=mock_stats):
            result = await activity_service.get_user_activity_stats(user_id=123, chat_id=456)
            
            assert result['total_messages'] == 150
            assert result['messages_today'] == 20
            assert result['streak_days'] == 5


class TestMoodService:
    """Tests for Mood service."""
    
    @pytest.fixture
    def mood_service(self, mock_openai_service):
        """Create mood service instance."""
        service = MoodService()
        service.openai_service = mock_openai_service
        return service
    
    @pytest.mark.asyncio
    async def test_analyze_user_mood_success(self, mood_service, mock_openai_service):
        """Test successful mood analysis."""
        
        # Mock user messages
        mock_messages = [
            "I'm feeling great today!",
            "This is an amazing day!",
            "Everything is wonderful!"
        ]
        
        mock_analysis = {
            'mood': 'happy',
            'confidence': 0.9,
            'energy_level': 'high',
            'explanation': 'Very positive language',
            'suggestions': ['Keep up the positive attitude!']
        }
        
        with patch.object(mood_service, '_get_recent_messages', return_value=mock_messages):
            with patch.object(mood_service.openai_service, 'analyze_sentiment', return_value=mock_analysis):
                result = await mood_service.analyze_user_mood(user_id=123)
                
                assert result['success'] is True
                assert result['mood'] == 'happy'
                assert result['confidence'] == 0.9
                assert 'suggestions' in result
    
    @pytest.mark.asyncio
    async def test_analyze_user_mood_no_messages(self, mood_service):
        """Test mood analysis with no messages."""
        
        with patch.object(mood_service, '_get_recent_messages', return_value=[]):
            result = await mood_service.analyze_user_mood(user_id=123)
            
            assert result['success'] is False
            assert 'not enough messages' in result['message']
    
    @pytest.mark.asyncio
    async def test_get_mood_trends(self, mood_service):
        """Test getting mood trends."""
        
        mock_trends = {
            'daily_moods': [
                {'date': '2023-01-01', 'mood': 'happy', 'confidence': 0.8},
                {'date': '2023-01-02', 'mood': 'neutral', 'confidence': 0.6}
            ],
            'average_mood': 'positive',
            'trend_direction': 'stable',
            'insights': ['User maintains consistent positive mood']
        }
        
        with patch.object(mood_service, '_calculate_mood_trends', return_value=mock_trends):
            result = await mood_service.get_mood_trends(user_id=123, days=7)
            
            assert len(result['daily_moods']) == 2
            assert result['average_mood'] == 'positive'
            assert result['trend_direction'] == 'stable'
    
    @pytest.mark.asyncio
    async def test_analyze_chat_mood(self, mood_service):
        """Test analyzing overall chat mood."""
        
        mock_chat_mood = {
            'overall_mood': 'positive',
            'user_moods': [
                {'user_id': 123, 'mood': 'happy'},
                {'user_id': 124, 'mood': 'content'}
            ],
            'mood_distribution': {
                'happy': 60,
                'content': 30,
                'neutral': 10
            }
        }
        
        with patch.object(mood_service, '_analyze_chat_sentiment', return_value=mock_chat_mood):
            result = await mood_service.analyze_chat_mood(chat_id=456)
            
            assert result['overall_mood'] == 'positive'
            assert len(result['user_moods']) == 2


class TestSynonymService:
    """Tests for Synonym service."""
    
    @pytest.fixture
    def synonym_service(self):
        """Create synonym service instance."""
        # Create temporary file for testing
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write('{}')
        temp_file.close()
        
        service = SynonymService()
        service.data_file = temp_file.name
        # Reset data for each test
        service.synonyms = {}
        
        yield service
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_add_synonym_new_word(self, synonym_service):
        """Test adding synonym for new word."""
        
        result = await synonym_service.add_synonym(
            word='happy',
            synonym='joyful',
            user_id=123,
            chat_id=456
        )
        
        assert result['success'] is True
        assert result['word'] == 'happy'
        assert result['synonym'] == 'joyful'
        assert result['total_synonyms'] == 1
    
    @pytest.mark.asyncio
    async def test_add_synonym_existing_word(self, synonym_service):
        """Test adding synonym to existing word."""
        
        # Add first synonym
        await synonym_service.add_synonym('happy', 'joyful', 123, 456)
        
        # Add second synonym
        result = await synonym_service.add_synonym('happy', 'cheerful', 123, 456)
        
        assert result['success'] is True
        assert result['total_synonyms'] == 2
    
    @pytest.mark.asyncio
    async def test_add_duplicate_synonym(self, synonym_service):
        """Test adding duplicate synonym."""
        
        # Add synonym
        await synonym_service.add_synonym('happy', 'joyful', 123, 456)
        
        # Try to add same synonym again
        result = await synonym_service.add_synonym('happy', 'joyful', 123, 456)
        
        assert result['success'] is False
        assert 'already a synonym' in result['message']
    
    @pytest.mark.asyncio
    async def test_get_synonyms(self, synonym_service):
        """Test getting synonyms for a word."""
        
        # Add synonyms
        await synonym_service.add_synonym('happy', 'joyful', 123, 456)
        await synonym_service.add_synonym('happy', 'cheerful', 123, 456)
        
        synonyms = await synonym_service.get_synonyms('happy')
        
        assert len(synonyms) == 2
        assert 'joyful' in synonyms
        assert 'cheerful' in synonyms
    
    @pytest.mark.asyncio
    async def test_search_synonyms(self, synonym_service):
        """Test searching synonyms."""
        
        # Add test data
        await synonym_service.add_synonym('happy', 'joyful', 123, 456)
        await synonym_service.add_synonym('happiness', 'joy', 123, 456)
        await synonym_service.add_synonym('sad', 'unhappy', 123, 456)
        
        result = await synonym_service.search_synonyms('happ')
        
        # Should find words containing 'happ' (both 'happy' and 'happiness')
        assert result['count'] >= 2
        assert 'happy' in result['results']
        assert 'happiness' in result['results']
    
    @pytest.mark.asyncio
    async def test_get_synonym_of_the_day(self, synonym_service):
        """Test getting synonym of the day."""
        
        # Add test data
        await synonym_service.add_synonym('amazing', 'fantastic', 123, 456)
        await synonym_service.add_synonym('amazing', 'wonderful', 123, 456)
        
        result = await synonym_service.get_synonym_of_the_day()
        
        assert 'word' in result
        assert 'synonyms' in result
        assert len(result['synonyms']) >= 1
    
    @pytest.mark.asyncio
    async def test_get_synonym_stats(self, synonym_service):
        """Test getting synonym statistics."""
        
        # Add test data
        await synonym_service.add_synonym('happy', 'joyful', 123, 456)
        await synonym_service.add_synonym('happy', 'cheerful', 123, 456)
        await synonym_service.add_synonym('sad', 'unhappy', 123, 456)
        
        stats = await synonym_service.get_synonym_stats()
        
        # Should have at least the words we added (might have more from other tests)
        assert stats['total_words'] >= 2
        assert stats['total_synonyms'] >= 3
        assert stats.get('average_synonyms_per_word', 0) > 0
        assert 'most_synonyms' in stats
    
    @pytest.mark.asyncio
    async def test_synonym_persistence(self, synonym_service):
        """Test that synonyms persist to file."""
        
        await synonym_service.add_synonym('test', 'exam', 123, 456)
        
        # Create new service instance with same file
        new_service = SynonymService()
        new_service.data_file = synonym_service.data_file
        await new_service._load_synonyms()
        
        synonyms = await new_service.get_synonyms('test')
        assert 'exam' in synonyms