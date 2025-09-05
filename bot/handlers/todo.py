"""Todo list and task management handlers."""

import re
from datetime import datetime, timedelta
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.todo_service import todo_service
from ..decorators.auth import auth_check

logger = get_logger(__name__)


def parse_due_date(date_str: str) -> Optional[datetime]:
    """Parse due date from various formats."""
    if not date_str:
        return None
    
    date_str = date_str.lower().strip()
    now = datetime.utcnow()
    
    # Handle relative dates
    if date_str in ["today", "tod"]:
        return now.replace(hour=23, minute=59, second=59, microsecond=0)
    elif date_str in ["tomorrow", "tmr"]:
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
    elif date_str.endswith("d"):
        try:
            days = int(date_str[:-1])
            return (now + timedelta(days=days)).replace(hour=23, minute=59, second=59, microsecond=0)
        except ValueError:
            pass
    elif date_str.endswith("h"):
        try:
            hours = int(date_str[:-1])
            return now + timedelta(hours=hours)
        except ValueError:
            pass
    
    # Handle specific date formats (YYYY-MM-DD, DD/MM, MM/DD)
    date_patterns = [
        r"(\d{4})-(\d{1,2})-(\d{1,2})",  # YYYY-MM-DD
        r"(\d{1,2})/(\d{1,2})/(\d{4})",  # MM/DD/YYYY
        r"(\d{1,2})/(\d{1,2})",          # MM/DD (current year)
        r"(\d{1,2})-(\d{1,2})",          # MM-DD (current year)
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # MM/DD/YYYY
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                else:  # MM/DD or MM-DD (current year)
                    month, day = int(groups[0]), int(groups[1])
                    year = now.year
                
                return datetime(year, month, day, 23, 59, 59)
            except (ValueError, TypeError):
                continue
    
    return None


def parse_priority(text: str) -> str:
    """Extract priority from task text."""
    if "!!!" in text or "urgent" in text.lower():
        return "urgent"
    elif "!!" in text or "high" in text.lower():
        return "high"
    elif "!" in text or "low" in text.lower():
        return "low"
    return "medium"


def parse_tags(text: str) -> List[str]:
    """Extract tags from task text (words starting with #)."""
    return re.findall(r"#(\w+)", text)


@auth_check
async def list_todos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List user's todo tasks."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        # Parse arguments for filtering
        status_filter = None
        if context.args:
            arg = context.args[0].lower()
            if arg in ["pending", "completed", "progress", "in_progress"]:
                status_filter = "in_progress" if arg == "progress" else arg
        
        # Get tasks
        tasks = await todo_service.get_tasks(user_id, status=status_filter, limit=15)
        stats = await todo_service.get_task_stats(user_id)
        
        if not tasks:
            message = (
                f"📋 **Your Todo List**\n\n"
                f"No tasks found"
            )
            if status_filter:
                message += f" with status '{status_filter}'"
            message += ".\n\nUse `/add_todo <task>` to add your first task!"
        else:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄", 
                "completed": "✅"
            }
            
            priority_emoji = {
                "urgent": "🔴",
                "high": "🟠",
                "medium": "🟡", 
                "low": "🟢"
            }
            
            message = f"📋 **Your Todo List**\n\n"
            
            for i, task in enumerate(tasks[:10], 1):
                status = status_emoji.get(task["status"], "📝")
                priority = priority_emoji.get(task["priority"], "🟡")
                
                due_str = ""
                if task["due_date"]:
                    due_date = task["due_date"]
                    if due_date.date() == datetime.utcnow().date():
                        due_str = " 📅Today"
                    elif due_date < datetime.utcnow():
                        due_str = " ⚠️Overdue"
                    else:
                        days_left = (due_date.date() - datetime.utcnow().date()).days
                        if days_left == 1:
                            due_str = " 📅Tomorrow"
                        elif days_left <= 7:
                            due_str = f" 📅{days_left}d"
                
                tags_str = ""
                if task["tags"]:
                    tags_str = " " + " ".join(f"#{tag}" for tag in task["tags"][:3])
                
                title = task["title"][:60] + "..." if len(task["title"]) > 60 else task["title"]
                message += f"{status}{priority} `{task['id']}` {title}{due_str}{tags_str}\n"
            
            if len(tasks) > 10:
                message += f"\n... and {len(tasks) - 10} more tasks\n"
        
        # Add stats
        message += (
            f"\n📊 **Stats:** {stats['pending']} pending, {stats['in_progress']} in progress, "
            f"{stats['completed']} completed"
        )
        
        if stats['overdue'] > 0:
            message += f", {stats['overdue']} overdue"
        if stats['due_today'] > 0:
            message += f", {stats['due_today']} due today"
        
        # Create action keyboard
        keyboard = [
            [
                InlineKeyboardButton("⏳ Pending", callback_data="todo_filter_pending"),
                InlineKeyboardButton("🔄 In Progress", callback_data="todo_filter_in_progress"),
            ],
            [
                InlineKeyboardButton("✅ Completed", callback_data="todo_filter_completed"),
                InlineKeyboardButton("📊 Stats", callback_data="todo_stats"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error("Error listing todos", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading your todo list."
        )


@auth_check
async def add_todo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new todo task."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "📝 **Add Todo Task**\n\n"
            "Usage: `/add_todo <task description>`\n\n"
            "**Advanced options:**\n"
            "• Add priority: `!` (low), `!!` (high), `!!!` (urgent)\n"
            "• Add due date: `due:today`, `due:tomorrow`, `due:3d`, `due:2024-12-25`\n"
            "• Add tags: `#work #important`\n\n"
            "**Examples:**\n"
            "`/add_todo Buy groceries due:today #personal`\n"
            "`/add_todo !! Finish project report due:tomorrow #work`\n"
            "`/add_todo !!! Fix critical bug due:2h #urgent`",
            parse_mode="Markdown"
        )
        return
    
    task_text = " ".join(context.args)
    
    try:
        # Parse due date
        due_date = None
        due_match = re.search(r"due:(\S+)", task_text)
        if due_match:
            due_date = parse_due_date(due_match.group(1))
            task_text = re.sub(r"due:\S+", "", task_text).strip()
        
        # Parse priority
        priority = parse_priority(task_text)
        # Clean priority markers from text
        task_text = re.sub(r"!+", "", task_text).strip()
        task_text = re.sub(r"\b(urgent|high|low)\b", "", task_text, flags=re.IGNORECASE).strip()
        
        # Parse tags
        tags = parse_tags(task_text)
        # Clean tags from main text
        task_text = re.sub(r"#\w+", "", task_text).strip()
        
        if not task_text:
            await update.message.reply_text("❌ Please provide a task description.")
            return
        
        # Add the task
        task = await todo_service.add_task(
            user_id=user_id,
            title=task_text,
            priority=priority,
            due_date=due_date,
            tags=tags
        )
        
        # Format response
        priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        due_str = ""
        if due_date:
            if due_date.date() == datetime.utcnow().date():
                due_str = "\n📅 Due: Today"
            elif due_date < datetime.utcnow():
                due_str = "\n⚠️ Due: Overdue!"
            else:
                due_str = f"\n📅 Due: {due_date.strftime('%Y-%m-%d')}"
        
        tags_str = ""
        if tags:
            tags_str = f"\n🏷️ Tags: {' '.join(f'#{tag}' for tag in tags)}"
        
        message = (
            f"✅ **Task Added!**\n\n"
            f"{priority_emoji[priority]} `{task['id']}` {task['title']}{due_str}{tags_str}\n\n"
            f"Use `/list_todos` to see all your tasks."
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
        logger.info("Todo added", user_id=user_id, task_id=task["id"], priority=priority)
        
    except Exception as e:
        logger.error("Error adding todo", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while adding your task. Please try again."
        )


@auth_check
async def complete_todo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a todo task as completed."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "✅ **Complete Task**\n\n"
            "Usage: `/complete_todo <task_id>`\n\n"
            "Use `/list_todos` to see task IDs."
        )
        return
    
    try:
        task_id = int(context.args[0])
        
        success = await todo_service.update_task_status(user_id, task_id, "completed")
        
        if success:
            await update.message.reply_text(
                f"✅ Task `{task_id}` marked as completed!\n\n"
                f"Use `/list_todos completed` to see completed tasks.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Task `{task_id}` not found or doesn't belong to you.",
                parse_mode="Markdown"
            )
        
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task ID (number).")
    except Exception as e:
        logger.error("Error completing todo", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while completing the task."
        )


@auth_check
async def remove_todo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a todo task."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🗑️ **Remove Task**\n\n"
            "Usage: `/remove_todo <task_id>`\n\n"
            "Use `/list_todos` to see task IDs."
        )
        return
    
    try:
        task_id = int(context.args[0])
        
        success = await todo_service.delete_task(user_id, task_id)
        
        if success:
            await update.message.reply_text(
                f"🗑️ Task `{task_id}` removed successfully!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Task `{task_id}` not found or doesn't belong to you.",
                parse_mode="Markdown"
            )
        
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task ID (number).")
    except Exception as e:
        logger.error("Error removing todo", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while removing the task."
        )


@auth_check
async def todo_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show todo statistics."""
    
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    try:
        stats = await todo_service.get_task_stats(user_id)
        
        # Calculate completion rate
        total_completed = stats["completed"]
        total_all = stats["total_tasks"] + total_completed
        completion_rate = (total_completed / total_all * 100) if total_all > 0 else 0
        
        # Progress bar for completion
        bar_length = 15
        filled_length = int(bar_length * completion_rate // 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        message = (
            f"📊 **Your Todo Statistics**\n\n"
            f"📋 **Total Tasks:** {stats['total_tasks']}\n"
            f"⏳ **Pending:** {stats['pending']}\n"
            f"🔄 **In Progress:** {stats['in_progress']}\n"
            f"✅ **Completed:** {stats['completed']}\n\n"
            f"📅 **Due Today:** {stats['due_today']}\n"
            f"⚠️ **Overdue:** {stats['overdue']}\n\n"
            f"🎯 **Completion Rate**\n"
            f"{bar} {completion_rate:.1f}%\n\n"
            f"💡 **Tip:** Stay organized by setting due dates and priorities!"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error showing todo stats", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while loading statistics."
        )


async def handle_todo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle todo-related callback queries."""
    
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        if callback_data.startswith("todo_filter_"):
            status = callback_data.replace("todo_filter_", "")
            
            # Get filtered tasks
            tasks = await todo_service.get_tasks(user_id, status=status, limit=15)
            
            if not tasks:
                await query.edit_message_text(
                    f"📋 No {status} tasks found.\n\n"
                    f"Use `/add_todo <task>` to add a new task!",
                    parse_mode="Markdown"
                )
                return
            
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄", 
                "completed": "✅"
            }
            
            message = f"📋 **{status.title()} Tasks**\n\n"
            
            for i, task in enumerate(tasks[:10], 1):
                emoji = status_emoji.get(task["status"], "📝")
                title = task["title"][:50] + "..." if len(task["title"]) > 50 else task["title"]
                message += f"{emoji} `{task['id']}` {title}\n"
            
            if len(tasks) > 10:
                message += f"\n... and {len(tasks) - 10} more tasks"
            
            await query.edit_message_text(message, parse_mode="Markdown")
        
        elif callback_data == "todo_stats":
            stats = await todo_service.get_task_stats(user_id)
            
            total_completed = stats["completed"]
            total_all = stats["total_tasks"] + total_completed
            completion_rate = (total_completed / total_all * 100) if total_all > 0 else 0
            
            message = (
                f"📊 **Todo Statistics**\n\n"
                f"📋 Total: {stats['total_tasks']}\n"
                f"⏳ Pending: {stats['pending']}\n"
                f"🔄 In Progress: {stats['in_progress']}\n"
                f"✅ Completed: {stats['completed']}\n"
                f"📅 Due Today: {stats['due_today']}\n"
                f"⚠️ Overdue: {stats['overdue']}\n\n"
                f"🎯 Completion: {completion_rate:.1f}%"
            )
            
            await query.edit_message_text(message, parse_mode="Markdown")
        
        else:
            await query.answer("❓ Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error("Error handling todo callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)