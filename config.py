"""
Configuration settings for the Claude Agent.
"""
import os
from pathlib import Path

# Default configuration
DEFAULT_CONFIG = {
    "repo_path": ".",
    "todo_file": "TODO.md",
    "log_file": "claude_log.txt",
    "max_tasks": 0,  # 0 means unlimited
    "log_level": "INFO",
    "session_id": None,
    "use_gh_cli": True
}

# Task prompt template based on the PRD
TASK_PROMPT_TEMPLATE = """You are an expert senior software engineer working on production enhancements for the write-to platform.
Your sole objective for this interaction is to complete exactly one task.

Follow these steps precisely:

1. Review Context:
   Read all .md files (README.md, TODO.md, projectbrief.md, testing_summary.md, CLAUDE.md).

2. Select ONE Task:
   I suggest you work on this task: {task}
   Choose the first unchecked task `[ ]` that is actionable and scoped.
   Example selection: "I will work on: [ ] Implement API endpoints for animals list and details that match the frontend".
   Do NOT discuss future tasks.

3. Create Git Branch:
   Generate a kebab-case name like `feature/implement-api-endpoints`.
   Create and switch to this Git branch using appropriate git commands.

4. Implement the Task:
   Write or modify code as required to implement the selected task only.
   Use the provided documentation as guidelines for style and behavior.

5. Update TODO.md:
   Replace `[ ]` with `[review]` for the selected task only.

6. Commit Work:
   Commit your changes with: `feat: Implement [task summary]`.
   Update `.claude/state.json` with task and branch info with the following structure:
   {{
     "last_task": "Task description",
     "last_branch": "feature/branch-name",
     "status": "awaiting_review"
   }}

7. Stop:
   Do not continue. Await human review before proceeding.
"""

# Review prompt template based on the PRD
REVIEW_PROMPT_TEMPLATE = """You are continuing the previously completed task that is awaiting review.

1. Review Context:
   Read TODO.md and .claude/state.json.
   This task was previously marked for review: {task}
   Confirm this is the last completed task in the state file.

2. Review Work:
   Check the branch mentioned in state.json for correctness and completeness of the task.
   Do NOT select or start any new tasks.

3. Apply Fixes:
   Correct or improve the code if necessary.

4. Finalize Task:
   Update TODO.md to change `[review]` to `[x]`.

5. Commit & Merge:
   Commit changes with `fix: Finalize [task summary]`.
   Merge into main, delete the branch.

6. Clear State:
   Set `.claude/state.json` to {{}} to allow new task in next session.
"""

# Empty TODO list template
EMPTY_TODO_TEMPLATE = """You are an expert senior software engineer working on production enhancements.

I notice that the TODO.md file is empty or doesn't contain any tasks marked with "[ ]" or "[review]". This means there are no specific tasks for you to work on at the moment.

Please suggest creating a new TODO.md file with some initial tasks, or provide guidance on what to do next. Use your expertise to suggest potential improvements or features that could be added to the project.

Feel free to:
1. Create a basic TODO.md template with some common development tasks
2. Suggest a project structure if this is a new project
3. Offer to analyze the existing codebase to identify potential improvement areas
"""

# All tasks completed template
ALL_TASKS_COMPLETED_TEMPLATE = """You are an expert senior software engineer working on production enhancements.

Great news! All tasks in the TODO.md file are marked as completed. The project has reached the milestone you set out to achieve.

Please provide a summary of the work that was done and suggest next steps. You could:
1. Suggest creating new tasks for the next phase of development
2. Offer to perform a comprehensive code review
3. Suggest improvements or optimizations based on the completed work
4. Recommend adding tests or documentation for the completed features

Feel free to analyze the current state of the project and provide your professional recommendations on how to proceed from here.
"""