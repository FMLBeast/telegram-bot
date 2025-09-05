"""Rate limiting utilities."""

import time
from typing import Dict, Tuple
from collections import defaultdict, deque

from ..core.config import settings
from ..core.logging import LoggerMixin


class RateLimiter(LoggerMixin):
    """Rate limiter using sliding window algorithm."""
    
    def __init__(self) -> None:
        """Initialize rate limiter."""
        self.user_requests: Dict[int, deque] = defaultdict(lambda: deque())
        self.max_requests = settings.rate_limit_requests
        self.time_window = settings.rate_limit_window
        
        self.logger.info(
            "Rate limiter initialized",
            max_requests=self.max_requests,
            time_window=self.time_window
        )
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit."""
        
        current_time = time.time()
        user_deque = self.user_requests[user_id]
        
        # Remove old requests outside the time window
        while user_deque and user_deque[0] <= current_time - self.time_window:
            user_deque.popleft()
        
        # Check if user has exceeded limit
        if len(user_deque) >= self.max_requests:
            self.logger.warning(
                "Rate limit exceeded",
                user_id=user_id,
                request_count=len(user_deque),
                max_requests=self.max_requests
            )
            return False
        
        # Add current request
        user_deque.append(current_time)
        
        self.logger.debug(
            "Rate limit check passed",
            user_id=user_id,
            request_count=len(user_deque),
            max_requests=self.max_requests
        )
        
        return True
    
    def get_user_request_count(self, user_id: int) -> int:
        """Get current request count for a user."""
        current_time = time.time()
        user_deque = self.user_requests[user_id]
        
        # Remove old requests
        while user_deque and user_deque[0] <= current_time - self.time_window:
            user_deque.popleft()
        
        return len(user_deque)
    
    def get_time_until_reset(self, user_id: int) -> int:
        """Get seconds until rate limit resets for user."""
        user_deque = self.user_requests[user_id]
        
        if not user_deque:
            return 0
        
        current_time = time.time()
        oldest_request = user_deque[0]
        
        return max(0, int(oldest_request + self.time_window - current_time))
    
    def clear_user_limits(self, user_id: int) -> None:
        """Clear rate limits for a specific user."""
        if user_id in self.user_requests:
            del self.user_requests[user_id]
            self.logger.info("Rate limits cleared for user", user_id=user_id)
    
    def clear_all_limits(self) -> None:
        """Clear all rate limits."""
        self.user_requests.clear()
        self.logger.info("All rate limits cleared")


class AdvancedRateLimiter(RateLimiter):
    """Advanced rate limiter with different limits for different operations."""
    
    def __init__(self) -> None:
        """Initialize advanced rate limiter."""
        super().__init__()
        
        # Different limits for different operation types
        self.operation_limits = {
            "message": (30, 60),      # 30 messages per minute
            "image": (5, 300),        # 5 images per 5 minutes
            "ai_request": (20, 60),   # 20 AI requests per minute
            "admin": (100, 60),       # 100 admin operations per minute
        }
        
        self.operation_requests: Dict[str, Dict[int, deque]] = {
            operation: defaultdict(lambda: deque())
            for operation in self.operation_limits.keys()
        }
    
    async def check_operation_limit(
        self,
        user_id: int,
        operation: str,
        is_admin: bool = False
    ) -> Tuple[bool, int]:
        """
        Check rate limit for specific operation.
        
        Returns:
            Tuple of (allowed, seconds_until_reset)
        """
        
        if operation not in self.operation_limits:
            return await self.check_rate_limit(user_id), 0
        
        # Admins get higher limits for most operations
        if is_admin and operation == "admin":
            max_requests, time_window = self.operation_limits["admin"]
        else:
            max_requests, time_window = self.operation_limits[operation]
        
        current_time = time.time()
        user_deque = self.operation_requests[operation][user_id]
        
        # Remove old requests
        while user_deque and user_deque[0] <= current_time - time_window:
            user_deque.popleft()
        
        # Check limit
        if len(user_deque) >= max_requests:
            reset_time = int(user_deque[0] + time_window - current_time)
            
            self.logger.warning(
                "Operation rate limit exceeded",
                user_id=user_id,
                operation=operation,
                request_count=len(user_deque),
                max_requests=max_requests,
                reset_in=reset_time
            )
            
            return False, max(reset_time, 1)
        
        # Add current request
        user_deque.append(current_time)
        
        return True, 0