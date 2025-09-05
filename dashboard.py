"""Web dashboard for Telegram bot monitoring and management."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify, request
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)

# Database path
DB_PATH = Path(__file__).parent / "bot.db"

def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_bot_stats() -> Dict[str, Any]:
    """Get basic bot statistics."""
    conn = get_db_connection()
    
    try:
        # Get total users
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        # Get active users (last 24h) - using created_at as proxy
        yesterday = datetime.now() - timedelta(days=1)
        active_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at > ?", 
            (yesterday.isoformat(),)
        ).fetchone()[0]
        
        # Get total images generated
        total_images = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
        
        # Get total todos
        total_todos = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
        completed_todos = conn.execute(
            "SELECT COUNT(*) FROM todos WHERE completed = 1"
        ).fetchone()[0]
        
        # Get crypto bets
        total_bets = conn.execute("SELECT COUNT(*) FROM crypto_bets").fetchone()[0]
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_images": total_images,
            "total_todos": total_todos,
            "completed_todos": completed_todos,
            "total_bets": total_bets,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    finally:
        conn.close()

def get_recent_activity() -> List[Dict[str, Any]]:
    """Get recent activity from the bot."""
    conn = get_db_connection()
    
    try:
        activities = []
        
        # Recent images
        recent_images = conn.execute("""
            SELECT u.username, i.prompt, i.created_at, 'image' as type
            FROM images i
            JOIN users u ON i.user_id = u.id
            ORDER BY i.created_at DESC
            LIMIT 5
        """).fetchall()
        
        for img in recent_images:
            activities.append({
                "type": "image",
                "user": img["username"] or "Anonymous",
                "description": f"Generated image: {img['prompt'][:50]}...",
                "timestamp": img["created_at"]
            })
        
        # Recent todos
        recent_todos = conn.execute("""
            SELECT u.username, t.task, t.created_at, 'todo' as type
            FROM todos t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
            LIMIT 5
        """).fetchall()
        
        for todo in recent_todos:
            activities.append({
                "type": "todo",
                "user": todo["username"] or "Anonymous",
                "description": f"Added todo: {todo['task'][:50]}...",
                "timestamp": todo["created_at"]
            })
        
        # Sort by timestamp and return latest
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:10]
    
    finally:
        conn.close()

@app.route("/")
def dashboard():
    """Main dashboard page."""
    return render_template("dashboard.html")

@app.route("/api/stats")
def api_stats():
    """API endpoint for bot statistics."""
    return jsonify(get_bot_stats())

@app.route("/api/activity")
def api_activity():
    """API endpoint for recent activity."""
    return jsonify(get_recent_activity())

@app.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    
    app.run(host="0.0.0.0", port=8080, debug=False)