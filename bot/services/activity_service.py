"""User activity tracking service."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from ..core.database import db_manager
from ..core.database import User, Message
from ..core.logging import get_logger

logger = get_logger(__name__)


class ActivityService:
    """Service for tracking and analyzing user activity."""
    
    def __init__(self):
        """Initialize the activity service."""
        logger.info("Activity service initialized")
    
    async def track_message(
        self, 
        user_id: int, 
        chat_id: int, 
        message_text: str,
        message_type: str = "text"
    ) -> None:
        """Track a user message for activity analysis."""
        try:
            async with db_manager.get_session() as session:
                # Create message record
                message = Message(
                    user_id=user_id,
                    chat_id=chat_id,
                    message_text=message_text[:1000],  # Truncate to prevent bloat
                    message_type=message_type,
                    created_at=datetime.utcnow()
                )
                session.add(message)
                await session.commit()
                
                logger.debug("Message tracked", user_id=user_id, chat_id=chat_id)
                
        except Exception as e:
            logger.error("Error tracking message", user_id=user_id, error=str(e), exc_info=True)
    
    async def get_night_owls(
        self, 
        chat_id: Optional[int] = None,
        hours_range: Tuple[int, int] = (22, 6),
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get users who are most active during night hours."""
        try:
            async with db_manager.get_session() as session:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Build query
                query = select(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    func.count(Message.id).label('night_messages')
                ).select_from(
                    Message.__table__.join(User.__table__)
                ).where(
                    and_(
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                        # Night hours (22:00-06:00)
                        func.extract('hour', Message.created_at).between(
                            hours_range[0] if hours_range[0] <= 23 else 0,
                            hours_range[1] if hours_range[1] >= 0 else 23
                        )
                    )
                ).group_by(
                    User.telegram_id,
                    User.username, 
                    User.first_name
                ).order_by(
                    desc('night_messages')
                ).limit(10)
                
                if chat_id:
                    query = query.where(Message.chat_id == chat_id)
                
                result = await session.execute(query)
                night_owls = []
                
                for row in result:
                    night_owls.append({
                        'user_id': row.telegram_id,
                        'username': row.username,
                        'first_name': row.first_name,
                        'night_messages': row.night_messages,
                        'display_name': row.first_name or row.username or f"User {row.telegram_id}"
                    })
                
                logger.info("Retrieved night owls", count=len(night_owls), chat_id=chat_id)
                return night_owls
                
        except Exception as e:
            logger.error("Error getting night owls", error=str(e), exc_info=True)
            return []
    
    async def get_most_active_users(
        self,
        chat_id: Optional[int] = None,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most active users by message count."""
        try:
            async with db_manager.get_session() as session:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Build query
                query = select(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    func.count(Message.id).label('message_count'),
                    func.avg(func.length(Message.message_text)).label('avg_message_length')
                ).select_from(
                    Message.__table__.join(User.__table__)
                ).where(
                    and_(
                        Message.created_at >= start_date,
                        Message.created_at <= end_date
                    )
                ).group_by(
                    User.telegram_id,
                    User.username,
                    User.first_name
                ).order_by(
                    desc('message_count')
                ).limit(limit)
                
                if chat_id:
                    query = query.where(Message.chat_id == chat_id)
                
                result = await session.execute(query)
                active_users = []
                
                for row in result:
                    active_users.append({
                        'user_id': row.telegram_id,
                        'username': row.username,
                        'first_name': row.first_name,
                        'message_count': row.message_count,
                        'avg_message_length': round(row.avg_message_length or 0, 1),
                        'display_name': row.first_name or row.username or f"User {row.telegram_id}"
                    })
                
                logger.info("Retrieved most active users", count=len(active_users), chat_id=chat_id)
                return active_users
                
        except Exception as e:
            logger.error("Error getting most active users", error=str(e), exc_info=True)
            return []
    
    async def get_user_activity_stats(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed activity statistics for a specific user."""
        try:
            async with db_manager.get_session() as session:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Build base query
                base_query = select(Message).where(
                    and_(
                        Message.user_id == user_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date
                    )
                )
                
                if chat_id:
                    base_query = base_query.where(Message.chat_id == chat_id)
                
                # Get total messages
                count_query = select(func.count(Message.id)).where(
                    base_query.whereclause
                )
                total_messages = await session.scalar(count_query)
                
                # Get hourly distribution
                hourly_query = select(
                    func.extract('hour', Message.created_at).label('hour'),
                    func.count(Message.id).label('count')
                ).where(
                    base_query.whereclause
                ).group_by(
                    'hour'
                ).order_by('hour')
                
                hourly_result = await session.execute(hourly_query)
                hourly_activity = {int(row.hour): row.count for row in hourly_result}
                
                return {
                    'user_id': user_id,
                    'total_messages': total_messages or 0,
                    'messages_per_day': round((total_messages or 0) / days, 2),
                    'hourly_distribution': hourly_activity,
                    'most_active_hour': max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else None,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error("Error getting user activity stats", user_id=user_id, error=str(e), exc_info=True)
            return {
                'user_id': user_id,
                'total_messages': 0,
                'messages_per_day': 0,
                'hourly_distribution': {},
                'most_active_hour': None,
                'period_days': days
            }
    
    async def get_chat_activity_summary(
        self,
        chat_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get overall activity summary for a chat."""
        try:
            async with db_manager.get_session() as session:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Total messages
                total_query = select(func.count(Message.id)).where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date
                    )
                )
                total_messages = await session.scalar(total_query) or 0
                
                # Unique users
                users_query = select(func.count(func.distinct(Message.user_id))).where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date
                    )
                )
                unique_users = await session.scalar(users_query) or 0
                
                # Daily breakdown
                daily_query = select(
                    func.date(Message.created_at).label('date'),
                    func.count(Message.id).label('count')
                ).where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date
                    )
                ).group_by('date').order_by('date')
                
                daily_result = await session.execute(daily_query)
                daily_activity = {str(row.date): row.count for row in daily_result}
                
                return {
                    'chat_id': chat_id,
                    'total_messages': total_messages,
                    'unique_users': unique_users,
                    'messages_per_day': round(total_messages / days, 2),
                    'messages_per_user': round(total_messages / unique_users, 2) if unique_users > 0 else 0,
                    'daily_breakdown': daily_activity,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error("Error getting chat activity summary", chat_id=chat_id, error=str(e), exc_info=True)
            return {
                'chat_id': chat_id,
                'total_messages': 0,
                'unique_users': 0,
                'messages_per_day': 0,
                'messages_per_user': 0,
                'daily_breakdown': {},
                'period_days': days
            }


# Global service instance
activity_service = ActivityService()