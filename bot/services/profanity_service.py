"""Profanity monitoring and counting service."""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, and_
from collections import defaultdict

from ..core.database import db_manager
from ..core.database import Message, User
from ..core.logging import get_logger

logger = get_logger(__name__)


class ProfanityService:
    """Service for monitoring and counting profanity usage."""
    
    def __init__(self):
        """Initialize the profanity service."""
        # Common profanity words to monitor
        self.monitored_words = {
            'cunt', 'fuck', 'shit', 'bitch', 'ass', 'damn', 'hell',
            'piss', 'cock', 'dick', 'pussy', 'whore', 'slut', 'bastard'
        }
        logger.info("Profanity service initialized with monitored words", 
                   word_count=len(self.monitored_words))
    
    async def check_and_count_profanity(
        self, 
        user_id: int, 
        chat_id: int, 
        text: str
    ) -> Dict[str, int]:
        """Check text for profanity and return counts."""
        if not text:
            return {}
        
        text_lower = text.lower()
        found_words = {}
        
        for word in self.monitored_words:
            count = text_lower.count(word)
            if count > 0:
                found_words[word] = count
                
        if found_words:
            await self._log_profanity_usage(user_id, chat_id, found_words, text)
            logger.debug("Profanity detected", user_id=user_id, words=list(found_words.keys()))
        
        return found_words
    
    async def get_user_profanity_stats(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, any]:
        """Get profanity statistics for a user."""
        try:
            async with db_manager.get_session() as session:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Get user info
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                # Build query for messages with profanity
                query = select(Message.text).where(
                    and_(
                        Message.user_id == user_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                        Message.text.isnot(None),
                        Message.text != ''
                    )
                )
                
                if chat_id:
                    query = query.where(Message.chat_id == chat_id)
                
                result = await session.execute(query)
                messages = [row[0] for row in result]
                
                # Count profanity in messages
                word_counts = defaultdict(int)
                total_profanity = 0
                messages_with_profanity = 0
                
                for message in messages:
                    message_lower = message.lower()
                    has_profanity = False
                    
                    for word in self.monitored_words:
                        count = message_lower.count(word)
                        if count > 0:
                            word_counts[word] += count
                            total_profanity += count
                            has_profanity = True
                    
                    if has_profanity:
                        messages_with_profanity += 1
                
                # Get top words
                top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                return {
                    'user_id': user_id,
                    'username': user.username if user else None,
                    'first_name': user.first_name if user else None,
                    'display_name': (user.first_name or user.username or f"User {user_id}") if user else f"User {user_id}",
                    'total_profanity_count': total_profanity,
                    'messages_with_profanity': messages_with_profanity,
                    'total_messages_checked': len(messages),
                    'profanity_rate': round((messages_with_profanity / len(messages)) * 100, 2) if messages else 0,
                    'top_words': top_words,
                    'word_counts': dict(word_counts),
                    'period_days': days
                }
                
        except Exception as e:
            logger.error("Error getting user profanity stats", 
                        user_id=user_id, error=str(e), exc_info=True)
            return {
                'user_id': user_id,
                'error': str(e),
                'total_profanity_count': 0,
                'messages_with_profanity': 0,
                'total_messages_checked': 0,
                'profanity_rate': 0,
                'top_words': [],
                'word_counts': {},
                'period_days': days
            }
    
    async def get_chat_profanity_leaderboard(
        self,
        chat_id: int,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, any]]:
        """Get profanity leaderboard for a chat."""
        try:
            async with db_manager.get_session() as session:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Get all users and their messages
                query = select(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    func.count(Message.id).label('total_messages')
                ).select_from(
                    Message.__table__.join(User.__table__, Message.user_id == User.telegram_id)
                ).where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                        Message.text.isnot(None),
                        Message.text != ''
                    )
                ).group_by(
                    User.telegram_id,
                    User.username,
                    User.first_name
                )
                
                result = await session.execute(query)
                users_data = []
                
                for row in result:
                    user_stats = await self.get_user_profanity_stats(
                        row.telegram_id, 
                        chat_id=chat_id,
                        days=days
                    )
                    
                    if user_stats['total_profanity_count'] > 0:
                        users_data.append({
                            'user_id': row.telegram_id,
                            'username': row.username,
                            'first_name': row.first_name,
                            'display_name': row.first_name or row.username or f"User {row.telegram_id}",
                            'total_profanity_count': user_stats['total_profanity_count'],
                            'messages_with_profanity': user_stats['messages_with_profanity'],
                            'profanity_rate': user_stats['profanity_rate'],
                            'top_word': user_stats['top_words'][0][0] if user_stats['top_words'] else None,
                            'top_word_count': user_stats['top_words'][0][1] if user_stats['top_words'] else 0,
                            'total_messages': row.total_messages
                        })
                
                # Sort by total profanity count
                users_data.sort(key=lambda x: x['total_profanity_count'], reverse=True)
                return users_data[:limit]
                
        except Exception as e:
            logger.error("Error getting chat profanity leaderboard", 
                        chat_id=chat_id, error=str(e), exc_info=True)
            return []
    
    async def get_word_specific_stats(
        self,
        word: str,
        chat_id: Optional[int] = None,
        days: int = 7,
        limit: int = 10
    ) -> Dict[str, any]:
        """Get statistics for a specific word."""
        word = word.lower()
        if word not in self.monitored_words:
            return {'error': f'Word "{word}" is not monitored'}
        
        try:
            async with db_manager.get_session() as session:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Build query
                query = select(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    Message.text
                ).select_from(
                    Message.__table__.join(User.__table__, Message.user_id == User.telegram_id)
                ).where(
                    and_(
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                        Message.text.isnot(None),
                        Message.text != '',
                        func.lower(Message.text).contains(word)
                    )
                )
                
                if chat_id:
                    query = query.where(Message.chat_id == chat_id)
                
                result = await session.execute(query)
                
                user_counts = defaultdict(int)
                total_count = 0
                
                for row in result:
                    count = row.text.lower().count(word)
                    user_counts[(row.telegram_id, row.username, row.first_name)] += count
                    total_count += count
                
                # Convert to list format
                top_users = []
                for (user_id, username, first_name), count in user_counts.items():
                    top_users.append({
                        'user_id': user_id,
                        'username': username,
                        'first_name': first_name,
                        'display_name': first_name or username or f"User {user_id}",
                        'count': count
                    })
                
                top_users.sort(key=lambda x: x['count'], reverse=True)
                
                return {
                    'word': word,
                    'total_usage': total_count,
                    'unique_users': len(user_counts),
                    'top_users': top_users[:limit],
                    'period_days': days
                }
                
        except Exception as e:
            logger.error("Error getting word specific stats", 
                        word=word, error=str(e), exc_info=True)
            return {'error': str(e), 'word': word}
    
    async def _log_profanity_usage(
        self,
        user_id: int,
        chat_id: int,
        words: Dict[str, int],
        original_text: str
    ) -> None:
        """Log profanity usage for analytics."""
        try:
            total_count = sum(words.values())
            word_list = list(words.keys())
            
            logger.info("Profanity usage logged",
                       user_id=user_id,
                       chat_id=chat_id,
                       words=word_list,
                       total_count=total_count,
                       text_preview=original_text[:50] + "..." if len(original_text) > 50 else original_text)
        except Exception as e:
            logger.error("Error logging profanity usage", error=str(e), exc_info=True)
    
    def add_monitored_word(self, word: str) -> bool:
        """Add a new word to monitor."""
        word = word.lower().strip()
        if word and word not in self.monitored_words:
            self.monitored_words.add(word)
            logger.info("Added new monitored word", word=word)
            return True
        return False
    
    def remove_monitored_word(self, word: str) -> bool:
        """Remove a word from monitoring."""
        word = word.lower().strip()
        if word in self.monitored_words:
            self.monitored_words.remove(word)
            logger.info("Removed monitored word", word=word)
            return True
        return False
    
    def get_monitored_words(self) -> Set[str]:
        """Get all currently monitored words."""
        return self.monitored_words.copy()


# Global service instance
profanity_service = ProfanityService()