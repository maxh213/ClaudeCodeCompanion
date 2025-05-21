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
python claude_agent.py [options]
