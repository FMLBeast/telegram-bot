"""Mood analysis service using OpenAI."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc

from ..core.database import db_manager
from ..core.database import User, Message
from ..services.openai_service import OpenAIService
from ..core.logging import get_logger

logger = get_logger(__name__)


class MoodService:
    """Service for analyzing user mood based on messages."""
    
    def __init__(self):
        """Initialize the mood service."""
        self.openai_service = OpenAIService()
        logger.info("Mood service initialized")
    
    async def analyze_user_mood(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        days: int = 3,
        max_messages: int = 20
    ) -> Dict[str, Any]:
        """Analyze a user's mood based on recent messages."""
        try:
            # Get recent messages from user
            recent_messages = await self._get_recent_messages(
                user_id=user_id,
                chat_id=chat_id,
                days=days,
                max_messages=max_messages
            )
            
            if not recent_messages:
                return {
                    'user_id': user_id,
                    'mood': 'unknown',
                    'confidence': 0.0,
                    'analysis': 'No recent messages found for analysis',
                    'suggestions': [],
                    'message_count': 0
                }
            
            # Prepare messages for analysis
            message_texts = [msg['text'] for msg in recent_messages]
            combined_text = '\n'.join(message_texts)
            
            # Analyze mood using OpenAI
            mood_analysis = await self._analyze_mood_with_ai(combined_text, len(message_texts))
            
            # Get user info
            user_info = await self._get_user_info(user_id)
            
            result = {
                'user_id': user_id,
                'username': user_info.get('username'),
                'first_name': user_info.get('first_name'),
                'message_count': len(message_texts),
                'analysis_period_days': days,
                **mood_analysis
            }
            
            logger.info("Mood analysis completed", user_id=user_id, mood=mood_analysis.get('mood'))
            return result
            
        except Exception as e:
            logger.error("Error analyzing user mood", user_id=user_id, error=str(e), exc_info=True)
            return {
                'user_id': user_id,
                'mood': 'error',
                'confidence': 0.0,
                'analysis': f'Error analyzing mood: {str(e)}',
                'suggestions': [],
                'message_count': 0
            }
    
    async def _get_recent_messages(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        days: int = 3,
        max_messages: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a user."""
        try:
            async with db_manager.get_session() as session:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Build query
                query = select(Message).where(
                    and_(
                        Message.user_id == user_id,
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                        Message.message_text.isnot(None),
                        Message.message_text != ''
                    )
                ).order_by(desc(Message.created_at)).limit(max_messages)
                
                if chat_id:
                    query = query.where(Message.chat_id == chat_id)
                
                result = await session.execute(query)
                messages = []
                
                for message in result.scalars():
                    messages.append({
                        'text': message.message_text,
                        'created_at': message.created_at,
                        'chat_id': message.chat_id
                    })
                
                return messages
                
        except Exception as e:
            logger.error("Error getting recent messages", user_id=user_id, error=str(e), exc_info=True)
            return []
    
    async def _get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get user information."""
        try:
            async with db_manager.get_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if user:
                    return {
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    }
                return {}
                
        except Exception as e:
            logger.error("Error getting user info", user_id=user_id, error=str(e), exc_info=True)
            return {}
    
    async def _analyze_mood_with_ai(self, text: str, message_count: int) -> Dict[str, Any]:
        """Use OpenAI to analyze mood from text."""
        try:
            prompt = f"""
            Analyze the emotional mood and sentiment of the following {message_count} recent messages from a user.
            
            Messages:
            {text}
            
            Please provide:
            1. Primary mood (happy, sad, angry, anxious, excited, neutral, frustrated, content, etc.)
            2. Confidence level (0.0 to 1.0)
            3. Brief analysis explaining the mood assessment
            4. 2-3 supportive suggestions or observations
            
            Respond in JSON format:
            {{
                "mood": "primary_mood",
                "confidence": 0.0,
                "analysis": "brief explanation",
                "suggestions": ["suggestion1", "suggestion2"]
            }}
            """
            
            response = await self.openai_service.generate_response(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )
            
            # Try to parse JSON response
            import json
            try:
                mood_data = json.loads(response)
                return mood_data
            except json.JSONDecodeError:
                # Fallback to basic parsing
                return {
                    'mood': 'neutral',
                    'confidence': 0.5,
                    'analysis': response[:200] + '...' if len(response) > 200 else response,
                    'suggestions': ['Take time for self-care', 'Stay connected with friends']
                }
            
        except Exception as e:
            logger.error("Error analyzing mood with AI", error=str(e), exc_info=True)
            return {
                'mood': 'unknown',
                'confidence': 0.0,
                'analysis': f'Unable to analyze mood: {str(e)}',
                'suggestions': ['Try expressing your thoughts more clearly', 'Consider talking to someone you trust']
            }
    
    async def get_mood_trends(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        days: int = 14
    ) -> Dict[str, Any]:
        """Analyze mood trends over time for a user."""
        try:
            # Get mood data points over time
            mood_points = []
            current_date = datetime.utcnow()
            
            # Sample mood every 2 days
            for i in range(0, days, 2):
                sample_date = current_date - timedelta(days=i)
                start_date = sample_date - timedelta(days=1)
                
                # Get messages for this period
                async with db_manager.get_session() as session:
                    query = select(Message.message_text).where(
                        and_(
                            Message.user_id == user_id,
                            Message.created_at >= start_date,
                            Message.created_at < sample_date,
                            Message.message_text.isnot(None),
                            Message.message_text != ''
                        )
                    ).limit(10)
                    
                    if chat_id:
                        query = query.where(Message.chat_id == chat_id)
                    
                    result = await session.execute(query)
                    messages = [row[0] for row in result]
                    
                    if messages:
                        combined_text = '\n'.join(messages)
                        mood_analysis = await self._analyze_mood_with_ai(combined_text, len(messages))
                        
                        mood_points.append({
                            'date': start_date.strftime('%Y-%m-%d'),
                            'mood': mood_analysis['mood'],
                            'confidence': mood_analysis['confidence'],
                            'message_count': len(messages)
                        })
            
            # Analyze trends
            if mood_points:
                moods = [point['mood'] for point in mood_points]
                avg_confidence = sum(point['confidence'] for point in mood_points) / len(mood_points)
                
                # Simple trend analysis
                positive_moods = ['happy', 'excited', 'content', 'joyful']
                negative_moods = ['sad', 'angry', 'anxious', 'frustrated', 'depressed']
                
                positive_count = sum(1 for mood in moods if mood in positive_moods)
                negative_count = sum(1 for mood in moods if mood in negative_moods)
                
                if positive_count > negative_count:
                    overall_trend = 'positive'
                elif negative_count > positive_count:
                    overall_trend = 'negative'
                else:
                    overall_trend = 'neutral'
                
                return {
                    'user_id': user_id,
                    'period_days': days,
                    'mood_points': mood_points,
                    'overall_trend': overall_trend,
                    'average_confidence': round(avg_confidence, 2),
                    'positive_days': positive_count,
                    'negative_days': negative_count,
                    'total_samples': len(mood_points)
                }
            
            return {
                'user_id': user_id,
                'period_days': days,
                'mood_points': [],
                'overall_trend': 'unknown',
                'average_confidence': 0.0,
                'positive_days': 0,
                'negative_days': 0,
                'total_samples': 0
            }
            
        except Exception as e:
            logger.error("Error getting mood trends", user_id=user_id, error=str(e), exc_info=True)
            return {
                'user_id': user_id,
                'error': str(e),
                'period_days': days,
                'mood_points': [],
                'overall_trend': 'error',
                'average_confidence': 0.0,
                'positive_days': 0,
                'negative_days': 0,
                'total_samples': 0
            }


# Global service instance
mood_service = MoodService()