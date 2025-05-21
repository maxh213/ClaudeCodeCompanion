"""
Logging system for Claude Agent to track all changes and interactions.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

class ClaudeAgentLogger:
    """Logger for tracking Claude Agent interactions and changes."""
    
    def __init__(self, log_dir=None, session_id=None):
        """Initialize the logger.
        
        Args:
            log_dir (str): Directory to store logs. Defaults to './logs'.
            session_id (str): Session ID to use for log files.
        """
        self.log_dir = Path(log_dir) if log_dir else Path("./logs")
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.log_dir / self.session_id
        self.setup_log_directory()
        
        # Set up file and console logging
        self.setup_logging()
        
        # Initialize interaction log
        self.interaction_log_path = self.session_dir / "interactions.jsonl"
        self.task_log_path = self.session_dir / "tasks.jsonl"
        self.changes_log_path = self.session_dir / "changes.jsonl"
        
        # Log session start
        self.log_session_start()
    
    def setup_log_directory(self):
        """Create log directory structure."""
        try:
            self.log_dir.mkdir(exist_ok=True)
            self.session_dir.mkdir(exist_ok=True)
        except Exception as e:
            print(f"Error creating log directories: {e}")
    
    def setup_logging(self):
        """Set up Python logging."""
        self.logger = logging.getLogger(f"claude_agent_{self.session_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = self.session_dir / "debug.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatters and add to handlers
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_session_start(self):
        """Log session start information."""
        self.logger.info(f"Started new Claude Agent session: {self.session_id}")
        
        # Write session start to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "session_start",
                "session_id": self.session_id
            }
        )
    
    def log_session_end(self, completed_tasks=None):
        """Log session end information.
        
        Args:
            completed_tasks (list): List of completed tasks.
        """
        if completed_tasks is None:
            completed_tasks = []
        
        self.logger.info(f"Ended Claude Agent session: {self.session_id}")
        self.logger.info(f"Completed {len(completed_tasks)} tasks")
        
        # Write session end to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "session_end",
                "session_id": self.session_id,
                "completed_tasks_count": len(completed_tasks),
                "completed_tasks": completed_tasks
            }
        )
    
    def log_task_start(self, task, is_review=False):
        """Log task start information.
        
        Args:
            task (str): The task being started.
            is_review (bool): Whether this is a review task.
        """
        task_type = "review" if is_review else "implementation"
        self.logger.info(f"Started {task_type} task: {task}")
        
        # Write task start to task log
        self._append_to_jsonl(
            self.task_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": f"task_{task_type}_start",
                "task": task
            }
        )
        
        # Write to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "task_start",
                "task": task,
                "task_type": task_type
            }
        )
    
    def log_task_end(self, task, is_review=False, success=True):
        """Log task end information.
        
        Args:
            task (str): The task being ended.
            is_review (bool): Whether this is a review task.
            success (bool): Whether the task was completed successfully.
        """
        task_type = "review" if is_review else "implementation"
        status = "completed" if success else "failed"
        self.logger.info(f"{status.capitalize()} {task_type} task: {task}")
        
        # Write task end to task log
        self._append_to_jsonl(
            self.task_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": f"task_{task_type}_end",
                "task": task,
                "status": status
            }
        )
        
        # Write to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "task_end",
                "task": task,
                "task_type": task_type,
                "status": status
            }
        )
    
    def log_claude_prompt(self, prompt, task=None, is_review=False):
        """Log a prompt sent to Claude.
        
        Args:
            prompt (str): The prompt sent to Claude.
            task (str): The related task.
            is_review (bool): Whether this is a review task.
        """
        task_type = "review" if is_review else "implementation"
        self.logger.debug(f"Sent prompt to Claude for {task_type} task: {task}")
        
        # Write to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "claude_prompt",
                "task": task,
                "task_type": task_type,
                "prompt": prompt
            }
        )
    
    def log_claude_response(self, response, task=None, is_review=False):
        """Log a response from Claude.
        
        Args:
            response (str): The response from Claude.
            task (str): The related task.
            is_review (bool): Whether this is a review task.
        """
        task_type = "review" if is_review else "implementation"
        self.logger.debug(f"Received response from Claude for {task_type} task: {task}")
        
        # Write to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "claude_response",
                "task": task,
                "task_type": task_type,
                "response_summary": response[:100] + "..." if len(response) > 100 else response
            }
        )
        
        # Save full response to a separate file
        response_dir = self.session_dir / "responses"
        response_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = response_dir / f"{timestamp}_{task_type}_{self._sanitize_filename(task)}.txt"
        
        try:
            with open(response_file, 'w') as f:
                f.write(response)
        except Exception as e:
            self.logger.error(f"Error saving Claude response: {e}")
    
    def log_file_change(self, file_path, change_type, content=None):
        """Log a file change.
        
        Args:
            file_path (str): Path to the file that was changed.
            change_type (str): Type of change (create, modify, delete).
            content (str): New content of the file (for create/modify).
        """
        self.logger.info(f"{change_type.capitalize()} file: {file_path}")
        
        # Write to changes log
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "file_change",
            "file_path": str(file_path),
            "change_type": change_type
        }
        
        if change_type in ["create", "modify"] and content:
            # Save content to a separate file
            changes_dir = self.session_dir / "changes"
            changes_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self._sanitize_filename(str(file_path))
            content_file = changes_dir / f"{timestamp}_{change_type}_{filename}.txt"
            
            try:
                with open(content_file, 'w') as f:
                    f.write(content)
                entry["content_file"] = str(content_file)
            except Exception as e:
                self.logger.error(f"Error saving file content: {e}")
        
        self._append_to_jsonl(self.changes_log_path, entry)
    
    def log_todo_change(self, old_content, new_content, task=None):
        """Log a change to the TODO.md file.
        
        Args:
            old_content (str): Previous content of TODO.md.
            new_content (str): New content of TODO.md.
            task (str): The related task.
        """
        self.logger.info(f"TODO.md updated for task: {task}")
        
        # Write to changes log
        self._append_to_jsonl(
            self.changes_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "todo_change",
                "task": task,
                "old_content": old_content,
                "new_content": new_content
            }
        )
    
    def log_context_clear(self):
        """Log that Claude's context was cleared."""
        self.logger.info("Claude's context cleared")
        
        # Write to interaction log
        self._append_to_jsonl(
            self.interaction_log_path,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "context_clear"
            }
        )
    
    def log_error(self, error_message, context=None):
        """Log an error.
        
        Args:
            error_message (str): Error message.
            context (dict): Additional context for the error.
        """
        self.logger.error(f"Error: {error_message}")
        
        # Write to interaction log
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_message": error_message
        }
        
        if context:
            entry["context"] = context
        
        self._append_to_jsonl(self.interaction_log_path, entry)
    
    def _append_to_jsonl(self, file_path, data):
        """Append a JSON object to a JSONL file.
        
        Args:
            file_path (Path): Path to the JSONL file.
            data (dict): Data to append.
        """
        try:
            with open(file_path, 'a') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            self.logger.error(f"Error writing to log file {file_path}: {e}")
    
    def _sanitize_filename(self, filename):
        """Sanitize a filename to be safe for the filesystem.
        
        Args:
            filename (str): Original filename.
            
        Returns:
            str: Sanitized filename.
        """
        # Replace slashes with underscores
        sanitized = filename.replace('/', '_').replace('\\', '_')
        
        # Remove any other unsafe characters
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c in '._- ')
        
        # Truncate if too long
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized