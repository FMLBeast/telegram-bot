"""Todo list and task management service."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from ..core.database import Base, db_manager
from ..core.logging import LoggerMixin
from ..core.exceptions import APIError


class TodoList(Base):
    """Todo list model."""
    
    __tablename__ = "todo_lists"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to tasks
    tasks = relationship("TodoTask", back_populates="todo_list", cascade="all, delete-orphan")


class TodoTask(Base):
    """Todo task model."""
    
    __tablename__ = "todo_tasks"
    
    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("todo_lists.id"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    status = Column(String(20), default="pending")  # pending, in_progress, completed, cancelled
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    position = Column(Integer, default=0)  # For ordering
    tags = Column(String(500), nullable=True)  # JSON array of tags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to list
    todo_list = relationship("TodoList", back_populates="tasks")


class TodoService(LoggerMixin):
    """Service for managing todo lists and tasks."""
    
    def __init__(self) -> None:
        """Initialize the todo service."""
        self.logger.info("Todo service initialized")
    
    async def ensure_default_list(self, user_id: int) -> int:
        """Ensure user has a default todo list and return its ID."""
        async with db_manager.get_session() as session:
            # Check if user has a default list
            stmt = select(TodoList).where(
                TodoList.user_id == user_id,
                TodoList.is_default == True,
                TodoList.is_active == True
            )
            result = await session.execute(stmt)
            default_list = result.scalar_one_or_none()
            
            if not default_list:
                # Create default list
                default_list = TodoList(
                    user_id=user_id,
                    name="My Tasks",
                    description="Default todo list",
                    is_default=True
                )
                session.add(default_list)
                await session.flush()
                self.logger.info("Created default todo list", user_id=user_id, list_id=default_list.id)
            
            return default_list.id
    
    async def create_list(self, user_id: int, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new todo list."""
        async with db_manager.get_session() as session:
            todo_list = TodoList(
                user_id=user_id,
                name=name[:255],
                description=description
            )
            session.add(todo_list)
            await session.flush()
            
            result = {
                "id": todo_list.id,
                "name": todo_list.name,
                "description": todo_list.description,
                "created_at": todo_list.created_at
            }
            
            self.logger.info("Todo list created", user_id=user_id, list_id=todo_list.id)
            return result
    
    async def get_user_lists(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all todo lists for a user."""
        async with db_manager.get_session() as session:
            stmt = select(TodoList).where(
                TodoList.user_id == user_id,
                TodoList.is_active == True
            ).order_by(TodoList.is_default.desc(), TodoList.created_at)
            
            result = await session.execute(stmt)
            lists = result.scalars().all()
            
            return [
                {
                    "id": lst.id,
                    "name": lst.name,
                    "description": lst.description,
                    "is_default": lst.is_default,
                    "task_count": len([t for t in lst.tasks if t.status != "cancelled"]),
                    "completed_count": len([t for t in lst.tasks if t.status == "completed"]),
                    "created_at": lst.created_at
                }
                for lst in lists
            ]
    
    async def add_task(
        self,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[datetime] = None,
        list_id: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add a new task to a todo list."""
        if not list_id:
            list_id = await self.ensure_default_list(user_id)
        
        async with db_manager.get_session() as session:
            # Get next position
            stmt = select(func.max(TodoTask.position)).where(
                TodoTask.list_id == list_id,
                TodoTask.status != "cancelled"
            )
            result = await session.execute(stmt)
            max_position = result.scalar() or 0
            
            task = TodoTask(
                list_id=list_id,
                user_id=user_id,
                title=title[:500],
                description=description,
                priority=priority,
                due_date=due_date,
                position=max_position + 1,
                tags=",".join(tags) if tags else None
            )
            session.add(task)
            await session.flush()
            
            result = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "due_date": task.due_date,
                "tags": task.tags.split(",") if task.tags else [],
                "created_at": task.created_at
            }
            
            self.logger.info("Task added", user_id=user_id, task_id=task.id, list_id=list_id)
            return result
    
    async def get_tasks(
        self,
        user_id: int,
        list_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get tasks for a user, optionally filtered by list and status."""
        async with db_manager.get_session() as session:
            stmt = select(TodoTask).where(TodoTask.user_id == user_id)
            
            if list_id:
                stmt = stmt.where(TodoTask.list_id == list_id)
            else:
                # Get default list if no list specified
                default_list_id = await self.ensure_default_list(user_id)
                stmt = stmt.where(TodoTask.list_id == default_list_id)
            
            if status:
                stmt = stmt.where(TodoTask.status == status)
            else:
                stmt = stmt.where(TodoTask.status != "cancelled")
            
            stmt = stmt.order_by(
                TodoTask.status.asc(),  # pending first
                TodoTask.priority.desc(),  # high priority first
                TodoTask.position.asc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            
            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority,
                    "status": task.status,
                    "due_date": task.due_date,
                    "tags": task.tags.split(",") if task.tags else [],
                    "created_at": task.created_at,
                    "completed_at": task.completed_at
                }
                for task in tasks
            ]
    
    async def update_task_status(
        self,
        user_id: int,
        task_id: int,
        status: str
    ) -> bool:
        """Update task status."""
        async with db_manager.get_session() as session:
            stmt = update(TodoTask).where(
                TodoTask.id == task_id,
                TodoTask.user_id == user_id
            ).values(
                status=status,
                completed_at=datetime.utcnow() if status == "completed" else None,
                updated_at=datetime.utcnow()
            )
            
            result = await session.execute(stmt)
            
            if result.rowcount > 0:
                self.logger.info("Task status updated", user_id=user_id, task_id=task_id, status=status)
                return True
            
            return False
    
    async def delete_task(self, user_id: int, task_id: int) -> bool:
        """Delete a task (mark as cancelled)."""
        return await self.update_task_status(user_id, task_id, "cancelled")
    
    async def edit_task(
        self,
        user_id: int,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Edit an existing task."""
        async with db_manager.get_session() as session:
            updates = {"updated_at": datetime.utcnow()}
            
            if title is not None:
                updates["title"] = title[:500]
            if description is not None:
                updates["description"] = description
            if priority is not None:
                updates["priority"] = priority
            if due_date is not None:
                updates["due_date"] = due_date
            if tags is not None:
                updates["tags"] = ",".join(tags) if tags else None
            
            stmt = update(TodoTask).where(
                TodoTask.id == task_id,
                TodoTask.user_id == user_id
            ).values(**updates)
            
            result = await session.execute(stmt)
            
            if result.rowcount > 0:
                self.logger.info("Task edited", user_id=user_id, task_id=task_id)
                return True
            
            return False
    
    async def get_task_stats(self, user_id: int) -> Dict[str, Any]:
        """Get task statistics for a user."""
        async with db_manager.get_session() as session:
            # Count tasks by status
            stmt = select(
                TodoTask.status,
                func.count(TodoTask.id)
            ).where(
                TodoTask.user_id == user_id,
                TodoTask.status != "cancelled"
            ).group_by(TodoTask.status)
            
            result = await session.execute(stmt)
            status_counts = dict(result.all())
            
            # Count overdue tasks
            stmt = select(func.count(TodoTask.id)).where(
                TodoTask.user_id == user_id,
                TodoTask.status.in_(["pending", "in_progress"]),
                TodoTask.due_date < datetime.utcnow()
            )
            result = await session.execute(stmt)
            overdue_count = result.scalar() or 0
            
            # Count today's tasks
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            stmt = select(func.count(TodoTask.id)).where(
                TodoTask.user_id == user_id,
                TodoTask.status.in_(["pending", "in_progress"]),
                TodoTask.due_date >= today_start,
                TodoTask.due_date < today_end
            )
            result = await session.execute(stmt)
            today_count = result.scalar() or 0
            
            return {
                "total_tasks": sum(status_counts.values()),
                "pending": status_counts.get("pending", 0),
                "in_progress": status_counts.get("in_progress", 0),
                "completed": status_counts.get("completed", 0),
                "overdue": overdue_count,
                "due_today": today_count
            }


# Global todo service instance
todo_service = TodoService()