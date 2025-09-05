"""Authorization and access control service."""

from typing import List, Set, Optional
from sqlalchemy import select, insert, delete
from sqlalchemy.exc import IntegrityError

from ..core.database import db_manager, Base
from ..core.logging import LoggerMixin
from ..core.exceptions import DatabaseError, AuthenticationError
from ..core.config import settings
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime


class AuthorizedChannel(Base):
    """Authorized channels model."""
    
    __tablename__ = "authorized_channels"
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, unique=True, index=True, nullable=False)
    channel_name = Column(String(255), nullable=True)
    authorized_by = Column(Integer, nullable=False)  # User who authorized
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPermission(Base):
    """User permissions model."""
    
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    channel_id = Column(Integer, nullable=True)  # None = global permission
    permission = Column(String(50), nullable=False)  # admin, user, banned, etc.
    granted_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthService(LoggerMixin):
    """Service for handling authorization and access control."""
    
    def __init__(self) -> None:
        """Initialize the authorization service."""
        self._authorized_channels: Set[int] = set()
        self._admin_users: Set[int] = set()
        self._banned_users: Set[int] = set()
        self._loaded = False
        
        # Add configured admin users
        for user_id in settings.admin_user_id_list:
            self._admin_users.add(user_id)
        
        self.logger.info("Authorization service initialized")
    
    async def load_authorizations(self) -> None:
        """Load authorizations from database."""
        try:
            async with db_manager.get_session() as session:
                # Load authorized channels
                stmt = select(AuthorizedChannel).where(AuthorizedChannel.is_active == True)
                result = await session.execute(stmt)
                channels = result.scalars().all()
                
                self._authorized_channels = {channel.channel_id for channel in channels}
                
                # Load user permissions
                stmt = select(UserPermission)
                result = await session.execute(stmt)
                permissions = result.scalars().all()
                
                for perm in permissions:
                    if perm.permission == "admin":
                        self._admin_users.add(perm.user_id)
                    elif perm.permission == "banned":
                        self._banned_users.add(perm.user_id)
                
                self._loaded = True
                
                self.logger.info(
                    "Authorizations loaded",
                    authorized_channels=len(self._authorized_channels),
                    admin_users=len(self._admin_users),
                    banned_users=len(self._banned_users)
                )
                
        except Exception as e:
            self.logger.error("Error loading authorizations", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to load authorizations: {str(e)}")
    
    async def is_channel_authorized(self, channel_id: int) -> bool:
        """Check if a channel is authorized."""
        if not self._loaded:
            await self.load_authorizations()
        
        # Always allow private chats (negative IDs are groups/channels)
        if channel_id > 0:
            return True
            
        return channel_id in self._authorized_channels
    
    async def is_user_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        if not self._loaded:
            await self.load_authorizations()
        
        return user_id in self._admin_users
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if a user is banned."""
        if not self._loaded:
            await self.load_authorizations()
        
        return user_id in self._banned_users
    
    async def check_access(self, user_id: int, channel_id: int) -> bool:
        """
        Check if user has access to use bot in a channel.
        
        Returns True if:
        - User is admin
        - User is not banned AND channel is authorized
        """
        is_banned = await self.is_user_banned(user_id)
        is_admin = await self.is_user_admin(user_id)
        channel_authorized = await self.is_channel_authorized(channel_id)
        
        self.logger.info(
            "Access check",
            user_id=user_id,
            channel_id=channel_id,
            is_banned=is_banned,
            is_admin=is_admin,
            channel_authorized=channel_authorized,
            admin_users=list(self._admin_users)
        )
        
        if is_banned:
            return False
        
        if is_admin:
            return True
        
        return channel_authorized
    
    async def authorize_channel(
        self, 
        channel_id: int, 
        channel_name: Optional[str],
        authorized_by: int
    ) -> bool:
        """Authorize a channel."""
        try:
            async with db_manager.get_session() as session:
                channel = AuthorizedChannel(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    authorized_by=authorized_by,
                )
                session.add(channel)
                await session.flush()
                
                # Update cache
                self._authorized_channels.add(channel_id)
                
                self.logger.info(
                    "Channel authorized",
                    channel_id=channel_id,
                    channel_name=channel_name,
                    authorized_by=authorized_by
                )
                
                return True
                
        except IntegrityError:
            self.logger.warning("Channel already authorized", channel_id=channel_id)
            return False
        except Exception as e:
            self.logger.error(
                "Error authorizing channel",
                channel_id=channel_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(f"Failed to authorize channel: {str(e)}")
    
    async def revoke_channel(self, channel_id: int) -> bool:
        """Revoke channel authorization."""
        try:
            async with db_manager.get_session() as session:
                stmt = (
                    delete(AuthorizedChannel)
                    .where(AuthorizedChannel.channel_id == channel_id)
                )
                result = await session.execute(stmt)
                
                success = result.rowcount > 0
                
                if success:
                    # Update cache
                    self._authorized_channels.discard(channel_id)
                    
                    self.logger.info("Channel authorization revoked", channel_id=channel_id)
                
                return success
                
        except Exception as e:
            self.logger.error(
                "Error revoking channel",
                channel_id=channel_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(f"Failed to revoke channel: {str(e)}")
    
    async def grant_user_permission(
        self,
        user_id: int,
        permission: str,
        granted_by: int,
        channel_id: Optional[int] = None
    ) -> bool:
        """Grant permission to a user."""
        try:
            async with db_manager.get_session() as session:
                user_perm = UserPermission(
                    user_id=user_id,
                    channel_id=channel_id,
                    permission=permission,
                    granted_by=granted_by,
                )
                session.add(user_perm)
                await session.flush()
                
                # Update cache
                if permission == "admin":
                    self._admin_users.add(user_id)
                elif permission == "banned":
                    self._banned_users.add(user_id)
                    # Remove from admin if was admin
                    self._admin_users.discard(user_id)
                
                self.logger.info(
                    "User permission granted",
                    user_id=user_id,
                    permission=permission,
                    granted_by=granted_by,
                    channel_id=channel_id
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Error granting permission",
                user_id=user_id,
                permission=permission,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(f"Failed to grant permission: {str(e)}")
    
    async def revoke_user_permission(
        self,
        user_id: int,
        permission: str,
        channel_id: Optional[int] = None
    ) -> bool:
        """Revoke permission from a user."""
        try:
            async with db_manager.get_session() as session:
                stmt = delete(UserPermission).where(
                    UserPermission.user_id == user_id,
                    UserPermission.permission == permission,
                    UserPermission.channel_id == channel_id
                )
                result = await session.execute(stmt)
                
                success = result.rowcount > 0
                
                if success:
                    # Update cache
                    if permission == "admin":
                        self._admin_users.discard(user_id)
                    elif permission == "banned":
                        self._banned_users.discard(user_id)
                    
                    self.logger.info(
                        "User permission revoked",
                        user_id=user_id,
                        permission=permission,
                        channel_id=channel_id
                    )
                
                return success
                
        except Exception as e:
            self.logger.error(
                "Error revoking permission",
                user_id=user_id,
                permission=permission,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(f"Failed to revoke permission: {str(e)}")
    
    async def get_authorized_channels(self) -> List[dict]:
        """Get all authorized channels."""
        try:
            async with db_manager.get_session() as session:
                stmt = select(AuthorizedChannel).where(AuthorizedChannel.is_active == True)
                result = await session.execute(stmt)
                channels = result.scalars().all()
                
                return [
                    {
                        "id": channel.id,
                        "channel_id": channel.channel_id,
                        "channel_name": channel.channel_name,
                        "authorized_by": channel.authorized_by,
                        "created_at": channel.created_at.isoformat() if channel.created_at else None,
                    }
                    for channel in channels
                ]
                
        except Exception as e:
            self.logger.error("Error getting authorized channels", error=str(e), exc_info=True)
            return []
    
    async def get_user_permissions(self, user_id: int) -> List[dict]:
        """Get all permissions for a user."""
        try:
            async with db_manager.get_session() as session:
                stmt = select(UserPermission).where(UserPermission.user_id == user_id)
                result = await session.execute(stmt)
                permissions = result.scalars().all()
                
                return [
                    {
                        "id": perm.id,
                        "user_id": perm.user_id,
                        "channel_id": perm.channel_id,
                        "permission": perm.permission,
                        "granted_by": perm.granted_by,
                        "created_at": perm.created_at.isoformat() if perm.created_at else None,
                    }
                    for perm in permissions
                ]
                
        except Exception as e:
            self.logger.error("Error getting user permissions", user_id=user_id, error=str(e), exc_info=True)
            return []


# Global auth service instance
auth_service = AuthService()