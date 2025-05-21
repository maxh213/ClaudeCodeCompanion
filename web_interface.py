"""
Web interface for managing Claude Agent workflow.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory

from logger import ClaudeAgentLogger
import config
from utils import read_file, write_file, get_next_task

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_claude_agent')

# Global state
SESSIONS = {}
CURRENT_SESSION_ID = None
LOGGER = None

def init_session(repo_path, todo_file='TODO.md', session_id=None):
    """Initialize a new session."""
    global CURRENT_SESSION_ID, LOGGER
    
    if session_id and session_id in SESSIONS:
        # Resume existing session
        CURRENT_SESSION_ID = session_id
        LOGGER = ClaudeAgentLogger(session_id=session_id)
        return SESSIONS[session_id]
    
    # Create new session
    session_id = session_id or f"{int(datetime.now().timestamp())}"
    CURRENT_SESSION_ID = session_id
    
    # Create logger
    LOGGER = ClaudeAgentLogger(session_id=session_id)
    
    repo_path = Path(repo_path).absolute()
    todo_path = repo_path / todo_file
    
    # Initialize session state
    SESSIONS[session_id] = {
        "session_id": session_id,
        "repo_path": str(repo_path),
        "todo_file": todo_file,
        "todo_path": str(todo_path),
        "completed_tasks": [],
        "current_task": None,
        "task_count": 0,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    return SESSIONS[session_id]

def get_task_status(session_id=None):
    """Get status of tasks in the TODO file."""
    if not session_id and not CURRENT_SESSION_ID:
        return None
    
    session_id = session_id or CURRENT_SESSION_ID
    session = SESSIONS.get(session_id)
    
    if not session:
        return None
    
    try:
        todo_content = read_file(session['todo_path'])
        
        # Parse tasks
        pending_tasks = []
        review_tasks = []
        completed_tasks = []
        
        for line in todo_content.split('\n'):
            if '[ ]' in line:
                pending_tasks.append(line.strip())
            elif '[R]' in line:
                review_tasks.append(line.strip())
            elif '[x]' in line or '[X]' in line:
                completed_tasks.append(line.strip())
        
        return {
            'pending': pending_tasks,
            'review': review_tasks,
            'completed': completed_tasks
        }
    except Exception as e:
        if LOGGER:
            LOGGER.log_error(f"Error getting task status: {e}")
        return None

def get_session_logs(session_id=None):
    """Get logs for a session."""
    session_id = session_id or CURRENT_SESSION_ID
    
    if not session_id:
        return []
    
    log_dir = Path("./logs") / session_id
    interaction_log = log_dir / "interactions.jsonl"
    
    if not interaction_log.exists():
        return []
    
    try:
        logs = []
        with open(interaction_log, 'r') as f:
            for line in f:
                logs.append(json.loads(line))
        return logs
    except Exception as e:
        if LOGGER:
            LOGGER.log_error(f"Error getting session logs: {e}")
        return []

# Routes
@app.route('/')
def index():
    """Home page showing available sessions and option to create new session."""
    global SESSIONS
    
    # Load existing sessions from log directories
    logs_dir = Path("./logs")
    if logs_dir.exists():
        for session_dir in logs_dir.iterdir():
            if session_dir.is_dir() and session_dir.name not in SESSIONS:
                # Try to load session info
                session_file = session_dir / "session_info.json"
                if session_file.exists():
                    try:
                        with open(session_file, 'r') as f:
                            session_info = json.load(f)
                            SESSIONS[session_dir.name] = session_info
                    except:
                        # If we can't load the info, create a basic entry
                        SESSIONS[session_dir.name] = {
                            "session_id": session_dir.name,
                            "created_at": datetime.fromtimestamp(int(session_dir.name.split('_')[0])).isoformat() 
                                if '_' in session_dir.name and session_dir.name.split('_')[0].isdigit() 
                                else "Unknown",
                            "status": "unknown"
                        }
    
    return render_template('index.html', 
                          sessions=SESSIONS, 
                          current_session=CURRENT_SESSION_ID)

@app.route('/session/new', methods=['GET', 'POST'])
def new_session():
    """Create a new session."""
    if request.method == 'POST':
        repo_path = request.form.get('repo_path', '.')
        todo_file = request.form.get('todo_file', 'TODO.md')
        
        session = init_session(repo_path, todo_file)
        
        # Save session info to log directory
        log_dir = Path("./logs") / session['session_id']
        log_dir.mkdir(exist_ok=True)
        
        try:
            with open(log_dir / "session_info.json", 'w') as f:
                json.dump(session, f, indent=2)
        except Exception as e:
            if LOGGER:
                LOGGER.log_error(f"Error saving session info: {e}")
        
        return redirect(url_for('session', session_id=session['session_id']))
    
    return render_template('new_session.html')

@app.route('/session/<session_id>')
def session(session_id):
    """View a session."""
    global CURRENT_SESSION_ID
    
    if session_id not in SESSIONS:
        # Try to load from logs
        log_dir = Path("./logs") / session_id
        session_file = log_dir / "session_info.json"
        
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    SESSIONS[session_id] = json.load(f)
            except:
                return redirect(url_for('index'))
        else:
            return redirect(url_for('index'))
    
    CURRENT_SESSION_ID = session_id
    
    # Get task status
    task_status = get_task_status(session_id)
    
    # Get logs
    logs = get_session_logs(session_id)
    
    return render_template('session.html', 
                          session=SESSIONS[session_id],
                          task_status=task_status,
                          logs=logs)

@app.route('/session/<session_id>/tasks')
def tasks(session_id):
    """View and manage tasks for a session."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    task_status = get_task_status(session_id)
    
    return render_template('tasks.html',
                          session=SESSIONS[session_id],
                          task_status=task_status)

@app.route('/session/<session_id>/prompt', methods=['GET', 'POST'])
def prompt(session_id):
    """Generate and show prompt for Claude."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    
    if request.method == 'POST':
        task_type = request.form.get('task_type', 'new')
        task = request.form.get('task')
        
        try:
            todo_content = read_file(session['todo_path'])
            
            if task_type == 'new':
                # Start a new task
                if task:
                    # Use specified task
                    next_task = task
                else:
                    # Get next task from TODO file
                    next_task, _ = get_next_task(todo_content)
                
                if not next_task:
                    return render_template('prompt.html',
                                          session=session,
                                          error="No task found or specified.")
                
                session['current_task'] = next_task
                session['task_count'] += 1
                
                # Generate prompt for task
                from utils import format_prompt_for_task
                prompt = format_prompt_for_task(next_task)
                
                if LOGGER:
                    LOGGER.log_task_start(next_task)
                    LOGGER.log_claude_prompt(prompt, next_task)
                
                return render_template('prompt.html',
                                      session=session,
                                      prompt=prompt,
                                      task=next_task,
                                      task_type='new')
            
            elif task_type == 'review':
                # Review a task
                if not task and not session.get('current_task'):
                    return render_template('prompt.html',
                                          session=session,
                                          error="No task specified for review.")
                
                review_task = task or session.get('current_task')
                
                # Generate prompt for review
                from utils import format_prompt_for_review
                prompt = format_prompt_for_review(review_task)
                
                if LOGGER:
                    LOGGER.log_task_start(review_task, is_review=True)
                    LOGGER.log_claude_prompt(prompt, review_task, is_review=True)
                
                return render_template('prompt.html',
                                      session=session,
                                      prompt=prompt,
                                      task=review_task,
                                      task_type='review')
        
        except Exception as e:
            if LOGGER:
                LOGGER.log_error(f"Error generating prompt: {e}")
            return render_template('prompt.html',
                                  session=session,
                                  error=f"Error: {e}")
    
    # Show form to generate prompt
    task_status = get_task_status(session_id)
    
    return render_template('prompt_form.html',
                          session=session,
                          task_status=task_status)

@app.route('/session/<session_id>/response', methods=['POST'])
def submit_response(session_id):
    """Submit Claude's response and take appropriate action."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    task = request.form.get('task')
    task_type = request.form.get('task_type', 'new')
    response = request.form.get('response', '')
    
    if LOGGER:
        LOGGER.log_claude_response(response, task, is_review=(task_type == 'review'))
    
    if task_type == 'review':
        # Mark task as completed
        if LOGGER:
            LOGGER.log_task_end(task, is_review=True)
        
        if 'current_task' in session and session['current_task'] == task:
            session['completed_tasks'].append(task)
            session['current_task'] = None
    else:
        # Mark task for review
        if LOGGER:
            LOGGER.log_task_end(task)
    
    # Save updated session
    try:
        log_dir = Path("./logs") / session_id
        with open(log_dir / "session_info.json", 'w') as f:
            json.dump(session, f, indent=2)
    except Exception as e:
        if LOGGER:
            LOGGER.log_error(f"Error saving session info: {e}")
    
    # Clear context
    if LOGGER:
        LOGGER.log_context_clear()
    
    return redirect(url_for('session', session_id=session_id))

@app.route('/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """End a session."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    SESSIONS[session_id]['status'] = 'completed'
    
    # Log session end
    if LOGGER:
        LOGGER.log_session_end(SESSIONS[session_id].get('completed_tasks', []))
    
    # Save updated session
    try:
        log_dir = Path("./logs") / session_id
        with open(log_dir / "session_info.json", 'w') as f:
            json.dump(SESSIONS[session_id], f, indent=2)
    except Exception as e:
        if LOGGER:
            LOGGER.log_error(f"Error saving session info: {e}")
    
    return redirect(url_for('index'))

@app.route('/logs/<path:filename>')
def download_log(filename):
    """Download a log file."""
    return send_from_directory('logs', filename)

if __name__ == '__main__':
    # Create templates and static dirs if they don't exist
    templates_dir = Path('./templates')
    templates_dir.mkdir(exist_ok=True)
    
    static_dir = Path('./static')
    static_dir.mkdir(exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)