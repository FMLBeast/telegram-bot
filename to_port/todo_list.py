import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db_conn

logger = logging.getLogger(__name__)

def init_todo_table():
    """Initialize the todo table in the database."""
    with db_conn.get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

# Initialize table when module is imported
init_todo_table()

async def list_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all todos for the current channel."""
    chat_id = update.effective_chat.id
    
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM todos WHERE channel_id = ? ORDER BY priority DESC',
                (chat_id,)
            )
            todos = cursor.fetchall()
            
        if not todos:
            await update.message.reply_text("No todos found for this channel.")
            return
        
        # Create keyboard for each todo
        keyboard = []
        for todo in todos:
            status = "✅" if todo['completed'] else "⏳"
            text = f"{status} {todo['description']}"
            if todo['remarks']:
                text += f"\n📝 {todo['remarks']}"
            
            # Add priority controls
            row = [
                InlineKeyboardButton("⬆️", callback_data=f"edit_up_{todo['id']}"),
                InlineKeyboardButton("⬇️", callback_data=f"edit_down_{todo['id']}"),
                InlineKeyboardButton("✅", callback_data=f"edit_complete_{todo['id']}")
            ]
            keyboard.append(row)
            keyboard.append([InlineKeyboardButton(text, callback_data=f"edit_view_{todo['id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Current todos:", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error listing todos: {e}")
        await update.message.reply_text("An error occurred while listing todos.")

async def move_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle priority changes for todos."""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("edit_"):
        return
    
    action, direction, todo_id = query.data.split("_")
    todo_id = int(todo_id)
    
    try:
        with db_conn.get_connection() as conn:
            if direction == "up":
                conn.execute(
                    'UPDATE todos SET priority = priority + 1 WHERE id = ?',
                    (todo_id,)
                )
            elif direction == "down":
                conn.execute(
                    'UPDATE todos SET priority = priority - 1 WHERE id = ?',
                    (todo_id,)
                )
            elif direction == "complete":
                conn.execute(
                    'UPDATE todos SET completed = NOT completed WHERE id = ?',
                    (todo_id,)
                )
        
        # Refresh the todo list
        await list_todos(update, context)
        
    except Exception as e:
        logger.error(f"Error updating todo priority: {e}")
        await query.message.reply_text("An error occurred while updating the todo.")

async def add_remark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a remark to a todo item."""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "Please provide todo ID and remark text: /remark <todo_id> <remark>"
            )
            return
        
        todo_id = int(args[0])
        remark_text = " ".join(args[1:])
        
        with db_conn.get_connection() as conn:
            conn.execute(
                'UPDATE todos SET remarks = ? WHERE id = ?',
                (remark_text, todo_id)
            )
        
        await update.message.reply_text("Remark added successfully!")
        await list_todos(update, context)
        
    except ValueError:
        await update.message.reply_text("Invalid todo ID. Please provide a number.")
    except Exception as e:
        logger.error(f"Error adding remark: {e}")
        await update.message.reply_text("An error occurred while adding the remark.")

async def add_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new todo item."""
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text("Please provide a description for the todo.")
        return
    
    description = " ".join(context.args)
    
    try:
        with db_conn.get_connection() as conn:
            conn.execute(
                'INSERT INTO todos (channel_id, description) VALUES (?, ?)',
                (chat_id, description)
            )
        
        await update.message.reply_text("Todo added successfully!")
        await list_todos(update, context)
        
    except Exception as e:
        logger.error(f"Error adding todo: {e}")
        await update.message.reply_text("An error occurred while adding the todo.")