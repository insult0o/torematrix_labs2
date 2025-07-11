#!/bin/bash

# Update agent progress
AGENT_NAME=$(jq -r '.agent_name' session_config.json)
ISSUE_NUMBER=$(jq -r '.issue_number' session_config.json)

echo "📊 Updating progress for agent: $AGENT_NAME"

# Update session config with new progress
read -p "Current task: " current_task
read -p "Completed task (or 'none'): " completed_task

if [[ "$completed_task" != "none" ]]; then
    # Add to completed tasks
    jq --arg task "$completed_task" '.completed_tasks += [$task]' session_config.json > tmp.json && mv tmp.json session_config.json
fi

# Update current task
jq --arg task "$current_task" '.current_task = $task' session_config.json > tmp.json && mv tmp.json session_config.json

# Update timestamp
jq --arg time "$(date -Iseconds)" '.last_updated = $time' session_config.json > tmp.json && mv tmp.json session_config.json

echo "✅ Progress updated!"

# Update GitHub issue if assigned
if [[ "$ISSUE_NUMBER" != "null" ]]; then
    gh issue comment "$ISSUE_NUMBER" --repo "insult0o/tore-matrix-labs" \
        --body "🤖 **Agent Progress Update**: $AGENT_NAME

**Current Task**: $current_task
**Recently Completed**: $completed_task
**Updated**: $(date)

*Auto-updated by agent coordinator*"
fi
