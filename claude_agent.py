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
    format_prompt_for_review,
    format_prompt_for_empty_todo,
    format_prompt_for_all_completed
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

def get_session_dir():
    """Get the directory for storing session files."""
    # Always store session files in the current directory where the script is run
    # This avoids polluting the target repo
    session_dir = Path(".")
    return session_dir

def load_session_state(session_id):
    """Load existing session state from file."""
    session_dir = get_session_dir()
    session_file = session_dir / f".claude_session_{session_id}.json"
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
    session_dir = get_session_dir()
    session_file = session_dir / f".claude_session_{session_state['session_id']}.json"
    try:
        with open(session_file, 'w') as f:
            json.dump(session_state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving session state: {e}")

def initialize_session(config):
    """Initialize a new session or resume an existing one."""
    # Make sure the repo path exists
    repo_path = Path(config['repo_path'])
    if not repo_path.exists():
        logging.error(f"Repository path does not exist: {repo_path}")
        raise ValueError(f"Repository path does not exist: {repo_path}")
    
    # Store session files in the workspace directory to avoid polluting the target repo
    workspace_dir = Path(".")
    
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
    
    # We don't create branches or PRs - Claude will be instructed to do this
    session_state = {
        "session_id": session_id,
        "completed_tasks": [],
        "current_task": None,
        "task_count": 0,
        "repo_path": str(repo_path.absolute())
    }
    
    save_session_state(session_state)
    logging.info(f"Started new session {session_id}")
    return session_state

def run_claude_api(prompt, repo_path, api_key=None):
    """Run a Claude API request using Claude Code CLI tool."""
    import subprocess
    import tempfile
    import os
    import json
    
    print(f"\n[Claude Agent] Working on task in {repo_path}...")
    
    # First, check if Claude Code is installed
    try:
        # Check if claude command is available
        result = subprocess.run(['claude', '--version'], 
                             capture_output=True, 
                             text=True, 
                             check=False)
        
        if result.returncode == 0:
            claude_code_available = True
            print("[Claude Agent] Claude Code detected. Using Claude Code CLI...")
        else:
            claude_code_available = False
            print("[Claude Agent] Claude Code not found. Falling back to manual mode...")
    except FileNotFoundError:
        claude_code_available = False
        print("[Claude Agent] Claude Code not installed. Falling back to manual mode...")
    
    # Use Claude Code if available
    if claude_code_available:
        try:
            # Save prompt to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(prompt)
            
            # Run Claude Code in print mode with json output format for automation
            print("[Claude Agent] Running Claude Code CLI...")
            cmd = ['claude', '-p', '--output-format', 'json', '--max-turns', '5']
            
            # Add the prompt (reading from file to handle large prompts better)
            with open(temp_file_path, 'r') as f:
                prompt_text = f.read()
            
            # Run Claude Code with the prompt
            proc = subprocess.run(
                cmd,
                input=prompt_text,
                capture_output=True,
                text=True,
                cwd=repo_path
            )
            
            if proc.returncode == 0:
                try:
                    # Parse the JSON output
                    output = json.loads(proc.stdout)
                    response = output.get('result', '')
                    
                    print("[Claude Agent] Claude Code execution successful")
                    print(f"[Claude Agent] Response length: {len(response)} characters")
                    
                    # Save the response for reference
                    response_file = Path(repo_path) / "claude_response.txt"
                    with open(response_file, 'w') as f:
                        f.write(response)
                    print(f"[Claude Agent] Saved Claude's response to {response_file}")
                    
                    return response
                except json.JSONDecodeError:
                    print("[Claude Agent] Error parsing Claude Code output as JSON")
                    print("[Claude Agent] Falling back to raw output...")
                    response = proc.stdout
                    return response
            else:
                print(f"[Claude Agent] Claude Code execution failed with exit code {proc.returncode}")
                print(f"[Claude Agent] Error: {proc.stderr}")
                print("[Claude Agent] Falling back to manual mode...")
        except Exception as e:
            print(f"[Claude Agent] Error running Claude Code: {str(e)}")
            print("[Claude Agent] Falling back to manual mode...")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    # If we have API key, try using Anthropic package 
    if api_key and not claude_code_available:
        try:
            print("[Claude Agent] Trying to use Anthropic API...")
            
            # Import dynamically only if needed
            import anthropic
            
            # The newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            client = anthropic.Anthropic(api_key=api_key)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.2,
                system="You are an expert programmer assisting with coding tasks. Follow instructions precisely.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            
            print("[Claude Agent] Successfully received response from Claude API")
            print(f"[Claude Agent] Response length: {len(response)} characters")
            
            return response
            
        except Exception as e:
            print(f"[Claude Agent] Error using Anthropic API: {str(e)}")
            print("[Claude Agent] Falling back to manual mode...")
    
    # Manual fallback mode if all else fails
    # Save the prompt to a file for convenience
    prompt_file = Path(repo_path) / "claude_prompt.txt"
    try:
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        print(f"[Claude Agent] Saved prompt to {prompt_file}")
    except Exception as e:
        print(f"[Claude Agent] Warning: Could not save prompt to file: {e}")
    
    print("\n" + "="*80)
    print("PROMPT FOR CLAUDE:")
    print("="*80)
    print(prompt)
    print("="*80 + "\n")
    
    print("[Claude Agent] Please use Claude Code or copy this prompt to Claude.")
    print("[Claude Agent] Then paste Claude's response below.")
    print("[Claude Agent] Type 'DONE' on a new line when finished.")
    
    # Collect user input until they indicate they're done
    lines = []
    while True:
        line = input()
        if line.strip() == "DONE":
            break
        lines.append(line)
    
    response = "\n".join(lines)
    
    # Save the response for reference
    try:
        response_file = Path(repo_path) / "claude_response.txt"
        with open(response_file, 'w') as f:
            f.write(response)
        print(f"[Claude Agent] Saved Claude's response to {response_file}")
    except Exception as e:
        print(f"[Claude Agent] Warning: Could not save response to file: {e}")
    
    return response

def run_claude_interaction(config, session_state, is_review=False):
    """Run a single Claude interaction for a task or review."""
    repo_path = Path(config['repo_path'])
    todo_path = repo_path / config['todo_file']
    
    # Read project files
    try:
        todo_content = read_file(todo_path)
    except Exception as e:
        logging.error(f"Error reading TODO file: {e}")
        return False
    
    if is_review and session_state['current_task']:
        # We're reviewing the previous task
        prompt = format_prompt_for_review(
            session_state['current_task']
        )
        logging.info(f"Reviewing task: {session_state['current_task']}")
        task_type = "review"
    else:
        # We're starting a new task
        next_task, task_type = get_next_task(todo_content)
        
        if task_type == "empty":
            # No tasks found in TODO.md
            prompt = format_prompt_for_empty_todo()
            logging.info("No tasks found in TODO.md")
        elif task_type == "completed":
            # All tasks are completed
            prompt = format_prompt_for_all_completed()
            logging.info("All tasks completed in TODO.md")
            # End the session automatically when all tasks are completed
            session_state['all_completed'] = True
            save_session_state(session_state)
            return True
        elif task_type == "review" or task_type == "task":
            # Regular task found
            session_state['current_task'] = next_task
            session_state['task_count'] += 1
            save_session_state(session_state)
            
            prompt = format_prompt_for_task(next_task)
            logging.info(f"Starting task: {next_task}")
        else:
            logging.error(f"Unknown task type: {task_type}")
            return False
    
    # Run the Claude interaction
    print(f"\n[Claude Agent] Processing {'review' if is_review else 'task'}...")
    
    # Check for API key
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("[Claude Agent] No CLAUDE_API_KEY found in environment variables.")
        print("[Claude Agent] Using manual interaction mode.")
    
    # Call Claude API (or manual fallback)
    claude_response = run_claude_api(prompt, repo_path, api_key)
    
    # Handle different task types
    if task_type == "empty" or task_type == "completed":
        # No need to commit anything for empty or completed task lists
        return True
    
    # Commit the changes for regular tasks
    if not is_review:
        commit_message = f"Mark task for review: {session_state['current_task']}"
    else:
        commit_message = f"Complete task: {session_state['current_task']}"
        session_state['completed_tasks'].append(session_state['current_task'])
        session_state['current_task'] = None
    
    try:
        # Use GitHub CLI if configured
        commit_changes(config['repo_path'], commit_message, config.get('use_gh_cli', False))
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
    
    # Initialize 'all_completed' flag if it doesn't exist
    if 'all_completed' not in session_state:
        session_state['all_completed'] = False
    
    print(f"\n[Claude Agent] Starting session: {session_state['session_id']}")
    print(f"[Claude Agent] Working with repository: {config['repo_path']}")
    print(f"[Claude Agent] TODO file: {config['todo_file']}")
    print(f"[Claude Agent] Using GitHub CLI: {config.get('use_gh_cli', False)}")
    print(f"[Claude Agent] Claude will manage branches and PRs through the prompt instructions")
    print(f"[Claude Agent] Autonomous mode: Tasks will automatically continue without user confirmation")
    
    # Main loop for processing tasks
    try:
        max_tasks = config["max_tasks"]
        task_complete = True  # Start with task complete (not in review)
        auto_mode = True  # Set to True for hands-off mode
        
        while max_tasks == 0 or session_state["task_count"] < max_tasks:
            # Check if all tasks are completed
            if session_state.get('all_completed', False):
                logging.info("All tasks are completed in TODO.md. Ending session.")
                print("\n[Claude Agent] All tasks are completed in TODO.md. Ending session.")
                break
                
            # If previous task is complete, start a new task; otherwise, review previous task
            if task_complete:
                print("\n[Claude Agent] Working on a new task...")
                task_complete = run_claude_interaction(config, session_state, is_review=False)
            else:
                # This is a review step
                print("\n[Claude Agent] Reviewing the previously implemented task...")
                run_claude_interaction(config, session_state, is_review=True)
                task_complete = True  # After review, mark as complete and move to next task
            
            # Clear context message
            print("\n" + "="*80)
            print("[Claude Agent] CONTEXT CLEARED!")
            print("[Claude Agent] Claude's context has been cleared. Next iteration will be a fresh interaction.")
            print("="*80 + "\n")
            
            # In automatic mode, we don't ask for confirmation
            if not auto_mode:
                # Ask if user wants to continue
                response = input("[Claude Agent] Continue to next task? (y/n): ").strip().lower()
                if response != 'y':
                    logging.info("Session ended by user")
                    print("[Claude Agent] Session ended by user request.")
                    break
            else:
                # In automatic mode, add a brief delay between tasks
                print("[Claude Agent] Continuing to next task automatically in 3 seconds...")
                time.sleep(3)
    
    except KeyboardInterrupt:
        logging.info("Session interrupted by user")
        print("\n[Claude Agent] Session interrupted by user.")
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        print(f"\n[Claude Agent] Error in main loop: {e}")
    
    # Summary message
    print(f"\n[Claude Agent] Session {session_state['session_id']} completed.")
    print(f"[Claude Agent] Repository path: {session_state['repo_path']}")
    print(f"[Claude Agent] Completed tasks: {len(session_state['completed_tasks'])}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
