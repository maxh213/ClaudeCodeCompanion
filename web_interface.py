"""
Web interface for managing Claude Agent workflow.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, flash, session as flask_session

from logger import ClaudeAgentLogger
from conversation_tracker import ConversationTracker
from ollama_client import OllamaClient
import config
from utils import read_file, write_file, get_next_task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_claude_agent')

# Global state
SESSIONS = {}
CURRENT_SESSION_ID = None
LOGGER = None
CONVERSATION_TRACKER = None
OLLAMA_CLIENT = None

# Default settings
APP_SETTINGS = {
    "ollama_enabled": False,
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "ollama_temperature": 0.7,
    "logs_retention": 30
}

def load_settings():
    """Load application settings from file."""
    settings_file = Path("./settings.json")
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                APP_SETTINGS.update(settings)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    # Initialize Ollama client if enabled
    global OLLAMA_CLIENT
    if APP_SETTINGS["ollama_enabled"]:
        try:
            OLLAMA_CLIENT = OllamaClient(
                base_url=APP_SETTINGS["ollama_base_url"],
                model=APP_SETTINGS["ollama_model"]
            )
            if not OLLAMA_CLIENT.check_connection():
                logger.warning("Could not connect to Ollama server. Disabling Ollama integration.")
                APP_SETTINGS["ollama_enabled"] = False
                OLLAMA_CLIENT = None
        except Exception as e:
            logger.error(f"Error initializing Ollama client: {e}")
            APP_SETTINGS["ollama_enabled"] = False
            OLLAMA_CLIENT = None

def save_settings():
    """Save application settings to file."""
    settings_file = Path("./settings.json")
    try:
        with open(settings_file, 'w') as f:
            json.dump(APP_SETTINGS, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def init_session(repo_path, todo_file='TODO.md', session_id=None):
    """Initialize a new session."""
    global CURRENT_SESSION_ID, LOGGER, CONVERSATION_TRACKER
    
    if session_id and session_id in SESSIONS:
        # Resume existing session
        CURRENT_SESSION_ID = session_id
        LOGGER = ClaudeAgentLogger(session_id=session_id)
        CONVERSATION_TRACKER = ConversationTracker(session_id=session_id)
        return SESSIONS[session_id]
    
    # Create new session
    session_id = session_id or f"{int(datetime.now().timestamp())}"
    CURRENT_SESSION_ID = session_id
    
    # Create logger and conversation tracker
    LOGGER = ClaudeAgentLogger(session_id=session_id)
    CONVERSATION_TRACKER = ConversationTracker(session_id=session_id)
    
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

def process_with_ollama(prompt, task, task_type, session_id):
    """Process a task with Ollama."""
    if not OLLAMA_CLIENT:
        return None
    
    session = SESSIONS.get(session_id)
    if not session:
        return None
    
    # Get TODO content
    todo_content = None
    try:
        todo_content = read_file(session['todo_path'])
    except Exception as e:
        logger.error(f"Error reading TODO file: {e}")
    
    # Get repo info
    repo_info = f"Repository path: {session['repo_path']}\nTODO file: {session['todo_file']}"
    
    # Process with Ollama
    result = OLLAMA_CLIENT.process_claude_task(
        prompt=prompt,
        todo_content=todo_content,
        repo_info=repo_info,
        model=APP_SETTINGS.get("ollama_model"),
        temperature=float(APP_SETTINGS.get("ollama_temperature", 0.7))
    )
    
    if not result.get("success"):
        logger.error(f"Error processing with Ollama: {result.get('error')}")
        return None
    
    # Start new conversation if needed
    if CONVERSATION_TRACKER:
        if not CONVERSATION_TRACKER.current_conversation_id:
            CONVERSATION_TRACKER.start_conversation(task=task, task_type="review" if task_type == "review" else "implementation")
        
        # Add prompt to conversation
        CONVERSATION_TRACKER.add_message(
            role="user",
            content=prompt,
            metadata={
                "format": "text",
                "task": task,
                "task_type": task_type
            }
        )
        
        # Add Ollama response to conversation
        CONVERSATION_TRACKER.add_message(
            role="assistant",
            content=result.get("text", ""),
            metadata={
                "format": "text",
                "model": result.get("model"),
                "task": task,
                "task_type": task_type
            }
        )
    
    return result.get("text", "")

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
                          current_session=CURRENT_SESSION_ID,
                          ollama_enabled=APP_SETTINGS.get("ollama_enabled", False))

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
                          logs=logs,
                          ollama_enabled=APP_SETTINGS.get("ollama_enabled", False))

@app.route('/session/<session_id>/tasks')
def tasks(session_id):
    """View and manage tasks for a session."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    task_status = get_task_status(session_id)
    
    return render_template('tasks.html',
                          session=SESSIONS[session_id],
                          task_status=task_status)

@app.route('/session/<session_id>/todo')
def todo_preview(session_id):
    """Preview the TODO.md file."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    todo_path = session.get('todo_path')
    
    todo_content = None
    last_updated = None
    
    try:
        todo_file = Path(todo_path)
        if todo_file.exists():
            todo_content = read_file(todo_path)
            last_updated = datetime.fromtimestamp(todo_file.stat().st_mtime).isoformat().replace('T', ' ')[:19]
    except Exception as e:
        if LOGGER:
            LOGGER.log_error(f"Error reading TODO file: {e}")
    
    task_status = get_task_status(session_id)
    
    return render_template('todo_preview.html',
                          session=session,
                          todo_content=todo_content,
                          todo_path=todo_path,
                          last_updated=last_updated,
                          task_status=task_status)

@app.route('/session/<session_id>/todo/edit', methods=['GET', 'POST'])
def edit_todo(session_id):
    """Edit the TODO.md file."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    todo_path = session.get('todo_path')
    
    if request.method == 'POST':
        todo_content = request.form.get('content', '')
        
        try:
            write_file(todo_path, todo_content)
            flash('TODO.md updated successfully', 'success')
            
            if LOGGER:
                LOGGER.log_file_change(todo_path, 'modify', todo_content)
            
            return redirect(url_for('todo_preview', session_id=session_id))
        except Exception as e:
            if LOGGER:
                LOGGER.log_error(f"Error writing TODO file: {e}")
            flash(f'Error updating TODO.md: {e}', 'danger')
    
    # GET request - load the file for editing
    todo_content = None
    
    try:
        todo_content = read_file(todo_path)
    except Exception as e:
        if LOGGER:
            LOGGER.log_error(f"Error reading TODO file: {e}")
        flash(f'Error reading TODO.md: {e}', 'danger')
    
    return render_template('todo_edit.html',
                          session=session,
                          todo_content=todo_content,
                          todo_path=todo_path)

@app.route('/session/<session_id>/todo/create', methods=['GET', 'POST'])
def create_todo(session_id):
    """Create a new TODO.md file."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    todo_path = session.get('todo_path')
    
    if request.method == 'POST':
        todo_content = request.form.get('content', '')
        
        try:
            write_file(todo_path, todo_content)
            flash('TODO.md created successfully', 'success')
            
            if LOGGER:
                LOGGER.log_file_change(todo_path, 'create', todo_content)
            
            return redirect(url_for('todo_preview', session_id=session_id))
        except Exception as e:
            if LOGGER:
                LOGGER.log_error(f"Error creating TODO file: {e}")
            flash(f'Error creating TODO.md: {e}', 'danger')
    
    # Default template for new TODO file
    default_content = """# Project TODO List

## Tasks
- [ ] Task 1: Description of first task
- [ ] Task 2: Description of second task

## Completed
"""
    
    return render_template('todo_create.html',
                          session=session,
                          todo_content=default_content,
                          todo_path=todo_path)

@app.route('/session/<session_id>/conversations')
def conversations(session_id):
    """View conversations for a session."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    global CONVERSATION_TRACKER
    if CONVERSATION_TRACKER is None or CONVERSATION_TRACKER.session_id != session_id:
        CONVERSATION_TRACKER = ConversationTracker(session_id=session_id)
    
    conversations = CONVERSATION_TRACKER.list_conversations()
    
    return render_template('conversation.html',
                          session=SESSIONS[session_id],
                          conversations=conversations)

@app.route('/session/<session_id>/conversations/<conversation_id>')
def view_conversation(session_id, conversation_id):
    """View a specific conversation."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    global CONVERSATION_TRACKER
    if CONVERSATION_TRACKER is None or CONVERSATION_TRACKER.session_id != session_id:
        CONVERSATION_TRACKER = ConversationTracker(session_id=session_id)
    
    conversation = CONVERSATION_TRACKER.get_conversation(conversation_id)
    conversations = CONVERSATION_TRACKER.list_conversations()
    
    if not conversation:
        flash('Conversation not found', 'danger')
        return redirect(url_for('conversations', session_id=session_id))
    
    return render_template('conversation.html',
                          session=SESSIONS[session_id],
                          conversation=conversation,
                          conversations=conversations)

@app.route('/session/<session_id>/conversations/<conversation_id>/message', methods=['POST'])
def add_conversation_message(session_id, conversation_id):
    """Add a message to a conversation."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    global CONVERSATION_TRACKER
    if CONVERSATION_TRACKER is None or CONVERSATION_TRACKER.session_id != session_id:
        CONVERSATION_TRACKER = ConversationTracker(session_id=session_id)
    
    conversation = CONVERSATION_TRACKER.get_conversation(conversation_id)
    
    if not conversation:
        flash('Conversation not found', 'danger')
        return redirect(url_for('conversations', session_id=session_id))
    
    if conversation.get('status') != 'active':
        flash('Cannot add messages to a completed conversation', 'warning')
        return redirect(url_for('view_conversation', session_id=session_id, conversation_id=conversation_id))
    
    role = request.form.get('role', 'user')
    content = request.form.get('content', '')
    format = request.form.get('format', 'text')
    
    CONVERSATION_TRACKER.current_conversation_id = conversation_id
    CONVERSATION_TRACKER.add_message(
        role=role,
        content=content,
        metadata={'format': format}
    )
    
    return redirect(url_for('view_conversation', session_id=session_id, conversation_id=conversation_id))

@app.route('/session/<session_id>/conversations/<conversation_id>/end', methods=['POST'])
def end_conversation(session_id, conversation_id):
    """End a conversation."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    global CONVERSATION_TRACKER
    if CONVERSATION_TRACKER is None or CONVERSATION_TRACKER.session_id != session_id:
        CONVERSATION_TRACKER = ConversationTracker(session_id=session_id)
    
    conversation = CONVERSATION_TRACKER.get_conversation(conversation_id)
    
    if not conversation:
        flash('Conversation not found', 'danger')
        return redirect(url_for('conversations', session_id=session_id))
    
    status = request.form.get('status', 'completed')
    
    CONVERSATION_TRACKER.current_conversation_id = conversation_id
    CONVERSATION_TRACKER.end_conversation(status=status)
    
    flash(f'Conversation marked as {status}', 'success')
    return redirect(url_for('view_conversation', session_id=session_id, conversation_id=conversation_id))

@app.route('/session/<session_id>/prompt', methods=['GET', 'POST'])
def prompt(session_id):
    """Generate and show prompt for Claude."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    
    if request.method == 'POST':
        task_type = request.form.get('task_type', 'new')
        task = request.form.get('task')
        use_ollama = APP_SETTINGS.get("ollama_enabled", False) and request.form.get('use_ollama') == 'on'
        
        try:
            todo_content = read_file(session['todo_path'])
            
            if task_type == 'new':
                # Start a new task
                if task:
                    # Use specified task
                    next_task = task
                else:
                    # Get next task from TODO file
                    next_task_data = get_next_task(todo_content)
                    next_task = next_task_data[0] if next_task_data else None
                
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
                
                # Start new conversation
                if CONVERSATION_TRACKER:
                    CONVERSATION_TRACKER.start_conversation(task=next_task, task_type="implementation")
                    CONVERSATION_TRACKER.add_message(
                        role="user",
                        content=prompt,
                        metadata={"task": next_task, "format": "text"}
                    )
                
                # Process with Ollama if enabled
                ollama_response = None
                if use_ollama and OLLAMA_CLIENT:
                    ollama_response = process_with_ollama(prompt, next_task, task_type, session_id)
                
                return render_template('prompt.html',
                                      session=session,
                                      prompt=prompt,
                                      task=next_task,
                                      task_type='new',
                                      ollama_enabled=APP_SETTINGS.get("ollama_enabled", False),
                                      ollama_response=ollama_response,
                                      conversation_id=CONVERSATION_TRACKER.current_conversation_id if CONVERSATION_TRACKER else None)
            
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
                
                # Start new conversation
                if CONVERSATION_TRACKER:
                    CONVERSATION_TRACKER.start_conversation(task=review_task, task_type="review")
                    CONVERSATION_TRACKER.add_message(
                        role="user",
                        content=prompt,
                        metadata={"task": review_task, "format": "text"}
                    )
                
                # Process with Ollama if enabled
                ollama_response = None
                if use_ollama and OLLAMA_CLIENT:
                    ollama_response = process_with_ollama(prompt, review_task, task_type, session_id)
                
                return render_template('prompt.html',
                                      session=session,
                                      prompt=prompt,
                                      task=review_task,
                                      task_type='review',
                                      ollama_enabled=APP_SETTINGS.get("ollama_enabled", False),
                                      ollama_response=ollama_response,
                                      conversation_id=CONVERSATION_TRACKER.current_conversation_id if CONVERSATION_TRACKER else None)
        
        except Exception as e:
            if LOGGER:
                LOGGER.log_error(f"Error generating prompt: {e}")
            return render_template('prompt.html',
                                  session=session,
                                  error=f"Error: {e}")
    
    # Show form to generate prompt
    task_status = get_task_status(session_id)
    
    # Check for task in query parameters
    task = request.args.get('task')
    task_type = request.args.get('task_type', 'new')
    
    return render_template('prompt_form.html',
                          session=session,
                          task_status=task_status,
                          selected_task=task,
                          selected_task_type=task_type,
                          ollama_enabled=APP_SETTINGS.get("ollama_enabled", False))

@app.route('/session/<session_id>/response', methods=['POST'])
def submit_response(session_id):
    """Submit Claude's response and take appropriate action."""
    if session_id not in SESSIONS:
        return redirect(url_for('index'))
    
    session = SESSIONS[session_id]
    task = request.form.get('task')
    task_type = request.form.get('task_type', 'new')
    response = request.form.get('response', '')
    conversation_id = request.form.get('conversation_id')
    
    if LOGGER:
        LOGGER.log_claude_response(response, task, is_review=(task_type == 'review'))
    
    # Add response to conversation if conversation ID is provided
    if conversation_id and CONVERSATION_TRACKER:
        CONVERSATION_TRACKER.current_conversation_id = conversation_id
        CONVERSATION_TRACKER.add_message(
            role="assistant",
            content=response,
            metadata={"task": task, "format": "text"}
        )
    
    if task_type == 'review':
        # Mark task as completed
        if LOGGER:
            LOGGER.log_task_end(task, is_review=True)
        
        if 'current_task' in session and session['current_task'] == task:
            session['completed_tasks'].append(task)
            session['current_task'] = None
            
        # End conversation if active
        if conversation_id and CONVERSATION_TRACKER:
            CONVERSATION_TRACKER.end_conversation(status='completed')
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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Application settings."""
    if request.method == 'POST':
        # Update settings from form
        APP_SETTINGS["ollama_enabled"] = 'ollama_enabled' in request.form
        APP_SETTINGS["ollama_base_url"] = request.form.get('ollama_base_url', 'http://localhost:11434')
        APP_SETTINGS["ollama_model"] = request.form.get('ollama_model', 'llama3')
        APP_SETTINGS["ollama_temperature"] = float(request.form.get('ollama_temperature', 0.7))
        APP_SETTINGS["logs_retention"] = int(request.form.get('logs_retention', 30))
        
        # Save settings
        if save_settings():
            flash('Settings saved successfully', 'success')
            
            # Reinitialize Ollama client if enabled
            global OLLAMA_CLIENT
            if APP_SETTINGS["ollama_enabled"]:
                try:
                    OLLAMA_CLIENT = OllamaClient(
                        base_url=APP_SETTINGS["ollama_base_url"],
                        model=APP_SETTINGS["ollama_model"]
                    )
                    if not OLLAMA_CLIENT.check_connection():
                        flash('Could not connect to Ollama server. Disabling Ollama integration.', 'warning')
                        APP_SETTINGS["ollama_enabled"] = False
                        OLLAMA_CLIENT = None
                        save_settings()
                except Exception as e:
                    flash(f'Error initializing Ollama client: {e}', 'danger')
                    APP_SETTINGS["ollama_enabled"] = False
                    OLLAMA_CLIENT = None
                    save_settings()
            else:
                OLLAMA_CLIENT = None
        else:
            flash('Error saving settings', 'danger')
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html', settings=APP_SETTINGS)

@app.route('/test_ollama', methods=['POST'])
def test_ollama():
    """Test connection to Ollama server."""
    data = request.json
    base_url = data.get('base_url', 'http://localhost:11434')
    model = data.get('model', 'llama3')
    
    try:
        client = OllamaClient(base_url=base_url, model=model)
        if client.check_connection():
            models = client.list_models()
            return jsonify({
                "success": True,
                "models": models or ["No models found"]
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not connect to Ollama server"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# App initialization
def init_app():
    """Initialize the application."""
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Load settings
    load_settings()

if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=True)