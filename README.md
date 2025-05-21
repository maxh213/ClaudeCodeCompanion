# Claude Agent

A Python script that automates Claude's workflow for completing tasks from a TODO list with a single PR for the entire session and context clearing between task iterations.

## Features

- Creates a single git branch for an entire development session
- Sets up a single PR at the beginning of the session
- Presents Claude with a prompt to work on one task at a time from a TODO.md file
- Has Claude mark tasks for review (using [R]) instead of checking them off
- Includes a review step at the beginning of each iteration to verify previous work
- Clears context between task iterations to maintain focus on single tasks
- Maintains state between iterations within the same session
- Works with any project directory - just point it at your repo

## Requirements

- Python 3.6+
- Git command-line tools
- Access to Claude AI

## Installation

1. Clone this repository or download the script files
2. Ensure you have Python 3.6+ installed
3. Ensure Git is properly configured on your system

## Usage

```bash
# Run on the current directory
python claude_agent.py --repo-path .

# Run on a specific project directory
python claude_agent.py --repo-path /path/to/your/project

# Additional options
python claude_agent.py --help
```

## How It Works

1. The script creates a Git branch for your session
2. It reads the TODO.md file in the target project
3. It presents Claude with a prompt to work on one task at a time
4. When Claude completes a task, it marks it for review (using [R])
5. In the next iteration, Claude reviews the previous task and marks it as complete if satisfied
6. The process repeats until all tasks are completed
7. All changes are committed to the same branch and included in the same PR

## Command Line Options

- `--repo-path`: Path to the repository you want to work on
- `--todo-file`: Path to the TODO.md file (default: TODO.md in repo path)
- `--branch-prefix`: Prefix for branch names (default: claude-session-)
- `--session-id`: Resume an existing session using this ID
- `--max-tasks`: Maximum number of tasks to complete (0 for unlimited)
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)
