#!/bin/bash

# Claude Agent Session Startup Script
# Run this when starting a new Claude session

AGENT_NAME=$(jq -r '.agent_name' session_config.json)
ISSUE_NUMBER=$(jq -r '.issue_number' session_config.json)
WORKING_BRANCH=$(jq -r '.working_branch' session_config.json)

echo "🤖 Starting Claude Agent Session: $AGENT_NAME"

# Set up working branch
if [[ "$ISSUE_NUMBER" != "null" ]]; then
    echo "📋 Assigned Issue: #$ISSUE_NUMBER"
    gh issue view "$ISSUE_NUMBER" --repo "insult0o/tore-matrix-labs"
fi

echo "🌿 Working Branch: $WORKING_BRANCH"
git checkout -b "$WORKING_BRANCH" 2>/dev/null || git checkout "$WORKING_BRANCH"

echo "✅ Session ready! Start working on your assigned tasks."
echo "📝 Update progress with: ./update_progress.sh"
