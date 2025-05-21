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
    """Run a Claude API request using Claude Code CLI tool with live streaming output."""
    import subprocess
    import tempfile
    import os
    import json
    import sys
    from datetime import datetime
    
    print(f"\n[Claude Agent] Working on task in {repo_path}...")
    print("[Claude Agent] Using Claude Code CLI with live streaming...")
    
    # Create a temporary file for the prompt
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(prompt)
    except Exception as e:
        print(f"[Claude Agent] Error creating temporary file: {e}")
        return f"ERROR: Failed to create temporary file: {str(e)}"
    
    # Save the prompt for reference
    prompt_file = Path(repo_path) / "claude_prompt.txt"
    try:
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        print(f"[Claude Agent] Saved prompt to: {prompt_file}")
    except Exception as e:
        print(f"[Claude Agent] Warning: Could not save prompt file: {e}")
    
    start_time = datetime.now()
    print(f"[Claude Agent] Started at: {start_time.strftime('%H:%M:%S')}")
    
    # Collect all output for final result
    full_output = []
    final_result = ""
    
    try:
        # Per documentation: Using stream-json format for real-time streaming output
        print("[Claude Agent] Starting Claude Code in streaming mode...")
        
        # Command based on Claude Code documentation
        # -p: Print response (non-interactive mode)
        # --output-format stream-json: Stream output as JSON objects
        # --verbose: Show detailed output
        # --max-turns: Limit number of agentic turns
        cmd = ['claude', '-p', '--output-format', 'stream-json', '--verbose', '--max-turns', '10']
        
        # Start the process with subprocess.run using input from the temp file
        print("[Claude Agent] Executing claude command with live streaming...")
        print("\n" + "="*80)
        print("[Claude Agent] STREAMING OUTPUT BEGIN")
        print("="*80)
        
        # Read the prompt from the temporary file
        with open(temp_file_path, 'r') as f:
            prompt_text = f.read()
            
        # Use Popen for streaming output
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=repo_path,
            bufsize=1  # Line buffered
        )
        
        # Send the prompt to stdin
        if process.stdin:
            process.stdin.write(prompt_text)
            process.stdin.close()
        else:
            print("[Claude Agent] Error: Could not write to process stdin")
            return "ERROR: Process stdin not available"
            
        # Process output line by line as it comes in
        if process.stdout:
            for line in process.stdout:
                # Store original line for debugging if needed
                # print(line, end='', flush=True)  # Commented out to reduce noise
                
                # Collect all output
                full_output.append(line)
                
                # Try to parse as JSON to extract meaningful content
                try:
                    obj = json.loads(line)
                    
                    # Handle different message types with human-readable formatting
                    if "type" in obj:
                        message_type = obj.get("type")
                        
                        # Assistant messages (Claude's thinking)
                        if message_type == "assistant":
                            message = obj.get("message", {})
                            content_items = message.get("content", [])
                            
                            for item in content_items:
                                if isinstance(item, dict):
                                    # Handle text content nicely
                                    if item.get("type") == "text":
                                        text = item.get("text", "").strip()
                                        if text:
                                            sys.stdout.write("\033[34m")  # Blue text
                                            print(f"\n🤖 Claude: {text}\n")
                                            sys.stdout.write("\033[0m")  # Reset color
                                    
                                    # Handle tool use (when Claude is using a tool)
                                    elif item.get("type") == "tool_use":
                                        tool_name = item.get("name", "")
                                        if tool_name:
                                            print(f"🔧 Claude is using tool: {tool_name}")
                        
                        # User messages (results from tools)
                        elif message_type == "user":
                            content_items = obj.get("message", {}).get("content", [])
                            for item in content_items:
                                if isinstance(item, dict):
                                    if item.get("type") == "tool_result":
                                        content = item.get("content", "").strip()
                                        is_error = item.get("is_error", False)
                                        
                                        if is_error:
                                            sys.stdout.write("\033[31m")  # Red for errors
                                            print(f"❌ Tool error: {content}")
                                            sys.stdout.write("\033[0m")  # Reset color
                                        elif content and len(content) < 150:  # Only short results
                                            sys.stdout.write("\033[32m")  # Green for tool results
                                            print(f"✅ Tool result: {content[:150]}...")
                                            sys.stdout.write("\033[0m")  # Reset color
                        
                        # System messages (stats and final results)
                        elif message_type == "system":
                            subtype = obj.get("subtype", "")
                            if subtype == "init":
                                print("\n✨ Claude Code initialized and ready to work\n")
                            if "result" in obj:
                                final_result = obj["result"]
                                print("\n✅ Task completed")
                            if "cost_usd" in obj:
                                print(f"💰 Cost: ${obj['cost_usd']:.5f}")
                            if "duration_ms" in obj:
                                print(f"⏱️ Duration: {obj['duration_ms']/1000:.2f} seconds")
                    
                    # Legacy message format handling
                    elif isinstance(obj, dict) and obj.get('role') == 'assistant' and 'content' in obj:
                        content = obj.get('content', '')
                        if content:
                            sys.stdout.write("\033[34m")  # Blue text for Claude's responses
                            print(f"\n🤖 Claude: {content}\n")
                            sys.stdout.write("\033[0m")  # Reset color
                    
                    # Legacy system message format
                    elif isinstance(obj, dict) and obj.get('role') == 'system':
                        if 'result' in obj:
                            final_result = obj['result']
                            print("\n✅ Task completed")
                        if 'cost_usd' in obj:
                            print(f"💰 Cost: ${obj['cost_usd']:.5f}")
                        if 'duration_ms' in obj:
                            print(f"⏱️ Duration: {obj['duration_ms']/1000:.2f} seconds")
                            
                except json.JSONDecodeError:
                    # Silent failure for non-JSON lines
                    pass
        else:
            print("[Claude Agent] Error: Process stdout not available")
            return "ERROR: Process stdout not available"
            
        # Check stderr for any errors
        if process.stderr:
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"[Claude Agent] STDERR: {stderr_output}")
        
        # Wait for process to complete
        return_code = process.wait()
        
        print("\n" + "="*80)
        print("[Claude Agent] STREAMING OUTPUT END")
        print("="*80)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        print(f"[Claude Agent] Completed at: {end_time.strftime('%H:%M:%S')} (took {elapsed:.2f} seconds)")
        
        # If we didn't parse the final result successfully, try to extract it
        if not final_result and full_output:
            # First try to find the system message with the result
            raw_output = ''.join(full_output)
            output_lines = raw_output.strip().split('\n')
            
            # Look for system messages from the end (they contain the final result)
            for line in reversed(output_lines):
                if not line.strip():
                    continue
                    
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and obj.get('role') == 'system' and 'result' in obj:
                        final_result = obj['result']
                        break
                except Exception:
                    continue
            
            # If we still don't have a result, collect all assistant messages
            if not final_result:
                assistant_messages = []
                for line in output_lines:
                    if not line.strip():
                        continue
                    
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and obj.get('role') == 'assistant' and 'content' in obj:
                            content = obj.get('content', '')
                            if content:
                                assistant_messages.append(content)
                    except Exception:
                        continue
                
                if assistant_messages:
                    final_result = '\n'.join(assistant_messages)
        
        # If we still don't have a result, use all the output as a fallback
        if not final_result:
            print("[Claude Agent] Warning: Could not extract final result from JSON, using raw output")
            final_result = ''.join(full_output)
        
        # Save the response for reference
        response_file = Path(repo_path) / "claude_response.txt"
        try:
            with open(response_file, 'w') as f:
                f.write(final_result)
            print(f"[Claude Agent] Saved response to: {response_file}")
        except Exception as e:
            print(f"[Claude Agent] Warning: Could not save response: {e}")
        
        return final_result
        
    except FileNotFoundError:
        error_message = (
            "ERROR: Claude Code CLI not found. Please install Claude Code using:\n\n"
            "npm install -g @anthropic-ai/claude-code\n\n"
            "Then authenticate by running 'claude' and follow the instructions to log in."
        )
        print(f"[Claude Agent] {error_message}")
        return error_message
        
    except Exception as e:
        error_message = f"ERROR: Failed to execute Claude Code: {str(e)}"
        print(f"[Claude Agent] {error_message}")
        return error_message
        
    finally:
        # Clean up the temporary file
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"[Claude Agent] Warning: Could not delete temporary file: {e}")

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
    print(f"[Claude Agent] Using Claude Code in streaming mode for live updates")
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
            
            # Get date/time for this iteration
            from datetime import datetime
            now = datetime.now()
            print(f"\n[Claude Agent] Task iteration started at: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
            # If previous task is complete, start a new task; otherwise, review previous task
            if task_complete:
                print("\n[Claude Agent] Working on a new task with Claude Code...")
                task_complete = run_claude_interaction(config, session_state, is_review=False)
            else:
                # This is a review step
                print("\n[Claude Agent] Reviewing the previously implemented task with Claude Code...")
                run_claude_interaction(config, session_state, is_review=True)
                task_complete = True  # After review, mark as complete and move to next task
            
            # Clear context message
            print("\n" + "="*80)
            print("[Claude Agent] CONTEXT CLEARED!")
            print("[Claude Agent] Claude's context has been cleared. Next iteration will be a fresh interaction.")
            print("="*80 + "\n")
            
            # Task summary
            todo_path = Path(config['repo_path']) / config['todo_file']
            try:
                if todo_path.exists():
                    # Count tasks in different states for summary
                    todo_content = read_file(todo_path)
                    pending_count = todo_content.count("[ ]")
                    review_count = todo_content.count("[review]")
                    completed_count = todo_content.count("[x]") + todo_content.count("[X]")
                    total_count = pending_count + review_count + completed_count
                    
                    # Calculate completion percentage
                    if total_count > 0:
                        completion_pct = (completed_count / total_count) * 100
                    else:
                        completion_pct = 0
                    
                    print(f"[Claude Agent] TODO Summary:")
                    print(f"  - Pending: {pending_count}")
                    print(f"  - For Review: {review_count}")
                    print(f"  - Completed: {completed_count}")
                    print(f"  - Overall Completion: {completion_pct:.1f}%")
            except Exception as e:
                print(f"[Claude Agent] Could not read TODO file for summary: {e}")
            
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
                delay_seconds = 5
                print(f"[Claude Agent] Continuing to next task automatically in {delay_seconds} seconds...")
                print("[Claude Agent] Press Ctrl+C to interrupt if needed.")
                
                # Allow interruption during delay
                try:
                    time.sleep(delay_seconds)
                except KeyboardInterrupt:
                    print("\n[Claude Agent] Interrupted by user during delay.")
                    logging.info("Session interrupted by user during delay")
                    break
    
    except KeyboardInterrupt:
        logging.info("Session interrupted by user")
        print("\n[Claude Agent] Session interrupted by user.")
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        print(f"\n[Claude Agent] Error in main loop: {e}")
    
    # Summary message
    print("\n" + "="*80)
    print(f"[Claude Agent] SESSION SUMMARY")
    print("="*80)
    print(f"Session ID: {session_state['session_id']}")
    print(f"Repository path: {session_state['repo_path']}")
    print(f"Completed tasks: {len(session_state['completed_tasks'])}")
    
    # List completed tasks
    if session_state['completed_tasks']:
        print("\nCompleted tasks:")
        for i, task in enumerate(session_state['completed_tasks'], 1):
            print(f"  {i}. {task}")
    
    # Final TODO summary
    todo_path = Path(config['repo_path']) / config['todo_file']
    try:
        if todo_path.exists():
            # Count tasks in different states for final summary
            todo_content = read_file(todo_path)
            pending_count = todo_content.count("[ ]")
            review_count = todo_content.count("[review]")
            completed_count = todo_content.count("[x]") + todo_content.count("[X]")
            total_count = pending_count + review_count + completed_count
            
            # Calculate completion percentage
            if total_count > 0:
                completion_pct = (completed_count / total_count) * 100
            else:
                completion_pct = 0
            
            print(f"\nFinal TODO Status:")
            print(f"  - Tasks Pending: {pending_count}")
            print(f"  - Tasks For Review: {review_count}")
            print(f"  - Tasks Completed: {completed_count}")
            print(f"  - Overall Completion: {completion_pct:.1f}%")
            
            if pending_count == 0 and review_count == 0 and completed_count > 0:
                print("\n🎉 All tasks completed successfully! 🎉")
    except Exception as e:
        print(f"Could not read TODO file for final summary: {e}")
    
    print("="*80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
