#!/bin/bash

STATE_FILE=".claude/state.json"

if [[ -f "$STATE_FILE" && $(jq -r .status "$STATE_FILE") == "awaiting_review" ]]; then
  PROMPT_FILE="./scripts/review_prompt.txt"
else
  PROMPT_FILE="./scripts/task_prompt.txt"
fi

claude -p "$(cat "$PROMPT_FILE")"