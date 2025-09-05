"""Text and data formatting utilities."""

from datetime import datetime, timedelta
from typing import Optional, Union
import pytz
from ..core.config import settings


def format_datetime(
    dt: datetime,
    format_type: str = "full",
    timezone: Optional[str] = None
) -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime to format
        format_type: Type of formatting ("full", "short", "time", "date")
        timezone: Timezone to convert to (defaults to UTC)
    
    Returns:
        Formatted datetime string
    """
    
    if not dt:
        return "Never"
    
    # Convert to timezone if specified
    if timezone:
        try:
            tz = pytz.timezone(timezone)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            dt = dt.astimezone(tz)
        except Exception:
            pass  # Use original datetime if timezone conversion fails
    
    formats = {
        "full": "%Y-%m-%d %H:%M:%S",
        "short": "%m/%d %H:%M",
        "time": "%H:%M:%S",
        "date": "%Y-%m-%d",
        "relative": None,  # Special case handled below
    }
    
    if format_type == "relative":
        return format_relative_time(dt)
    
    format_str = formats.get(format_type, formats["full"])
    return dt.strftime(format_str)


def format_relative_time(dt: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 hours ago").
    
    Args:
        dt: Datetime to format
    
    Returns:
        Relative time string
    """
    
    now = datetime.utcnow()
    if dt.tzinfo is not None:
        now = now.replace(tzinfo=pytz.utc)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
    
    diff = now - dt
    
    if diff.total_seconds() < 0:
        # Future time
        diff = dt - now
        future = True
    else:
        future = False
    
    seconds = int(abs(diff.total_seconds()))
    
    if seconds < 60:
        time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
    elif seconds < 3600:
        minutes = seconds // 60
        time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        time_str = f"{hours} hour{'s' if hours != 1 else ''}"
    elif seconds < 2592000:  # 30 days
        days = seconds // 86400
        time_str = f"{days} day{'s' if days != 1 else ''}"
    elif seconds < 31536000:  # 365 days
        months = seconds // 2592000
        time_str = f"{months} month{'s' if months != 1 else ''}"
    else:
        years = seconds // 31536000
        time_str = f"{years} year{'s' if years != 1 else ''}"
    
    if future:
        return f"in {time_str}"
    else:
        return f"{time_str} ago"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: Union[int, float]) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string (e.g., "2h 30m 15s")
    """
    
    if seconds < 0:
        return "0s"
    
    seconds = int(seconds)
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def format_number(number: Union[int, float], precision: int = 2) -> str:
    """
    Format number with appropriate suffixes (K, M, B).
    
    Args:
        number: Number to format
        precision: Decimal precision
    
    Returns:
        Formatted number string
    """
    
    if number == 0:
        return "0"
    
    abs_number = abs(number)
    sign = "-" if number < 0 else ""
    
    if abs_number >= 1_000_000_000:
        formatted = f"{abs_number / 1_000_000_000:.{precision}f}B"
    elif abs_number >= 1_000_000:
        formatted = f"{abs_number / 1_000_000:.{precision}f}M"
    elif abs_number >= 1_000:
        formatted = f"{abs_number / 1_000:.{precision}f}K"
    else:
        if isinstance(number, float):
            formatted = f"{abs_number:.{precision}f}"
        else:
            formatted = str(abs_number)
    
    return f"{sign}{formatted}"


def format_percentage(value: float, precision: int = 1) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Value to format (0.0 to 1.0)
        precision: Decimal precision
    
    Returns:
        Formatted percentage string
    """
    
    percentage = value * 100
    return f"{percentage:.{precision}f}%"


def format_money(amount: float, currency: str = "USD", precision: int = 2) -> str:
    """
    Format money amount.
    
    Args:
        amount: Amount to format
        currency: Currency code
        precision: Decimal precision
    
    Returns:
        Formatted money string
    """
    
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "BTC": "₿",
        "ETH": "Ξ",
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if currency == "JPY":
        # Japanese Yen doesn't use decimal places
        return f"{symbol}{amount:,.0f}"
    
    return f"{symbol}{amount:,.{precision}f}"


def truncate_text(text: str, max_length: int = 100, ellipsis: str = "...") -> str:
    """
    Truncate text to maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including ellipsis
        ellipsis: String to append when truncated
    
    Returns:
        Truncated text
    """
    
    if len(text) <= max_length:
        return text
    
    truncated_length = max_length - len(ellipsis)
    return text[:truncated_length] + ellipsis


def format_list(items: list, separator: str = ", ", last_separator: str = " and ") -> str:
    """
    Format list of items with proper separators.
    
    Args:
        items: List of items to format
        separator: Separator for items
        last_separator: Separator before last item
    
    Returns:
        Formatted list string
    """
    
    if not items:
        return ""
    
    if len(items) == 1:
        return str(items[0])
    
    if len(items) == 2:
        return f"{items[0]}{last_separator}{items[1]}"
    
    return separator.join(str(item) for item in items[:-1]) + last_separator + str(items[-1])