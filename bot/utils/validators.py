"""Input validation utilities."""

import re
from typing import Optional, List, Tuple
from html import escape

from ..core.logging import get_logger

logger = get_logger(__name__)


def validate_user_input(
    text: str,
    max_length: int = 4000,
    min_length: int = 1,
    allow_empty: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate user input text.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    if not text and not allow_empty:
        return False, "Input cannot be empty"
    
    if not text and allow_empty:
        return True, None
    
    if len(text) < min_length:
        return False, f"Input must be at least {min_length} characters long"
    
    if len(text) > max_length:
        return False, f"Input cannot exceed {max_length} characters"
    
    # Check for potential malicious content
    if contains_malicious_content(text):
        return False, "Input contains potentially malicious content"
    
    return True, None


def sanitize_text(text: str, preserve_formatting: bool = True) -> str:
    """
    Sanitize text for safe display.
    
    Args:
        text: Text to sanitize
        preserve_formatting: Whether to preserve basic Markdown formatting
    
    Returns:
        Sanitized text
    """
    
    if not text:
        return ""
    
    # HTML escape to prevent XSS
    sanitized = escape(text)
    
    # If preserving formatting, allow basic Markdown
    if preserve_formatting:
        # Allow basic Markdown characters (be careful with this in production)
        markdown_chars = ['*', '_', '`', '~', '[', ']', '(', ')']
        for char in markdown_chars:
            escaped_char = escape(char)
            if escaped_char != char:
                sanitized = sanitized.replace(escaped_char, char)
    
    # Remove or replace potentially dangerous characters
    sanitized = re.sub(r'[^\w\s\-.,!?@#$%^&*()+=\[\]{};:"\'|\\<>/~`_]', '', sanitized)
    
    # Limit consecutive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def contains_malicious_content(text: str) -> bool:
    """
    Check if text contains potentially malicious content.
    
    This is a basic implementation - in production, you'd want more sophisticated checks.
    """
    
    malicious_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                # Javascript URLs
        r'on\w+\s*=',                 # Event handlers
        r'<iframe[^>]*>.*?</iframe>',  # Iframes
        r'<object[^>]*>.*?</object>',  # Objects
        r'<embed[^>]*>.*?</embed>',    # Embeds
        r'\b(eval|exec|system|shell_exec)\s*\(',  # Dangerous functions
    ]
    
    text_lower = text.lower()
    
    for pattern in malicious_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
            logger.warning("Malicious content detected", pattern=pattern, text_preview=text[:100])
            return True
    
    return False


def validate_telegram_username(username: str) -> bool:
    """
    Validate Telegram username format.
    
    Telegram usernames must:
    - Be 5-32 characters long
    - Start with a letter
    - Contain only letters, digits, and underscores
    - Not end with an underscore
    """
    
    if not username:
        return False
    
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Check length
    if len(username) < 5 or len(username) > 32:
        return False
    
    # Check format
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*[a-zA-Z0-9]$'
    
    if len(username) == 5:
        # For 5-character usernames, allow ending with letter or digit
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]*[a-zA-Z0-9]$'
    
    return bool(re.match(pattern, username))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def extract_command_args(text: str) -> Tuple[str, List[str]]:
    """
    Extract command and arguments from text.
    
    Returns:
        Tuple of (command, args_list)
    """
    
    parts = text.strip().split()
    
    if not parts:
        return "", []
    
    command = parts[0].lower()
    
    # Remove leading slash if present
    if command.startswith('/'):
        command = command[1:]
    
    args = parts[1:] if len(parts) > 1 else []
    
    return command, args


def validate_image_prompt(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Validate image generation prompt.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    if not prompt:
        return False, "Image prompt cannot be empty"
    
    if len(prompt) < 3:
        return False, "Image prompt must be at least 3 characters long"
    
    if len(prompt) > 1000:
        return False, "Image prompt cannot exceed 1000 characters"
    
    # Check for inappropriate content (basic check)
    inappropriate_keywords = [
        'nude', 'naked', 'nsfw', 'explicit', 'sexual',
        'violence', 'gore', 'blood', 'weapon', 'drug',
        'hate', 'racism', 'discrimination'
    ]
    
    prompt_lower = prompt.lower()
    for keyword in inappropriate_keywords:
        if keyword in prompt_lower:
            return False, f"Image prompt contains inappropriate content: '{keyword}'"
    
    return True, None