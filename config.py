"""
Configuration settings for the Claude Agent.
"""

DEFAULT_CONFIG = {
    "repo_path": ".",
    "todo_file": "TODO.md",
    "branch_prefix": "claude-session-",
    "pr_title": "Claude Session Changes",
    "pr_base": "main",
    "log_level": "INFO",
    "max_tasks": 0,
    "session_id": None,
}

# Task prompt template
TASK_PROMPT_TEMPLATE = """You are an expert senior software engineer working on production enhancements.  
Your **sole objective for this interaction** is to complete **exactly one task**.

Follow these steps precisely:

1.  **Review Context:** Briefly acknowledge you have reviewed all `.md` files (README.md, TODO.md, projectbrief.md, testing_summary.md, CLAUDE.md) to understand the current project state and requirements.
2.  **Select ONE Task:**
    *   Examine `TODO.md`.
    *   I suggest you work on this task: "{task}"
    *   **State clearly which task you have selected.** For example: "I will work on: [ ] Implement API endpoints for animals list and details that match the frontend".
    *   Do **NOT** plan or discuss any other tasks.
3.  **Branch and PR Management:**
    *   Note that all your task implementations are part of a single branch session.
    *   All your changes will be included in the same pull request for the entire session.
    *   You do not need to create separate branches or PRs for each task.
4.  **Implement the Selected Task:**
    *   Develop the code necessary to complete **only the selected task**.
    *   Adhere to the project's standards and requirements as outlined in the .md files.
5.  **Prepare for Code Review:**
    *   Modify the `TODO.md` content to mark the task for review: change "[ ]" to "[R]" for the implemented task.
    *   If the task was part of a larger item, update its sub-tasks or add a note for the next logical step *for that specific item only*.
    *   Do **NOT** add new, unrelated TODOs or plan future work beyond the immediate next step for the completed item if necessary.

**Crucial Instruction:** Focus exclusively on the single task you select. Do not outline a plan for multiple tasks or work on anything beyond the one item identified in Step 2. Before committing your changes ask me to verify it worked ok and test. You don't need to run the project I will handle that.
"""

# Review prompt template
REVIEW_PROMPT_TEMPLATE = """You are an expert senior software engineer reviewing code changes.
Your **sole objective for this interaction** is to review and fix **exactly one task** that was marked for review.

Follow these steps precisely:

1.  **Review Context:** Briefly acknowledge you have reviewed all `.md` files (README.md, TODO.md, projectbrief.md, testing_summary.md, CLAUDE.md) to understand the current project state and requirements.
2.  **Review Task:**
    *   This task was previously marked for review: "{task}"
    *   **State clearly which task you are reviewing.** 
    *   Do **NOT** plan or discuss any other tasks.
3.  **Branch and PR Management:**
    *   Note that all your task implementations are part of a single branch session.
    *   All your changes will be included in the same pull request for the entire session.
    *   You do not need to create separate branches or PRs for each task.
4.  **Review Implementation:**
    *   Carefully review the code changes related to this task.
    *   Fix any issues, bugs, or improvements needed.
    *   Make sure the implementation meets the project's standards and requirements.
5.  **Complete the Task:**
    *   After you're satisfied with the implementation, modify the `TODO.md` content to mark the task as complete: change "[R]" to "[x]" for the reviewed task.
    *   If the task was part of a larger item, update its sub-tasks or add a note for the next logical step *for that specific item only*.
    *   Do **NOT** add new, unrelated TODOs or plan future work beyond the immediate next step for the completed item if necessary.

**Crucial Instruction:** Focus exclusively on the single task you are reviewing. Do not outline a plan for multiple tasks or work on anything beyond the one item identified in Step 2. Before committing your changes ask me to verify it worked ok and test. You don't need to run the project I will handle that.
"""

# Empty TODO list template
EMPTY_TODO_TEMPLATE = """You are an expert senior software engineer working on production enhancements.

I notice that the TODO.md file is empty or doesn't contain any tasks marked with "[ ]" or "[R]". This means there are no specific tasks for you to work on at the moment.

Here are some suggestions for what you could do:

1. If you believe all tasks have been completed, congratulate the team on a job well done.

2. If this is a new project, you could suggest creating a TODO.md file with some initial tasks based on the project's README.md and other documentation.

3. If there are tasks in the TODO.md but they are not formatted correctly (they should use "- [ ]" format), you could offer to reformat them.

Please respond with your thoughts on the current state of the project and any recommendations you have for next steps. You can also ask the user if there are specific tasks they would like you to focus on.
"""

# All tasks completed template
ALL_TASKS_COMPLETED_TEMPLATE = """You are an expert senior software engineer working on production enhancements.

Congratulations! It appears that all tasks in the TODO.md file have been completed. This is an excellent milestone for the project.

Would you like me to:

1. Review the entire project for any potential improvements or optimizations?
2. Suggest new features or enhancements that could be added to the project?
3. Create a new set of tasks for the next phase of development?
4. Something else?

Please let me know how you'd like to proceed, and I'd be happy to help with the next steps.
"""
