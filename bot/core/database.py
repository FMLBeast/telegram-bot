"""Database management with async SQLAlchemy."""

from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for database models."""
    pass


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Chat(Base):
    """Chat model."""
    
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    """Message model."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    telegram_message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    chat_id = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)
    message_type = Column(String(50), nullable=False, default="text")
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url.replace("sqlite://", "sqlite+aiosqlite://"),
            echo=settings.is_development,
            future=True,
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Database manager initialized", database_url=settings.database_url)
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        # Import all models to ensure they're registered
        from ..services.auth_service import AuthorizedChannel, UserPermission
        from ..services.image_service import ImageRequest, ImageCollection
        from ..services.todo_service import TodoList, TodoTask
        from ..services.timezone_service import UserTimezone, Reminder
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()