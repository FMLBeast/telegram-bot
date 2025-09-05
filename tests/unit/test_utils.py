"""Unit tests for utility functions."""

import pytest
from datetime import datetime, timedelta
import time

from bot.utils.validators import (
    validate_user_input, 
    sanitize_text, 
    validate_telegram_username,
    validate_image_prompt
)
from bot.utils.formatters import (
    format_datetime,
    format_relative_time,
    format_file_size,
    format_duration,
    format_number,
    truncate_text
)
from bot.utils.rate_limiter import RateLimiter


class TestValidators:
    """Tests for validation utilities."""
    
    def test_validate_user_input_valid(self):
        """Test valid user input."""
        is_valid, error = validate_user_input("Hello world!")
        assert is_valid is True
        assert error is None
    
    def test_validate_user_input_empty(self):
        """Test empty user input."""
        is_valid, error = validate_user_input("")
        assert is_valid is False
        assert "cannot be empty" in error
        
        # Test with allow_empty=True
        is_valid, error = validate_user_input("", allow_empty=True)
        assert is_valid is True
        assert error is None
    
    def test_validate_user_input_too_short(self):
        """Test input that's too short."""
        is_valid, error = validate_user_input("Hi", min_length=5)
        assert is_valid is False
        assert "at least 5 characters" in error
    
    def test_validate_user_input_too_long(self):
        """Test input that's too long."""
        long_text = "x" * 5000
        is_valid, error = validate_user_input(long_text, max_length=4000)
        assert is_valid is False
        assert "cannot exceed 4000 characters" in error
    
    def test_sanitize_text_basic(self):
        """Test basic text sanitization."""
        result = sanitize_text("Hello <script>alert('xss')</script> world")
        assert "<script>" not in result
        assert "Hello" in result
        assert "world" in result
    
    def test_sanitize_text_preserve_formatting(self):
        """Test sanitization with preserved formatting."""
        result = sanitize_text("**bold** and _italic_", preserve_formatting=True)
        assert "**bold**" in result
        assert "_italic_" in result
    
    def test_validate_telegram_username_valid(self):
        """Test valid Telegram usernames."""
        assert validate_telegram_username("@testuser") is True
        assert validate_telegram_username("testuser") is True
        assert validate_telegram_username("test_user123") is True
        assert validate_telegram_username("a1b2c") is True  # minimum 5 chars
    
    def test_validate_telegram_username_invalid(self):
        """Test invalid Telegram usernames."""
        assert validate_telegram_username("") is False
        assert validate_telegram_username("test") is False  # too short
        assert validate_telegram_username("1testuser") is False  # starts with number
        assert validate_telegram_username("test_") is False  # ends with underscore
        assert validate_telegram_username("test-user") is False  # contains hyphen
        assert validate_telegram_username("x" * 33) is False  # too long
    
    def test_validate_image_prompt_valid(self):
        """Test valid image prompts."""
        is_valid, error = validate_image_prompt("a cute robot in a garden")
        assert is_valid is True
        assert error is None
    
    def test_validate_image_prompt_invalid(self):
        """Test invalid image prompts."""
        # Empty prompt
        is_valid, error = validate_image_prompt("")
        assert is_valid is False
        assert "cannot be empty" in error
        
        # Too short
        is_valid, error = validate_image_prompt("hi")
        assert is_valid is False
        assert "at least 3 characters" in error
        
        # Too long
        long_prompt = "x" * 1001
        is_valid, error = validate_image_prompt(long_prompt)
        assert is_valid is False
        assert "cannot exceed 1000 characters" in error
        
        # Inappropriate content
        is_valid, error = validate_image_prompt("nude person")
        assert is_valid is False
        assert "inappropriate content" in error


class TestFormatters:
    """Tests for formatting utilities."""
    
    def test_format_datetime_full(self):
        """Test full datetime formatting."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt, "full")
        assert "2024-01-15 14:30:45" == result
    
    def test_format_datetime_short(self):
        """Test short datetime formatting."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt, "short")
        assert "01/15 14:30" == result
    
    def test_format_relative_time_past(self):
        """Test relative time formatting for past times."""
        now = datetime.utcnow()
        
        # 5 minutes ago
        past_time = now - timedelta(minutes=5)
        result = format_relative_time(past_time)
        assert "5 minutes ago" == result
        
        # 2 hours ago
        past_time = now - timedelta(hours=2)
        result = format_relative_time(past_time)
        assert "2 hours ago" == result
        
        # 3 days ago
        past_time = now - timedelta(days=3)
        result = format_relative_time(past_time)
        assert "3 days ago" == result
    
    def test_format_relative_time_future(self):
        """Test relative time formatting for future times."""
        now = datetime.utcnow()
        future_time = now + timedelta(hours=3)
        result = format_relative_time(future_time)
        assert "in 3 hours" == result
    
    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(0) == "0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(1536) == "1.5 KB"
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(0) == "0s"
        assert format_duration(30) == "30s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(90061) == "1d 1h 1m 1s"
    
    def test_format_number(self):
        """Test number formatting with suffixes."""
        assert format_number(500) == "500"
        assert format_number(1500) == "1.50K"
        assert format_number(1500000) == "1.50M"
        assert format_number(1500000000) == "1.50B"
        assert format_number(-1500) == "-1.50K"
    
    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a very long text that should be truncated"
        result = truncate_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")
        assert "This is a very" in result
        
        # Test text shorter than max length
        short_text = "Short"
        result = truncate_text(short_text, max_length=20)
        assert result == "Short"


class TestRateLimiter:
    """Tests for rate limiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance."""
        limiter = RateLimiter()
        limiter.max_requests = 3
        limiter.time_window = 60
        return limiter
    
    @pytest.mark.asyncio
    async def test_rate_limit_allow_initial_requests(self, rate_limiter):
        """Test that initial requests are allowed."""
        user_id = 123
        
        # First 3 requests should be allowed
        for i in range(3):
            result = await rate_limiter.check_rate_limit(user_id)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_block_excess_requests(self, rate_limiter):
        """Test that excess requests are blocked."""
        user_id = 123
        
        # Use up the limit
        for i in range(3):
            await rate_limiter.check_rate_limit(user_id)
        
        # Next request should be blocked
        result = await rate_limiter.check_rate_limit(user_id)
        assert result is False
    
    def test_get_user_request_count(self, rate_limiter):
        """Test getting user request count."""
        user_id = 123
        
        # Add some requests manually
        current_time = time.time()
        rate_limiter.user_requests[user_id].extend([
            current_time - 30,
            current_time - 20,
            current_time - 10
        ])
        
        count = rate_limiter.get_user_request_count(user_id)
        assert count == 3
    
    def test_clear_user_limits(self, rate_limiter):
        """Test clearing limits for specific user."""
        user_id = 123
        
        # Add some requests
        rate_limiter.user_requests[user_id].append(time.time())
        
        # Clear limits
        rate_limiter.clear_user_limits(user_id)
        
        # Should be empty now
        count = rate_limiter.get_user_request_count(user_id)
        assert count == 0
    
    def test_clear_all_limits(self, rate_limiter):
        """Test clearing all limits."""
        # Add requests for multiple users
        rate_limiter.user_requests[123].append(time.time())
        rate_limiter.user_requests[456].append(time.time())
        
        # Clear all
        rate_limiter.clear_all_limits()
        
        # Should be empty
        assert len(rate_limiter.user_requests) == 0
    
    def test_time_window_expiry(self, rate_limiter):
        """Test that old requests expire from the time window."""
        user_id = 123
        current_time = time.time()
        
        # Add old request (outside time window)
        rate_limiter.user_requests[user_id].append(current_time - 120)  # 2 minutes ago
        
        # Check current count (should be 0 as old request expired)
        count = rate_limiter.get_user_request_count(user_id)
        assert count == 0