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
    "use_gh_cli": True
}

# Task prompt template based on the PRD
TASK_PROMPT_TEMPLATE = """You are an expert senior software engineer working on production enhancements for the write-to platform.
Your sole objective for this interaction is to complete exactly one task.

Follow these steps precisely:

1. Review Context:
   Read all .md files (README.md, TODO.md, projectbrief.md, testing_summary.md, CLAUDE.md).

2. Select ONE Task:
   I suggest you work on this task: "{task}"
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
   {
     "last_task": "Task description",
     "last_branch": "feature/branch-name",
     "status": "awaiting_review"
   }

7. Stop:
   Do not continue. Await human review before proceeding.
"""

# Review prompt template based on the PRD
REVIEW_PROMPT_TEMPLATE = """You are continuing the previously completed task that is awaiting review.

1. Review Context:
   Read TODO.md and .claude/state.json.
   This task was previously marked for review: "{task}"
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
   Set `.claude/state.json` to `{}` to allow new task in next session.
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
