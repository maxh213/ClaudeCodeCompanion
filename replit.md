# Claude Agent - Replit Guide

## Overview

This repository contains a Python-based automation tool called "Claude Agent" designed to streamline AI-assisted development workflows. The agent helps with completing tasks from a TODO list, creating a single PR for an entire development session, and maintaining context between task iterations.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The Claude Agent follows a modular command-line application architecture with the following key design principles:

1. **Single Responsibility**: Each module and function has a specific, focused purpose.
2. **Configuration Management**: Centralized configuration with defaults and command-line overrides.
3. **State Management**: Maintains state between iterations while clearing context between tasks.
4. **Git Integration**: Automates Git operations like branch creation, commits, and PR management.

The system is built as a Python command-line application that orchestrates Claude's interactions with a repository's task list, ensuring a structured workflow for completing development tasks.

## Key Components

### 1. Command-line Interface (`claude_agent.py`)

The main entry point that:
- Processes command-line arguments
- Initializes configuration
- Sets up logging
- Orchestrates the workflow (branch creation, task selection, PR creation)

### 2. Configuration Management (`config.py`)

Contains:
- Default configuration settings
- Task prompt templates that structure how Claude approaches tasks
- Standardized format for interactions

### 3. Utility Functions (`utils.py`)

Helper functions for:
- File operations (reading/writing)
- Git operations (creating branches, commits, PRs)
- Task management (extracting tasks, formatting prompts)
- Logging setup

### 4. Workflow Configuration (`.replit`)

Defines how the application runs in Replit, specifying:
- Python version (3.11)
- Run commands and workflows
- Deployment configuration

## Data Flow

1. **Initialization**:
   - Parse command-line arguments
   - Load configuration (from defaults and any specified config file)
   - Set up logging

2. **Repository Setup**:
   - Create a git branch for the session
   - Set up a single PR at the beginning

3. **Task Processing Loop**:
   - Read the TODO.md file
   - Extract the next task to work on
   - Format a prompt for Claude to focus on that single task
   - Present the prompt to Claude
   - Claude completes the task and marks it for review (using [R])
   - Commit changes to the repository

4. **Context Management**:
   - Clear context between task iterations
   - Maintain state for the entire session

## External Dependencies

The system relies on:

1. **Python 3.6+**: As the runtime environment
2. **Git**: For repository operations (branch creation, commits, PRs)
3. **Claude AI**: For task completion (implied from the repository description)

No explicit third-party Python packages are mentioned in the available code snippets, suggesting a lightweight approach using mainly standard library components.

## Deployment Strategy

The application is designed to run in a Replit environment with:

1. **Runtime Configuration**:
   - Python 3.11 module specified
   - Stable Nix channel (stable-24_05)

2. **Execution Strategy**:
   - The run button triggers the "Project" workflow
   - The project workflow runs the "ClaudeAgent" workflow in parallel
   - The ClaudeAgent workflow executes `python claude_agent.py --repo-path .`

3. **Usage Pattern**:
   - Users interact with the application via the Replit interface
   - The agent processes one task at a time from a TODO.md file
   - Changes are committed to a single branch with a single PR

This deployment strategy allows for a seamless experience within the Replit environment while maintaining a structured development workflow.