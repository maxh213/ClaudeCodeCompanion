#!/usr/bin/env python3
"""
Claude Agent - Automated workflow for Claude to complete tasks from a TODO list.
"""

import os
import sys
import argparse
import logging
import json
import time
from pathlib import Path
import subprocess
from config import DEFAULT_CONFIG
from utils import (
    setup_logging,
    read_file,
    write_file,
    run_git_command,
    create_branch,
    create_pr,
    commit_changes,
    get_next_task,
    format_prompt_for_task,
    format_prompt_for_review
)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Automated Claude Task Workflow")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to config file (JSON)"
    )
    parser.add_argument(
        "--repo-path", 
        type=str, 
        help="Path to repository"
    )
    parser.add_argument(
        "--todo-file", 
        type=str, 
        default="TODO.md", 
        help="Path to TODO.md file"
    )
    parser.add_argument(
        "--branch-prefix", 
        type=str, 
        default="claude-session-", 
        help="Prefix for branch names"
    )
    parser.add_argument(
        "--pr-title", 
        type=str, 
        default="Claude Session Changes", 
        help="Title for the pull request"
    )
    parser.add_argument(
        "--pr-base", 
        type=str, 
        default="main", 
        help="Base branch for the pull request"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
        default="INFO", 
        help="Logging level"
    )
    parser.add_argument(
        "--max-tasks", 
        type=int, 
        default=0, 
        help="Maximum number of tasks to complete (0 for unlimited)"
    )
    parser.add_argument(
        "--session-id", 
        type=str, 
        help="Resume an existing session using this ID"
    )
    return parser.parse_args()

def load_config(args):
    """Load configuration from file or use defaults with command line overrides."""
    config = DEFAULT_CONFIG.copy()
    
    # If config file specified, load it
    if args.config:
        try:
            with open(args.config, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
            sys.exit(1)
    
    # Override with command line arguments if provided
    for key, value in vars(args).items():
        if value is not None and key in config:
            config[key] = value
    
    return config

def load_session_state(session_id):
    """Load existing session state from file."""
    session_file = Path(f".claude_session_{session_id}.json")
    if session_file.exists():
        try:
            with open(session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading session state: {e}")
            return None
    return None

def save_session_state(session_state):
    """Save current session state to file."""
    session_file = Path(f".claude_session_{session_state['session_id']}.json")
    try:
        with open(session_file, 'w') as f:
            json.dump(session_state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving session state: {e}")

def initialize_session(config):
    """Initialize a new session or resume an existing one."""
    if config["session_id"]:
        # Try to resume existing session
        session_state = load_session_state(config["session_id"])
        if session_state:
            logging.info(f"Resuming session {config['session_id']}")
            return session_state
        else:
            logging.warning(f"Could not find session {config['session_id']}, starting new session")
    
    # Create new session
    session_id = f"{int(time.time())}"
    branch_name = f"{config['branch_prefix']}{session_id}"
    
    # Create a new branch
    create_branch(config['repo_path'], branch_name, config['pr_base'])
    
    # Create the PR
    pr_url = create_pr(
        config['repo_path'], 
        branch_name, 
        config['pr_base'], 
        config['pr_title'], 
        f"Automated claude session {session_id}"
    )
    
    session_state = {
        "session_id": session_id,
        "branch_name": branch_name,
        "pr_url": pr_url,
        "completed_tasks": [],
        "current_task": None,
        "task_count": 0
    }
    
    save_session_state(session_state)
    logging.info(f"Started new session {session_id} on branch {branch_name}")
    return session_state

def run_claude_interaction(config, session_state, is_review=False):
    """Run a single Claude interaction for a task or review."""
    repo_path = Path(config['repo_path'])
    todo_path = repo_path / config['todo_file']
    
    # Read project files
    try:
        todo_content = read_file(todo_path)
        readme_content = read_file(repo_path / "README.md") if (repo_path / "README.md").exists() else ""
        projectbrief_content = read_file(repo_path / "projectbrief.md") if (repo_path / "projectbrief.md").exists() else ""
        testing_summary_content = read_file(repo_path / "testing_summary.md") if (repo_path / "testing_summary.md").exists() else ""
        claude_md_content = read_file(repo_path / "CLAUDE.md") if (repo_path / "CLAUDE.md").exists() else ""
    except Exception as e:
        logging.error(f"Error reading project files: {e}")
        return False
    
    if is_review and session_state['current_task']:
        # We're reviewing the previous task
        prompt = format_prompt_for_review(
            session_state['current_task'],
            todo_content,
            readme_content,
            projectbrief_content,
            testing_summary_content,
            claude_md_content
        )
        logging.info(f"Reviewing task: {session_state['current_task']}")
    else:
        # We're starting a new task
        next_task = get_next_task(todo_content)
        if not next_task:
            logging.info("No more tasks found in TODO.md")
            return False
        
        session_state['current_task'] = next_task
        session_state['task_count'] += 1
        save_session_state(session_state)
        
        prompt = format_prompt_for_task(
            next_task,
            todo_content,
            readme_content,
            projectbrief_content,
            testing_summary_content,
            claude_md_content
        )
        logging.info(f"Starting task: {next_task}")
    
    # Print the prompt for the user to give to Claude
    print("\n" + "="*80)
    print("CLAUDE PROMPT:")
    print("="*80)
    print(prompt)
    print("="*80 + "\n")
    
    # Wait for user to confirm task completion
    input("Press Enter once Claude has completed the task and you're ready to continue...")
    
    # Commit the changes
    if not is_review:
        commit_message = f"Mark task for review: {session_state['current_task']}"
    else:
        commit_message = f"Complete task: {session_state['current_task']}"
        session_state['completed_tasks'].append(session_state['current_task'])
        session_state['current_task'] = None
    
    try:
        commit_changes(config['repo_path'], commit_message)
        logging.info(f"Committed changes: {commit_message}")
        save_session_state(session_state)
        return True
    except Exception as e:
        logging.error(f"Error committing changes: {e}")
        return False

def main():
    """Main entry point for the Claude Agent script."""
    args = parse_arguments()
    setup_logging(args.log_level)
    
    config = load_config(args)
    session_state = initialize_session(config)
    
    # Main loop for processing tasks
    try:
        max_tasks = config["max_tasks"]
        task_complete = True  # Start with task complete (not in review)
        
        while max_tasks == 0 or session_state["task_count"] < max_tasks:
            # If previous task is complete, start a new task; otherwise, review previous task
            if task_complete:
                task_complete = run_claude_interaction(config, session_state, is_review=False)
            else:
                # This is a review step
                run_claude_interaction(config, session_state, is_review=True)
                task_complete = True  # After review, mark as complete and move to next task
            
            # Clear context message
            print("\n" + "="*80)
            print("CONTEXT CLEARED!")
            print("Claude's context has been cleared. Start a new interaction for the next task.")
            print("="*80 + "\n")
            
            # Ask if user wants to continue
            response = input("Continue to next task? (y/n): ").strip().lower()
            if response != 'y':
                logging.info("Session ended by user")
                break
    
    except KeyboardInterrupt:
        logging.info("Session interrupted by user")
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
    
    print(f"\nSession {session_state['session_id']} completed.")
    print(f"Branch: {session_state['branch_name']}")
    print(f"PR URL: {session_state['pr_url']}")
    print(f"Completed tasks: {len(session_state['completed_tasks'])}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
