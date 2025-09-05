"""Timezone and reminder management service."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

from ..core.database import Base, db_manager
from ..core.logging import LoggerMixin
from ..core.exceptions import APIError


class UserTimezone(Base):
    """User timezone model."""
    
    __tablename__ = "user_timezones"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    timezone = Column(String(100), nullable=False, default="UTC")
    display_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Reminder(Base):
    """Reminder model."""
    
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(100), nullable=True)  # cron pattern
    is_active = Column(Boolean, default=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    job_id = Column(String(100), nullable=True)  # APScheduler job ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimezoneService(LoggerMixin):
    """Service for managing user timezones and reminders."""
    
    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        """Initialize the timezone service with scheduler."""
        self.scheduler = scheduler
        self.logger.info("Timezone service initialized")
    
    async def set_user_timezone(self, user_id: int, timezone_str: str) -> bool:
        """Set or update user's timezone."""
        try:
            # Validate timezone
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)
            display_name = f"{timezone_str} (UTC{now.strftime('%z')})"
            
            async with db_manager.get_session() as session:
                # Check if user already has timezone
                stmt = select(UserTimezone).where(UserTimezone.user_id == user_id)
                result = await session.execute(stmt)
                user_tz = result.scalar_one_or_none()
                
                if user_tz:
                    # Update existing
                    stmt = update(UserTimezone).where(
                        UserTimezone.user_id == user_id
                    ).values(
                        timezone=timezone_str,
                        display_name=display_name,
                        updated_at=datetime.utcnow()
                    )
                    await session.execute(stmt)
                    self.logger.info("User timezone updated", user_id=user_id, timezone=timezone_str)
                else:
                    # Create new
                    user_tz = UserTimezone(
                        user_id=user_id,
                        timezone=timezone_str,
                        display_name=display_name
                    )
                    session.add(user_tz)
                    self.logger.info("User timezone set", user_id=user_id, timezone=timezone_str)
                
                return True
                
        except Exception as e:
            self.logger.error("Error setting timezone", user_id=user_id, timezone=timezone_str, error=str(e))
            return False
    
    async def get_user_timezone(self, user_id: int) -> Optional[str]:
        """Get user's timezone, default to UTC."""
        try:
            async with db_manager.get_session() as session:
                stmt = select(UserTimezone).where(
                    UserTimezone.user_id == user_id,
                    UserTimezone.is_active == True
                )
                result = await session.execute(stmt)
                user_tz = result.scalar_one_or_none()
                
                if user_tz:
                    return user_tz.timezone
                return "UTC"
                
        except Exception as e:
            self.logger.error("Error getting timezone", user_id=user_id, error=str(e))
            return "UTC"
    
    async def convert_to_user_time(self, user_id: int, dt: datetime) -> datetime:
        """Convert datetime to user's timezone."""
        user_tz_str = await self.get_user_timezone(user_id)
        user_tz = ZoneInfo(user_tz_str)
        
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt.astimezone(user_tz)
    
    async def convert_from_user_time(self, user_id: int, dt: datetime) -> datetime:
        """Convert user's local time to UTC."""
        user_tz_str = await self.get_user_timezone(user_id)
        user_tz = ZoneInfo(user_tz_str)
        
        if dt.tzinfo is None:
            # Assume user's timezone
            dt = dt.replace(tzinfo=user_tz)
        
        return dt.astimezone(timezone.utc)
    
    async def create_reminder(
        self,
        user_id: int,
        chat_id: int,
        message: str,
        reminder_time: datetime,
        is_recurring: bool = False,
        recurrence_pattern: Optional[str] = None
    ) -> Optional[int]:
        """Create a new reminder."""
        try:
            # Convert to UTC
            utc_time = await self.convert_from_user_time(user_id, reminder_time)
            
            async with db_manager.get_session() as session:
                reminder = Reminder(
                    user_id=user_id,
                    chat_id=chat_id,
                    message=message,
                    reminder_time=utc_time,
                    is_recurring=is_recurring,
                    recurrence_pattern=recurrence_pattern
                )
                session.add(reminder)
                await session.flush()
                
                # Schedule the reminder
                job_id = f"reminder_{reminder.id}"
                
                if is_recurring and recurrence_pattern:
                    # Parse cron pattern and schedule recurring job
                    self.scheduler.add_job(
                        func=self._send_reminder,
                        trigger=CronTrigger.from_crontab(recurrence_pattern),
                        args=[reminder.id],
                        id=job_id,
                        replace_existing=True
                    )
                else:
                    # Schedule one-time reminder
                    self.scheduler.add_job(
                        func=self._send_reminder,
                        trigger=DateTrigger(run_date=utc_time),
                        args=[reminder.id],
                        id=job_id,
                        replace_existing=True
                    )
                
                # Update reminder with job ID
                reminder.job_id = job_id
                
                self.logger.info(
                    "Reminder created",
                    reminder_id=reminder.id,
                    user_id=user_id,
                    reminder_time=utc_time,
                    recurring=is_recurring
                )
                
                return reminder.id
                
        except Exception as e:
            self.logger.error("Error creating reminder", user_id=user_id, error=str(e), exc_info=True)
            return None
    
    async def _send_reminder(self, reminder_id: int) -> None:
        """Send a reminder (called by scheduler)."""
        try:
            from ..core.app import get_bot_instance  # Avoid circular import
            
            async with db_manager.get_session() as session:
                stmt = select(Reminder).where(
                    Reminder.id == reminder_id,
                    Reminder.is_active == True
                )
                result = await session.execute(stmt)
                reminder = result.scalar_one_or_none()
                
                if not reminder:
                    self.logger.warning("Reminder not found", reminder_id=reminder_id)
                    return
                
                # Send reminder message
                bot = get_bot_instance()
                if bot and bot.application:
                    await bot.application.bot.send_message(
                        chat_id=reminder.chat_id,
                        text=f"⏰ **Reminder**\\n\\n{reminder.message}",
                        parse_mode="Markdown"
                    )
                
                # Mark as sent for one-time reminders
                if not reminder.is_recurring:
                    stmt = update(Reminder).where(
                        Reminder.id == reminder_id
                    ).values(
                        is_sent=True,
                        sent_at=datetime.utcnow(),
                        is_active=False
                    )
                    await session.execute(stmt)
                
                self.logger.info("Reminder sent", reminder_id=reminder_id, user_id=reminder.user_id)
                
        except Exception as e:
            self.logger.error("Error sending reminder", reminder_id=reminder_id, error=str(e), exc_info=True)
    
    async def get_user_reminders(
        self,
        user_id: int,
        active_only: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's reminders."""
        try:
            async with db_manager.get_session() as session:
                stmt = select(Reminder).where(Reminder.user_id == user_id)
                
                if active_only:
                    stmt = stmt.where(Reminder.is_active == True)
                
                stmt = stmt.order_by(Reminder.reminder_time.asc()).limit(limit)
                
                result = await session.execute(stmt)
                reminders = result.scalars().all()
                
                result_list = []
                for reminder in reminders:
                    # Convert to user's timezone
                    user_time = await self.convert_to_user_time(user_id, reminder.reminder_time)
                    
                    result_list.append({
                        "id": reminder.id,
                        "message": reminder.message,
                        "reminder_time": user_time,
                        "reminder_time_utc": reminder.reminder_time,
                        "is_recurring": reminder.is_recurring,
                        "recurrence_pattern": reminder.recurrence_pattern,
                        "is_active": reminder.is_active,
                        "is_sent": reminder.is_sent,
                        "created_at": reminder.created_at
                    })
                
                return result_list
                
        except Exception as e:
            self.logger.error("Error getting reminders", user_id=user_id, error=str(e), exc_info=True)
            return []
    
    async def cancel_reminder(self, user_id: int, reminder_id: int) -> bool:
        """Cancel a reminder."""
        try:
            async with db_manager.get_session() as session:
                stmt = select(Reminder).where(
                    Reminder.id == reminder_id,
                    Reminder.user_id == user_id,
                    Reminder.is_active == True
                )
                result = await session.execute(stmt)
                reminder = result.scalar_one_or_none()
                
                if not reminder:
                    return False
                
                # Remove from scheduler
                if reminder.job_id:
                    try:
                        self.scheduler.remove_job(reminder.job_id)
                    except Exception:
                        pass  # Job might not exist
                
                # Mark as inactive
                stmt = update(Reminder).where(
                    Reminder.id == reminder_id
                ).values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
                await session.execute(stmt)
                
                self.logger.info("Reminder cancelled", reminder_id=reminder_id, user_id=user_id)
                return True
                
        except Exception as e:
            self.logger.error("Error cancelling reminder", reminder_id=reminder_id, user_id=user_id, error=str(e))
            return False
    
    async def get_timezone_info(self, timezone_str: str) -> Optional[Dict[str, Any]]:
        """Get timezone information."""
        try:
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)
            utc_now = datetime.now(timezone.utc)
            
            return {
                "timezone": timezone_str,
                "current_time": now,
                "utc_offset": now.strftime("%z"),
                "display_name": f"{timezone_str} (UTC{now.strftime('%z')})",
                "is_dst": now.dst() != timedelta(0),
                "utc_difference_hours": (now.utcoffset().total_seconds() / 3600) if now.utcoffset() else 0
            }
            
        except Exception as e:
            self.logger.error("Error getting timezone info", timezone=timezone_str, error=str(e))
            return None
    
    async def search_timezones(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for timezones matching the query."""
        from zoneinfo import available_timezones
        
        query = query.lower()
        results = []
        
        # Common timezone mappings
        common_timezones = {
            "new york": "America/New_York",
            "los angeles": "America/Los_Angeles",
            "london": "Europe/London",
            "paris": "Europe/Paris",
            "tokyo": "Asia/Tokyo",
            "sydney": "Australia/Sydney",
            "moscow": "Europe/Moscow",
            "dubai": "Asia/Dubai",
            "singapore": "Asia/Singapore",
            "berlin": "Europe/Berlin",
            "mumbai": "Asia/Kolkata",
            "beijing": "Asia/Shanghai",
            "cairo": "Africa/Cairo",
            "mexico city": "America/Mexico_City",
            "chicago": "America/Chicago",
            "denver": "America/Denver",
            "phoenix": "America/Phoenix",
            "toronto": "America/Toronto",
            "vancouver": "America/Vancouver",
            "montreal": "America/Montreal",
            "sao paulo": "America/Sao_Paulo",
            "buenos aires": "America/Argentina/Buenos_Aires",
            "lima": "America/Lima",
            "bogota": "America/Bogota",
            "helsinki": "Europe/Helsinki",
            "stockholm": "Europe/Stockholm",
            "oslo": "Europe/Oslo",
            "copenhagen": "Europe/Copenhagen",
            "amsterdam": "Europe/Amsterdam",
            "zurich": "Europe/Zurich",
            "rome": "Europe/Rome",
            "madrid": "Europe/Madrid",
            "lisbon": "Europe/Lisbon",
            "athens": "Europe/Athens",
            "istanbul": "Europe/Istanbul",
            "tel aviv": "Asia/Jerusalem",
            "riyadh": "Asia/Riyadh",
            "tehran": "Asia/Tehran",
            "karachi": "Asia/Karachi",
            "dhaka": "Asia/Dhaka",
            "bangkok": "Asia/Bangkok",
            "jakarta": "Asia/Jakarta",
            "manila": "Asia/Manila",
            "seoul": "Asia/Seoul",
            "hong kong": "Asia/Hong_Kong",
            "taipei": "Asia/Taipei",
            "perth": "Australia/Perth",
            "melbourne": "Australia/Melbourne",
            "brisbane": "Australia/Brisbane",
            "auckland": "Pacific/Auckland",
            "fiji": "Pacific/Fiji",
            "honolulu": "Pacific/Honolulu",
            "anchorage": "America/Anchorage",
        }
        
        # Check common timezones first
        for city, tz in common_timezones.items():
            if query in city or query in tz.lower():
                try:
                    info = await self.get_timezone_info(tz)
                    if info:
                        results.append({
                            "timezone": tz,
                            "display_name": info["display_name"],
                            "city": city.title()
                        })
                except Exception:
                    pass
        
        # Search all available timezones if not enough results
        if len(results) < limit:
            for tz in available_timezones():
                if len(results) >= limit:
                    break
                    
                if query in tz.lower() and tz not in [r["timezone"] for r in results]:
                    try:
                        info = await self.get_timezone_info(tz)
                        if info:
                            results.append({
                                "timezone": tz,
                                "display_name": info["display_name"],
                                "city": tz.split("/")[-1].replace("_", " ")
                            })
                    except Exception:
                        pass
        
        return results[:limit]


# Global timezone service will be initialized with scheduler
timezone_service: Optional[TimezoneService] = None