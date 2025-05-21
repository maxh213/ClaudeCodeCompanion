# Claude Agent

A Python script that automates Claude's workflow for completing tasks from a TODO list with a single PR for the entire session and context clearing between task iterations.

## Features

- Guides Claude to create a single git branch for an entire development session
- Instructs Claude to set up a single PR for all the tasks
- Presents Claude with a prompt to work on one task at a time from a TODO.md file
- Has Claude mark tasks for review (using [R]) instead of checking them off
- Includes a review step at the beginning of each iteration to verify previous work
- Clears context between task iterations to maintain focus on single tasks
- Works with any project directory - just point it at your repo

## Requirements

- Python 3.6+
- Access to Claude AI

## Installation

1. Clone this repository or download the script files
2. Ensure you have Python 3.6+ installed

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

1. The script starts a session for the target project
2. It reads the TODO.md file in the target project
3. It presents Claude with a prompt to work on one task at a time
4. Claude is instructed to create branches and PRs as part of its workflow
5. When Claude completes a task, it marks it for review (using [R])
6. In the next iteration, Claude reviews the previous task and marks it as complete if satisfied
7. The context is cleared between iterations, but session state is maintained
8. The process repeats until all tasks are completed

## Command Line Options

- `--repo-path`: Path to the repository you want to work on
- `--todo-file`: Path to the TODO.md file (default: TODO.md in repo path)
- `--max-tasks`: Maximum number of tasks to complete (0 for unlimited)
- `--session-id`: Resume an existing session using this ID
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)
