"""
Utility functions for the Claude Agent.
"""

import os
import sys
import re
import logging
import subprocess
from pathlib import Path
from config import (
    TASK_PROMPT_TEMPLATE, 
    REVIEW_PROMPT_TEMPLATE, 
    EMPTY_TODO_TEMPLATE,
    ALL_TASKS_COMPLETED_TEMPLATE
)

def setup_logging(log_level):
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def read_file(file_path):
    """Read content from a file."""
    file_path = Path(file_path)
    if not file_path.exists():
        logging.warning(f"File not found: {file_path}")
        return ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return ""

def write_file(file_path, content):
    """Write content to a file."""
    file_path = Path(file_path)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error writing to file {file_path}: {e}")
        return False

def run_git_command(repo_path, command, capture_output=True):
    """Run a git command in the repository."""
    full_command = ['git'] + command
    cwd = Path(repo_path).absolute()
    
    try:
        if capture_output:
            result = subprocess.run(
                full_command, 
                cwd=cwd, 
                check=True, 
                text=True, 
                capture_output=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(full_command, cwd=cwd, check=True)
            return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {' '.join(full_command)}")
        logging.error(f"Error: {e}")
        if capture_output and e.stderr:
            logging.error(f"Git error output: {e.stderr}")
        raise

def initialize_git_repo(repo_path):
    """Initialize a git repository if it doesn't exist."""
    git_dir = Path(repo_path) / ".git"
    if not git_dir.exists():
        try:
            logging.info(f"Initializing git repository in {repo_path}")
            run_git_command(repo_path, ['init'], capture_output=False)
            # Create initial commit if needed
            try:
                # Check if there are any commits
                run_git_command(repo_path, ['log', '-1'])
            except:
                # No commits yet, create initial commit
                run_git_command(repo_path, ['add', '.'], capture_output=False)
                run_git_command(repo_path, ['commit', '-m', 'Initial commit'], capture_output=False)
            return True
        except Exception as e:
            logging.error(f"Error initializing git repository: {e}")
            raise
    return True

def create_branch(repo_path, branch_name, base_branch):
    """Create a new git branch."""
    try:
        # Initialize repository if needed
        initialize_git_repo(repo_path)
        
        # Try to use the base branch if it exists
        try:
            # Make sure we're on the base branch
            run_git_command(repo_path, ['checkout', base_branch], capture_output=False)
            
            # Try to pull latest changes, but don't fail if remote is not set up
            try:
                run_git_command(repo_path, ['pull'], capture_output=False)
            except:
                logging.warning("Could not pull latest changes. Remote may not be set up.")
        except:
            # Base branch doesn't exist, create it
            logging.warning(f"Base branch '{base_branch}' not found. Creating it.")
            # Get current branch
            current_branch = run_git_command(repo_path, ['branch', '--show-current'])
            if not current_branch:
                # No branch exists, create the base branch
                run_git_command(repo_path, ['checkout', '-b', base_branch], capture_output=False)
        
        # Check if we're already on the target branch
        current_branch = run_git_command(repo_path, ['branch', '--show-current'])
        if current_branch == branch_name:
            logging.info(f"Already on branch: {branch_name}")
            return True
            
        # Create and checkout new branch
        try:
            run_git_command(repo_path, ['checkout', '-b', branch_name], capture_output=False)
        except:
            # Branch might already exist
            try:
                run_git_command(repo_path, ['checkout', branch_name], capture_output=False)
            except Exception as e:
                logging.error(f"Could not checkout branch {branch_name}: {e}")
                raise
        
        logging.info(f"Created and checked out branch: {branch_name}")
        return True
    except Exception as e:
        logging.error(f"Error creating branch: {e}")
        raise

def create_pr(repo_path, branch_name, base_branch, title, description):
    """Create a pull request using git."""
    try:
        # Default PR URL for local repos
        pr_url = f"Local branch created: {branch_name}"
        
        # Check if remote exists
        try:
            # Try to get remote URL
            remote_url = run_git_command(repo_path, ['remote', 'get-url', 'origin'])
            if remote_url:
                # Push the branch to remote
                try:
                    run_git_command(repo_path, ['push', '--set-upstream', 'origin', branch_name], capture_output=False)
                    
                    # For GitHub repositories
                    if "github.com" in str(remote_url):
                        # Extract owner and repo from GitHub URL
                        github_pattern = r'github\.com[:/]([^/]+)/([^/\.]+)'
                        github_match = re.search(github_pattern, str(remote_url))
                        if github_match:
                            owner, repo = github_match.groups()
                            repo = repo.rstrip('.git')
                            pr_url = f"https://github.com/{owner}/{repo}/compare/{base_branch}...{branch_name}?expand=1"
                        else:
                            pr_url = "Could not determine GitHub PR URL from remote"
                    
                    # For GitLab repositories
                    elif "gitlab.com" in str(remote_url):
                        # Extract project path from GitLab URL
                        gitlab_pattern = r'gitlab\.com[:/](.+?)(?:\.git)?$'
                        gitlab_match = re.search(gitlab_pattern, str(remote_url))
                        if gitlab_match:
                            project_path = gitlab_match.group(1)
                            pr_url = f"https://gitlab.com/{project_path}/-/merge_requests/new?merge_request[source_branch]={branch_name}&merge_request[target_branch]={base_branch}"
                        else:
                            pr_url = "Could not determine GitLab PR URL from remote"
                    
                    # For other git hosting services
                    else:
                        pr_url = f"Branch pushed to origin/{branch_name}"
                except Exception as push_error:
                    logging.warning(f"Could not push to remote: {push_error}")
        except Exception as remote_error:
            logging.warning(f"No remote 'origin' found: {remote_error}")
        
        logging.info(f"PR URL: {pr_url}")
        return pr_url
    except Exception as e:
        logging.error(f"Error creating PR: {e}")
        return "Error creating PR"

def commit_changes(repo_path, commit_message):
    """Commit all changes in the repository."""
    try:
        # Add all files
        run_git_command(repo_path, ['add', '.'], capture_output=False)
        
        # Commit with message
        run_git_command(repo_path, ['commit', '-m', commit_message], capture_output=False)
        
        # Try to push to remote, but don't fail if remote is not set up
        try:
            run_git_command(repo_path, ['push'], capture_output=False)
        except Exception as push_error:
            logging.warning(f"Could not push to remote: {push_error}")
            logging.info("Changes committed locally only")
        
        return True
    except Exception as e:
        logging.error(f"Error committing changes: {e}")
        raise

def get_next_task(todo_content):
    """Extract the next uncompleted task or task for review from TODO.md."""
    # First check for tasks marked for review (lines with "[R]")
    review_tasks = re.findall(r'^(\s*[-*] \[R\].+)$', todo_content, re.MULTILINE)
    
    if review_tasks:
        # Return the first task marked for review
        return review_tasks[0].strip(), "review"
    
    # If no review tasks, look for uncompleted tasks (lines with "[ ]")
    uncompleted_tasks = re.findall(r'^(\s*[-*] \[ \].+)$', todo_content, re.MULTILINE)
    
    if uncompleted_tasks:
        # Return the first uncompleted task
        return uncompleted_tasks[0].strip(), "task"
    
    # Check if there are any completed tasks
    completed_tasks = re.findall(r'^(\s*[-*] \[x\].+)$', todo_content, re.MULTILINE)
    
    if completed_tasks:
        # All tasks are completed
        return None, "completed"
    
    # No tasks found at all
    return None, "empty"

def format_prompt_for_task(task, **kwargs):
    """Format the prompt for Claude to work on a task."""
    prompt = TASK_PROMPT_TEMPLATE.format(
        task=task
    )
    return prompt

def format_prompt_for_review(task, **kwargs):
    """Format the prompt for Claude to review a task."""
    prompt = REVIEW_PROMPT_TEMPLATE.format(
        task=task
    )
    return prompt

def format_prompt_for_empty_todo(**kwargs):
    """Format the prompt for Claude when there are no tasks in the TODO list."""
    prompt = EMPTY_TODO_TEMPLATE
    return prompt

def format_prompt_for_all_completed(**kwargs):
    """Format the prompt for Claude when all tasks in the TODO list are completed."""
    prompt = ALL_TASKS_COMPLETED_TEMPLATE
    return prompt
