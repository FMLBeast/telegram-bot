"""User service for managing users and their data."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, insert, update
from sqlalchemy.exc import IntegrityError

from ..core.database import db_manager, User, Chat, Message
from ..core.logging import LoggerMixin
from ..core.exceptions import DatabaseError


class UserService(LoggerMixin):
    """Service for managing users and their interactions."""
    
    async def create_or_update_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        """Create a new user or update existing user information."""
        
        try:
            async with db_manager.get_session() as session:
                # Try to get existing user
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    # Update existing user
                    user.username = username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.updated_at = datetime.utcnow()
                    
                    self.logger.info(
                        "User updated",
                        user_id=user.id,
                        telegram_id=telegram_id,
                        username=username
                    )
                else:
                    # Create new user
                    user = User(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    session.add(user)
                    await session.flush()  # Get the ID
                    
                    self.logger.info(
                        "New user created",
                        user_id=user.id,
                        telegram_id=telegram_id,
                        username=username
                    )
                
                return user
                
        except Exception as e:
            self.logger.error(
                "Error creating/updating user",
                telegram_id=telegram_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(f"Failed to create/update user: {str(e)}")
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        
        try:
            async with db_manager.get_session() as session:
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error(
                "Error getting user",
                telegram_id=telegram_id,
                error=str(e),
                exc_info=True
            )
            return None
    
    async def set_user_admin(self, telegram_id: int, is_admin: bool = True) -> bool:
        """Set user admin status."""
        
        try:
            async with db_manager.get_session() as session:
                stmt = (
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(is_admin=is_admin, updated_at=datetime.utcnow())
                )
                result = await session.execute(stmt)
                
                success = result.rowcount > 0
                
                self.logger.info(
                    "User admin status updated",
                    telegram_id=telegram_id,
                    is_admin=is_admin,
                    success=success
                )
                
                return success
                
        except Exception as e:
            self.logger.error(
                "Error setting user admin status",
                telegram_id=telegram_id,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def deactivate_user(self, telegram_id: int) -> bool:
        """Deactivate a user (mark as inactive)."""
        
        try:
            async with db_manager.get_session() as session:
                stmt = (
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(is_active=False, updated_at=datetime.utcnow())
                )
                result = await session.execute(stmt)
                
                success = result.rowcount > 0
                
                self.logger.info(
                    "User deactivated",
                    telegram_id=telegram_id,
                    success=success
                )
                
                return success
                
        except Exception as e:
            self.logger.error(
                "Error deactivating user",
                telegram_id=telegram_id,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def get_all_active_users(self) -> List[User]:
        """Get all active users."""
        
        try:
            async with db_manager.get_session() as session:
                stmt = select(User).where(User.is_active == True)
                result = await session.execute(stmt)
                return list(result.scalars())
                
        except Exception as e:
            self.logger.error(
                "Error getting all active users",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def get_admin_users(self) -> List[User]:
        """Get all admin users."""
        
        try:
            async with db_manager.get_session() as session:
                stmt = select(User).where(User.is_admin == True, User.is_active == True)
                result = await session.execute(stmt)
                return list(result.scalars())
                
        except Exception as e:
            self.logger.error(
                "Error getting admin users",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def log_message(
        self,
        user_id: int,
        chat_id: int,
        message_text: str,
        message_type: str = "text"
    ) -> Optional[Message]:
        """Log a message to the database."""
        
        try:
            async with db_manager.get_session() as session:
                message = Message(
                    telegram_message_id=0,  # Will be updated if needed
                    user_id=user_id,
                    chat_id=chat_id,
                    text=message_text,
                    message_type=message_type,
                )
                session.add(message)
                await session.flush()
                
                self.logger.debug(
                    "Message logged",
                    message_id=message.id,
                    user_id=user_id,
                    chat_id=chat_id,
                    message_type=message_type
                )
                
                return message
                
        except Exception as e:
            self.logger.error(
                "Error logging message",
                user_id=user_id,
                chat_id=chat_id,
                error=str(e),
                exc_info=True
            )
            return None
    
    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get user statistics."""
        
        try:
            async with db_manager.get_session() as session:
                # Get user
                user_stmt = select(User).where(User.telegram_id == telegram_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {}
                
                # Get message count (simplified query)
                # In a real implementation, you'd use proper aggregation queries
                from sqlalchemy import func
                
                msg_stmt = select(func.count(Message.id)).where(Message.user_id == user.telegram_id)
                msg_result = await session.execute(msg_stmt)
                message_count = msg_result.scalar() or 0
                
                return {
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "message_count": message_count,
                }
                
        except Exception as e:
            self.logger.error(
                "Error getting user stats",
                telegram_id=telegram_id,
                error=str(e),
                exc_info=True
            )
            return {}

    async def log_command_usage(self, user_id: int, command: str, target_user: Optional[int] = None) -> None:
        """Log command usage for analytics."""
        try:
            self.logger.info(
                "Command usage logged",
                user_id=user_id,
                command=command,
                target_user=target_user
            )
        except Exception as e:
            self.logger.error("Error logging command usage", error=str(e))


# Global service instance
user_service = UserService()