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
3.  **Implement the Selected Task:**
    *   Develop the code necessary to complete **only the selected task**.
    *   Adhere to the project's standards and requirements as outlined in the .md files.
4.  **Prepare for Code Review:**
    *   Modify the `TODO.md` content to mark the task for review: change "[ ]" to "[R]" for the implemented task.
    *   If the task was part of a larger item, update its sub-tasks or add a note for the next logical step *for that specific item only*.
    *   Do **NOT** add new, unrelated TODOs or plan future work beyond the immediate next step for the completed item if necessary.

**Crucial Instruction:** Focus exclusively on the single task you select. Do not outline a plan for multiple tasks or work on anything beyond the one item identified in Step 2. Before committing your changes ask me to verify it worked ok and test. You don't need to run the project I will handle that.

Here is the current content of TODO.md:
{todo_content}

Additional context:
Here is the README.md content:
{readme_content}
{projectbrief_section}
{testing_summary_section}
{claude_md_section}
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
3.  **Review Implementation:**
    *   Carefully review the code changes related to this task.
    *   Fix any issues, bugs, or improvements needed.
    *   Make sure the implementation meets the project's standards and requirements.
4.  **Complete the Task:**
    *   After you're satisfied with the implementation, modify the `TODO.md` content to mark the task as complete: change "[R]" to "[x]" for the reviewed task.
    *   If the task was part of a larger item, update its sub-tasks or add a note for the next logical step *for that specific item only*.
    *   Do **NOT** add new, unrelated TODOs or plan future work beyond the immediate next step for the completed item if necessary.

**Crucial Instruction:** Focus exclusively on the single task you are reviewing. Do not outline a plan for multiple tasks or work on anything beyond the one item identified in Step 2. Before committing your changes ask me to verify it worked ok and test. You don't need to run the project I will handle that.

Here is the current content of TODO.md:
{todo_content}

Additional context:
Here is the README.md content:
{readme_content}
{projectbrief_section}
{testing_summary_section}
{claude_md_section}
"""
