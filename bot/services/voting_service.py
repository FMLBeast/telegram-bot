"""Voting and polling service for the bot."""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from enum import Enum
import json

from ..core.database import Base, db_manager
from ..core.logging import LoggerMixin
from ..core.exceptions import APIError


class PollStatus(str, Enum):
    """Poll status enumeration."""
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PollType(str, Enum):
    """Poll type enumeration."""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    ANONYMOUS = "anonymous"
    QUIZ = "quiz"


class Poll(Base):
    """Poll model."""
    
    __tablename__ = "polls"
    
    id = Column(Integer, primary_key=True)
    creator_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    poll_type = Column(String(20), default=PollType.SINGLE_CHOICE)
    options = Column(Text, nullable=False)  # JSON string of options
    correct_option = Column(Integer, nullable=True)  # For quiz polls
    is_anonymous = Column(Boolean, default=False)
    allows_multiple = Column(Boolean, default=False)
    duration_minutes = Column(Integer, default=1440)  # 24 hours default
    status = Column(String(20), default=PollStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    votes = relationship("PollVote", back_populates="poll", cascade="all, delete-orphan")


class PollVote(Base):
    """Poll vote model."""
    
    __tablename__ = "poll_votes"
    
    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    option_ids = Column(Text, nullable=False)  # JSON array of selected option IDs
    voted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    poll = relationship("Poll", back_populates="votes")


class VotingService(LoggerMixin):
    """Service for voting and polling functionality."""
    
    def __init__(self) -> None:
        """Initialize the voting service."""
        self.active_polls = {}  # Cache for active polls
        self.logger.info("Voting service initialized")
    
    async def create_poll(
        self,
        creator_id: int,
        chat_id: int,
        title: str,
        options: List[str],
        description: Optional[str] = None,
        poll_type: PollType = PollType.SINGLE_CHOICE,
        duration_minutes: int = 1440,
        is_anonymous: bool = False,
        correct_option: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new poll."""
        try:
            if len(options) < 2:
                raise APIError("Poll must have at least 2 options")
            
            if len(options) > 10:
                raise APIError("Poll cannot have more than 10 options")
            
            if poll_type == PollType.QUIZ and correct_option is None:
                raise APIError("Quiz polls must have a correct answer")
            
            if poll_type == PollType.QUIZ and (correct_option < 0 or correct_option >= len(options)):
                raise APIError("Correct option index is invalid")
            
            expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
            
            async with db_manager.get_session() as session:
                poll = Poll(
                    creator_id=creator_id,
                    chat_id=chat_id,
                    title=title,
                    description=description,
                    poll_type=poll_type,
                    options=json.dumps(options),
                    correct_option=correct_option,
                    is_anonymous=is_anonymous,
                    allows_multiple=(poll_type == PollType.MULTIPLE_CHOICE),
                    duration_minutes=duration_minutes,
                    expires_at=expires_at
                )
                
                session.add(poll)
                await session.flush()
                
                self.logger.info(
                    "Poll created",
                    poll_id=poll.id,
                    creator_id=creator_id,
                    chat_id=chat_id,
                    title=title,
                    options_count=len(options)
                )
                
                return {
                    "id": poll.id,
                    "title": title,
                    "description": description,
                    "options": options,
                    "poll_type": poll_type,
                    "is_anonymous": is_anonymous,
                    "allows_multiple": poll.allows_multiple,
                    "duration_minutes": duration_minutes,
                    "expires_at": expires_at,
                    "correct_option": correct_option
                }
                
        except Exception as e:
            self.logger.error("Error creating poll", error=str(e), exc_info=True)
            return None
    
    async def get_poll(self, poll_id: int) -> Optional[Dict[str, Any]]:
        """Get poll by ID."""
        async with db_manager.get_session() as session:
            stmt = select(Poll).where(Poll.id == poll_id)
            result = await session.execute(stmt)
            poll = result.scalar_one_or_none()
            
            if not poll:
                return None
            
            # Get vote counts
            vote_counts = await self.get_poll_results(poll_id)
            
            return {
                "id": poll.id,
                "creator_id": poll.creator_id,
                "chat_id": poll.chat_id,
                "title": poll.title,
                "description": poll.description,
                "options": json.loads(poll.options),
                "poll_type": poll.poll_type,
                "is_anonymous": poll.is_anonymous,
                "allows_multiple": poll.allows_multiple,
                "duration_minutes": poll.duration_minutes,
                "status": poll.status,
                "created_at": poll.created_at,
                "expires_at": poll.expires_at,
                "closed_at": poll.closed_at,
                "correct_option": poll.correct_option,
                "vote_counts": vote_counts["counts"],
                "total_votes": vote_counts["total_votes"],
                "unique_voters": vote_counts["unique_voters"]
            }
    
    async def vote_on_poll(
        self,
        poll_id: int,
        user_id: int,
        option_ids: List[int]
    ) -> Optional[Dict[str, Any]]:
        """Cast a vote on a poll."""
        try:
            async with db_manager.get_session() as session:
                # Get poll
                stmt = select(Poll).where(Poll.id == poll_id)
                result = await session.execute(stmt)
                poll = result.scalar_one_or_none()
                
                if not poll:
                    raise APIError("Poll not found")
                
                if poll.status != PollStatus.ACTIVE:
                    raise APIError("Poll is not active")
                
                if datetime.utcnow() > poll.expires_at:
                    # Auto-close expired poll
                    poll.status = PollStatus.CLOSED
                    poll.closed_at = datetime.utcnow()
                    raise APIError("Poll has expired")
                
                options = json.loads(poll.options)
                
                # Validate option IDs
                for option_id in option_ids:
                    if option_id < 0 or option_id >= len(options):
                        raise APIError(f"Invalid option ID: {option_id}")
                
                # Check if multiple votes allowed
                if not poll.allows_multiple and len(option_ids) > 1:
                    raise APIError("This poll only allows single choice")
                
                # Check if user already voted
                existing_vote_stmt = select(PollVote).where(
                    PollVote.poll_id == poll_id,
                    PollVote.user_id == user_id
                )
                existing_vote_result = await session.execute(existing_vote_stmt)
                existing_vote = existing_vote_result.scalar_one_or_none()
                
                if existing_vote:
                    # Update existing vote
                    existing_vote.option_ids = json.dumps(option_ids)
                    existing_vote.voted_at = datetime.utcnow()
                    action = "updated"
                else:
                    # Create new vote
                    vote = PollVote(
                        poll_id=poll_id,
                        user_id=user_id,
                        option_ids=json.dumps(option_ids)
                    )
                    session.add(vote)
                    action = "cast"
                
                self.logger.info(
                    f"Vote {action}",
                    poll_id=poll_id,
                    user_id=user_id,
                    option_ids=option_ids
                )
                
                return {
                    "poll_id": poll_id,
                    "user_id": user_id,
                    "option_ids": option_ids,
                    "action": action
                }
                
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error voting on poll", poll_id=poll_id, user_id=user_id, 
                            error=str(e), exc_info=True)
            return None
    
    async def get_poll_results(self, poll_id: int) -> Dict[str, Any]:
        """Get poll results."""
        async with db_manager.get_session() as session:
            # Get poll info
            poll_stmt = select(Poll).where(Poll.id == poll_id)
            poll_result = await session.execute(poll_stmt)
            poll = poll_result.scalar_one_or_none()
            
            if not poll:
                return {"counts": [], "total_votes": 0, "unique_voters": 0}
            
            options = json.loads(poll.options)
            
            # Get all votes
            votes_stmt = select(PollVote).where(PollVote.poll_id == poll_id)
            votes_result = await session.execute(votes_stmt)
            votes = votes_result.scalars().all()
            
            # Count votes for each option
            option_counts = [0] * len(options)
            unique_voters = len(votes)
            total_votes = 0
            
            for vote in votes:
                vote_option_ids = json.loads(vote.option_ids)
                for option_id in vote_option_ids:
                    if 0 <= option_id < len(options):
                        option_counts[option_id] += 1
                        total_votes += 1
            
            return {
                "counts": option_counts,
                "total_votes": total_votes,
                "unique_voters": unique_voters
            }
    
    async def close_poll(self, poll_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Close a poll."""
        async with db_manager.get_session() as session:
            stmt = select(Poll).where(Poll.id == poll_id)
            result = await session.execute(stmt)
            poll = result.scalar_one_or_none()
            
            if not poll:
                return None
            
            if poll.creator_id != user_id:
                raise APIError("Only the poll creator can close this poll")
            
            if poll.status != PollStatus.ACTIVE:
                raise APIError("Poll is already closed")
            
            poll.status = PollStatus.CLOSED
            poll.closed_at = datetime.utcnow()
            
            self.logger.info("Poll closed", poll_id=poll_id, user_id=user_id)
            
            # Get final results
            results = await self.get_poll_results(poll_id)
            
            return {
                "poll_id": poll_id,
                "closed_at": poll.closed_at,
                "results": results
            }
    
    async def get_active_polls(self, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get active polls."""
        async with db_manager.get_session() as session:
            stmt = select(Poll).where(
                Poll.status == PollStatus.ACTIVE,
                Poll.expires_at > datetime.utcnow()
            )
            
            if chat_id:
                stmt = stmt.where(Poll.chat_id == chat_id)
            
            stmt = stmt.order_by(Poll.created_at.desc())
            
            result = await session.execute(stmt)
            polls = result.scalars().all()
            
            poll_list = []
            for poll in polls:
                results = await self.get_poll_results(poll.id)
                poll_list.append({
                    "id": poll.id,
                    "title": poll.title,
                    "description": poll.description,
                    "options": json.loads(poll.options),
                    "poll_type": poll.poll_type,
                    "is_anonymous": poll.is_anonymous,
                    "allows_multiple": poll.allows_multiple,
                    "creator_id": poll.creator_id,
                    "chat_id": poll.chat_id,
                    "created_at": poll.created_at,
                    "expires_at": poll.expires_at,
                    "vote_counts": results["counts"],
                    "total_votes": results["total_votes"],
                    "unique_voters": results["unique_voters"]
                })
            
            return poll_list
    
    async def get_user_votes(self, user_id: int, poll_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get user's votes."""
        async with db_manager.get_session() as session:
            stmt = select(PollVote, Poll).join(Poll).where(PollVote.user_id == user_id)
            
            if poll_id:
                stmt = stmt.where(PollVote.poll_id == poll_id)
            
            stmt = stmt.order_by(PollVote.voted_at.desc())
            
            result = await session.execute(stmt)
            vote_data = result.all()
            
            votes = []
            for vote, poll in vote_data:
                options = json.loads(poll.options)
                option_ids = json.loads(vote.option_ids)
                selected_options = [options[i] for i in option_ids if 0 <= i < len(options)]
                
                votes.append({
                    "poll_id": vote.poll_id,
                    "poll_title": poll.title,
                    "option_ids": option_ids,
                    "selected_options": selected_options,
                    "voted_at": vote.voted_at,
                    "poll_status": poll.status
                })
            
            return votes
    
    async def cleanup_expired_polls(self) -> int:
        """Clean up expired polls."""
        try:
            async with db_manager.get_session() as session:
                # Close expired active polls
                stmt = update(Poll).where(
                    Poll.status == PollStatus.ACTIVE,
                    Poll.expires_at <= datetime.utcnow()
                ).values(
                    status=PollStatus.CLOSED,
                    closed_at=datetime.utcnow()
                )
                
                result = await session.execute(stmt)
                closed_count = result.rowcount
                
                if closed_count > 0:
                    self.logger.info("Closed expired polls", count=closed_count)
                
                return closed_count
                
        except Exception as e:
            self.logger.error("Error cleaning up expired polls", error=str(e), exc_info=True)
            return 0


# Global voting service instance
voting_service = VotingService()