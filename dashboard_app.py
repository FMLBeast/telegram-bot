#!/usr/bin/env python3
"""
Comprehensive Telegram Bot Dashboard
Features: Status monitoring, log viewing, controls, GitHub rollback
"""

import subprocess
import json
import os
import time
from datetime import datetime
from threading import Thread
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'telegram-bot-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
BOT_SERVICE_NAME = 'telegram-bot'
BOT_DIRECTORY = '/opt/telegram-bot'
GITHUB_API_URL = 'https://api.github.com/repos/FMLBeast/telegram-bot'

class BotManager:
    def __init__(self):
        self.log_thread = None
        self.log_running = False

    def get_status(self):
        """Get comprehensive bot status"""
        try:
            # Get systemd status
            result = subprocess.run(['systemctl', 'status', BOT_SERVICE_NAME], 
                                 capture_output=True, text=True)
            
            # Parse status
            status = {
                'active': 'active (running)' in result.stdout,
                'enabled': 'enabled' in result.stdout,
                'uptime': self._parse_uptime(result.stdout),
                'memory_usage': self._parse_memory(result.stdout),
                'cpu_usage': self._parse_cpu(result.stdout),
                'restart_count': self._parse_restart_count(result.stdout),
                'last_log': self._get_last_log_line()
            }
            
            # Get Git info
            status.update(self._get_git_info())
            
            return status
        except Exception as e:
            return {'error': str(e), 'active': False}

    def _parse_uptime(self, output):
        """Extract uptime from systemctl output"""
        lines = output.split('\n')
        for line in lines:
            if 'Active:' in line and 'since' in line:
                try:
                    since_part = line.split('since ')[1].split(';')[0].strip()
                    start_time = datetime.strptime(since_part, '%a %Y-%m-%d %H:%M:%S %Z')
                    uptime = datetime.now() - start_time
                    return str(uptime).split('.')[0]  # Remove microseconds
                except:
                    pass
        return 'Unknown'

    def _parse_memory(self, output):
        """Extract memory usage from systemctl output"""
        lines = output.split('\n')
        for line in lines:
            if 'Memory:' in line:
                return line.split('Memory: ')[1].split(' ')[0]
        return 'Unknown'

    def _parse_cpu(self, output):
        """Extract CPU time from systemctl output"""
        lines = output.split('\n')
        for line in lines:
            if 'CPU:' in line:
                return line.split('CPU: ')[1].split(' ')[0]
        return 'Unknown'

    def _parse_restart_count(self, output):
        """Extract restart count from systemctl output"""
        lines = output.split('\n')
        for line in lines:
            if 'restart counter is at' in line:
                try:
                    return line.split('restart counter is at ')[1].split('.')[0]
                except:
                    pass
        return '0'

    def _get_last_log_line(self):
        """Get the most recent log line"""
        try:
            result = subprocess.run(['/usr/bin/journalctl', '-u', BOT_SERVICE_NAME, '-n', '1', '--no-pager'], 
                                 capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if lines and len(lines) > 0:
                return lines[-1]
        except:
            pass
        return 'No logs available'

    def _get_git_info(self):
        """Get current Git commit info"""
        try:
            os.chdir(BOT_DIRECTORY)
            
            # Get current commit hash
            result = subprocess.run(['/usr/bin/git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
            commit_hash = result.stdout.strip()[:8]
            
            # Get current branch
            result = subprocess.run(['/usr/bin/git', 'branch', '--show-current'], capture_output=True, text=True)
            branch = result.stdout.strip()
            
            # Get last commit message
            result = subprocess.run(['/usr/bin/git', 'log', '-1', '--pretty=format:%s'], capture_output=True, text=True)
            last_commit_msg = result.stdout.strip()
            
            # Get last commit date
            result = subprocess.run(['/usr/bin/git', 'log', '-1', '--pretty=format:%ci'], capture_output=True, text=True)
            last_commit_date = result.stdout.strip()
            
            return {
                'commit_hash': commit_hash,
                'branch': branch,
                'last_commit_msg': last_commit_msg,
                'last_commit_date': last_commit_date
            }
        except Exception as e:
            return {'git_error': str(e)}

    def start_bot(self):
        """Start the bot service"""
        try:
            result = subprocess.run(['systemctl', 'start', BOT_SERVICE_NAME], 
                                 capture_output=True, text=True)
            return result.returncode == 0, result.stderr if result.returncode != 0 else "Bot started successfully"
        except Exception as e:
            return False, str(e)

    def stop_bot(self):
        """Stop the bot service"""
        try:
            result = subprocess.run(['systemctl', 'stop', BOT_SERVICE_NAME], 
                                 capture_output=True, text=True)
            return result.returncode == 0, result.stderr if result.returncode != 0 else "Bot stopped successfully"
        except Exception as e:
            return False, str(e)

    def restart_bot(self):
        """Restart the bot service"""
        try:
            result = subprocess.run(['systemctl', 'restart', BOT_SERVICE_NAME], 
                                 capture_output=True, text=True)
            return result.returncode == 0, result.stderr if result.returncode != 0 else "Bot restarted successfully"
        except Exception as e:
            return False, str(e)

    def get_github_releases(self):
        """Get recent GitHub releases/commits"""
        try:
            # Get recent commits
            response = requests.get(f"{GITHUB_API_URL}/commits", timeout=10)
            if response.status_code == 200:
                commits = response.json()[:10]  # Get last 10 commits
                return [
                    {
                        'sha': commit['sha'][:8],
                        'full_sha': commit['sha'],
                        'message': commit['commit']['message'].split('\n')[0][:100],
                        'author': commit['commit']['author']['name'],
                        'date': commit['commit']['author']['date'],
                        'url': commit['html_url']
                    }
                    for commit in commits
                ]
        except Exception as e:
            return [{'error': str(e)}]
        return []

    def rollback_to_commit(self, commit_sha):
        """Rollback to a specific commit"""
        try:
            os.chdir(BOT_DIRECTORY)
            
            # Stop the bot first
            subprocess.run(['/usr/bin/systemctl', 'stop', BOT_SERVICE_NAME], check=True)
            
            # Fetch latest changes
            subprocess.run(['/usr/bin/git', 'fetch', 'origin'], check=True)
            
            # Reset to the specific commit
            subprocess.run(['/usr/bin/git', 'reset', '--hard', commit_sha], check=True)
            
            # Install requirements
            subprocess.run(['/opt/telegram-bot/venv/bin/pip', 'install', '-r', 'requirements.txt'], check=True)
            
            # Start the bot
            subprocess.run(['/usr/bin/systemctl', 'start', BOT_SERVICE_NAME], check=True)
            
            return True, f"Successfully rolled back to commit {commit_sha[:8]}"
        except Exception as e:
            # Try to start the bot again if rollback failed
            try:
                subprocess.run(['/usr/bin/systemctl', 'start', BOT_SERVICE_NAME])
            except:
                pass
            return False, f"Rollback failed: {str(e)}"

    def start_log_streaming(self):
        """Start streaming logs via WebSocket"""
        if self.log_running:
            return
        
        self.log_running = True
        self.log_thread = Thread(target=self._stream_logs)
        self.log_thread.daemon = True
        self.log_thread.start()

    def stop_log_streaming(self):
        """Stop streaming logs"""
        self.log_running = False

    def _stream_logs(self):
        """Stream logs to WebSocket clients"""
        try:
            # First send some initial recent logs
            try:
                result = subprocess.run(['/usr/bin/journalctl', '-u', BOT_SERVICE_NAME, '-n', '20', '--no-pager'], 
                                     capture_output=True, text=True, timeout=5)
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            socketio.emit('log_line', {'line': f'[RECENT] {line.strip()}'})
                            time.sleep(0.05)
            except Exception as e:
                socketio.emit('log_line', {'line': f'Error getting recent logs: {str(e)}'})
            
            # Then start following new logs
            socketio.emit('log_line', {'line': '--- Following live logs ---'})
            
            proc = subprocess.Popen(
                ['/usr/bin/journalctl', '-u', BOT_SERVICE_NAME, '-f', '--no-pager'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            while self.log_running and proc.poll() is None:
                line = proc.stdout.readline()
                if line:
                    socketio.emit('log_line', {'line': line.strip()})
                time.sleep(0.1)
                    
        except Exception as e:
            socketio.emit('log_line', {'line': f'Log streaming error: {str(e)}'})

bot_manager = BotManager()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    return jsonify(bot_manager.get_status())

@app.route('/api/control', methods=['POST'])
def api_control():
    """API endpoint for bot control"""
    action = request.json.get('action')
    
    if action == 'start':
        success, message = bot_manager.start_bot()
    elif action == 'stop':
        success, message = bot_manager.stop_bot()
    elif action == 'restart':
        success, message = bot_manager.restart_bot()
    else:
        return jsonify({'success': False, 'message': 'Invalid action'})
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/releases')
def api_releases():
    """API endpoint for GitHub releases"""
    return jsonify(bot_manager.get_github_releases())

@app.route('/api/rollback', methods=['POST'])
def api_rollback():
    """API endpoint for rollback"""
    commit_sha = request.json.get('commit_sha')
    if not commit_sha:
        return jsonify({'success': False, 'message': 'Commit SHA required'})
    
    success, message = bot_manager.rollback_to_commit(commit_sha)
    return jsonify({'success': success, 'message': message})

@socketio.on('connect')
def on_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to bot dashboard'})
    bot_manager.start_log_streaming()

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection"""
    # Note: This only stops when all clients disconnect
    # For simplicity, we'll keep the log streaming running
    pass

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=9000, debug=False)