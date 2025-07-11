#!/bin/bash

# Complete agent session and prepare for merge
AGENT_NAME=$(jq -r '.agent_name' session_config.json)
ISSUE_NUMBER=$(jq -r '.issue_number' session_config.json)
WORKING_BRANCH=$(jq -r '.working_branch' session_config.json)

echo "🎉 Completing agent session: $AGENT_NAME"

# Update session status
jq '.status = "completed" | .completed_at = "'"$(date -Iseconds)"'"' session_config.json > tmp.json && mv tmp.json session_config.json

# Commit any pending changes
git add .
git commit -m "🤖 Agent $AGENT_NAME: Complete work on issue #$ISSUE_NUMBER" || echo "No changes to commit"

# Push branch
git push -u origin "$WORKING_BRANCH"

# Create pull request if issue assigned
if [[ "$ISSUE_NUMBER" != "null" ]]; then
    gh pr create \
        --title "🤖 Agent $AGENT_NAME: Fix issue #$ISSUE_NUMBER" \
        --body "## Agent Work Summary

**Agent**: $AGENT_NAME
**Issue**: #$ISSUE_NUMBER
**Branch**: $WORKING_BRANCH

## Completed Tasks
$(jq -r '.completed_tasks[]' session_config.json | sed 's/^/- /')

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass  
- [ ] Manual testing completed

Closes #$ISSUE_NUMBER" \
        --repo "insult0o/tore-matrix-labs"
        
    echo "🔗 Pull request created for issue #$ISSUE_NUMBER"
fi

echo "✅ Session completed and ready for review!"
