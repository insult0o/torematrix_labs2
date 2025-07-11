#!/bin/bash

# TORE Matrix Labs - Claude Agent Coordinator
# Manages multiple Claude agent sessions for parallel development

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
AGENTS_DIR=".claude_agents"
SESSIONS_DIR=".claude_sessions"
REPO="insult0o/tore-matrix-labs"

print_header() {
    echo -e "${PURPLE}================================================${NC}"
    echo -e "${PURPLE}  TORE Matrix Labs - Agent Coordinator${NC}"
    echo -e "${PURPLE}================================================${NC}"
}

print_usage() {
    echo -e "${CYAN}Usage: $0 [command] [options]${NC}"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  create-session     Create new agent session"
    echo "  list-sessions      List all active agent sessions"
    echo "  session-status     Show status of specific session"
    echo "  coordinate         Run coordination commands across all agents"
    echo "  merge-results      Merge completed work from multiple agents"
    echo "  cleanup           Clean up completed sessions"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 create-session agent-ui-fixes 123"
    echo "  $0 list-sessions"
    echo "  $0 coordinate status"
    echo "  $0 merge-results"
}

setup_directories() {
    mkdir -p "$AGENTS_DIR"
    mkdir -p "$SESSIONS_DIR"
    mkdir -p "logs/agents"
}

create_agent_session() {
    local agent_name="$1"
    local issue_number="$2"
    
    if [[ -z "$agent_name" ]]; then
        echo -e "${RED}❌ Agent name required${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🤖 Creating Agent Session: $agent_name${NC}"
    
    # Create session directory
    session_dir="${SESSIONS_DIR}/${agent_name}"
    mkdir -p "$session_dir"
    
    # Create session configuration
    cat > "${session_dir}/session_config.json" << EOF
{
    "agent_name": "$agent_name",
    "issue_number": ${issue_number:-null},
    "created_at": "$(date -Iseconds)",
    "status": "active",
    "working_branch": "issue-${issue_number:-dev}-${agent_name}",
    "assigned_files": [],
    "completed_tasks": [],
    "current_task": null
}
EOF

    # Create session startup script
    cat > "${session_dir}/startup.sh" << 'EOF'
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
EOF

    chmod +x "${session_dir}/startup.sh"

    # Create progress update script  
    cat > "${session_dir}/update_progress.sh" << 'EOF'
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
EOF

    chmod +x "${session_dir}/update_progress.sh"

    # Create completion script
    cat > "${session_dir}/complete_session.sh" << 'EOF'
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
EOF

    chmod +x "${session_dir}/complete_session.sh"

    # Create agent instructions
    cat > "${session_dir}/AGENT_INSTRUCTIONS.md" << EOF
# Claude Agent Instructions: $agent_name

## Session Setup
This agent session is configured for: **$agent_name**
$(if [[ -n "$issue_number" ]]; then echo "**Assigned Issue**: #$issue_number"; fi)

## Getting Started
1. Run: \`./startup.sh\` to initialize your working environment
2. Check your assigned issue (if any): \`gh issue view $issue_number\`
3. Start working on your assigned tasks
4. Update progress regularly: \`./update_progress.sh\`
5. When done: \`./complete_session.sh\`

## Working Guidelines
- **Focus**: Work only on tasks assigned to this agent
- **Branch**: Use the designated working branch
- **Testing**: Test your changes before completion
- **Communication**: Update progress through GitHub issues
- **Coordination**: Avoid conflicts with other agents

## Essential Commands
\`\`\`bash
# Check session status
cat session_config.json | jq

# View assigned issue
gh issue view $issue_number --repo $REPO

# Update progress  
./update_progress.sh

# Complete session
./complete_session.sh

# Quick status check
../../../scripts/project_operations.sh status
\`\`\`

## Session Files
- \`session_config.json\` - Configuration and progress
- \`startup.sh\` - Initialize session environment
- \`update_progress.sh\` - Update progress and communicate
- \`complete_session.sh\` - Finalize work and create PR
- \`AGENT_INSTRUCTIONS.md\` - This file

## Coordination
This agent is part of a parallel development workflow. Other agents may be working simultaneously on different issues. Coordinate through GitHub Issues and avoid editing the same files when possible.

---
**Session Created**: $(date)
**Agent**: $agent_name
**Ready for parallel development!** 🚀
EOF

    echo -e "${GREEN}✅ Agent session created: $agent_name${NC}"
    echo -e "${CYAN}📁 Session directory: $session_dir${NC}"
    echo -e "${CYAN}📋 Instructions: ${session_dir}/AGENT_INSTRUCTIONS.md${NC}"
    
    if [[ -n "$issue_number" ]]; then
        echo -e "${CYAN}🔗 Assigned Issue: #$issue_number${NC}"
    fi
}

list_sessions() {
    echo -e "${YELLOW}🤖 Active Agent Sessions${NC}"
    echo ""
    
    if [[ ! -d "$SESSIONS_DIR" ]] || [[ -z "$(ls -A "$SESSIONS_DIR" 2>/dev/null)" ]]; then
        echo -e "${YELLOW}No active sessions found${NC}"
        return
    fi
    
    for session_dir in "$SESSIONS_DIR"/*; do
        if [[ -d "$session_dir" && -f "$session_dir/session_config.json" ]]; then
            agent_name=$(jq -r '.agent_name' "$session_dir/session_config.json")
            status=$(jq -r '.status' "$session_dir/session_config.json")
            issue_number=$(jq -r '.issue_number' "$session_dir/session_config.json")
            current_task=$(jq -r '.current_task' "$session_dir/session_config.json")
            created_at=$(jq -r '.created_at' "$session_dir/session_config.json")
            
            case "$status" in
                "active")
                    status_color="$GREEN"
                    status_icon="🟢"
                    ;;
                "completed")
                    status_color="$BLUE"
                    status_icon="✅"
                    ;;
                *)
                    status_color="$YELLOW"
                    status_icon="🟡"
                    ;;
            esac
            
            echo -e "${status_icon} ${CYAN}$agent_name${NC} (${status_color}$status${NC})"
            
            if [[ "$issue_number" != "null" ]]; then
                echo -e "   📋 Issue: #$issue_number"
            fi
            
            if [[ "$current_task" != "null" && "$current_task" != "" ]]; then
                echo -e "   🎯 Current: $current_task"
            fi
            
            echo -e "   📅 Created: $created_at"
            echo ""
        fi
    done
}

session_status() {
    local agent_name="$1"
    
    if [[ -z "$agent_name" ]]; then
        echo -e "${RED}❌ Agent name required${NC}"
        return 1
    fi
    
    session_dir="${SESSIONS_DIR}/${agent_name}"
    
    if [[ ! -f "$session_dir/session_config.json" ]]; then
        echo -e "${RED}❌ Session not found: $agent_name${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}📊 Session Status: $agent_name${NC}"
    echo ""
    
    # Display session info
    jq -r '
        "🤖 Agent: " + .agent_name,
        "📋 Issue: #" + (.issue_number // "unassigned"),
        "🌿 Branch: " + .working_branch,
        "📅 Created: " + .created_at,
        "🎯 Status: " + .status,
        (if .current_task then "📝 Current Task: " + .current_task else "📝 Current Task: None" end),
        "",
        "✅ Completed Tasks:"
    ' "$session_dir/session_config.json"
    
    # List completed tasks
    jq -r '.completed_tasks[]? | "  - " + .' "$session_dir/session_config.json"
}

coordinate_command() {
    local command="$1"
    
    echo -e "${YELLOW}🔄 Coordinating command across all agents: $command${NC}"
    echo ""
    
    for session_dir in "$SESSIONS_DIR"/*; do
        if [[ -d "$session_dir" && -f "$session_dir/session_config.json" ]]; then
            agent_name=$(jq -r '.agent_name' "$session_dir/session_config.json")
            status=$(jq -r '.status' "$session_dir/session_config.json")
            
            if [[ "$status" == "active" ]]; then
                echo -e "${CYAN}🤖 $agent_name${NC}:"
                
                case "$command" in
                    "status")
                        echo -e "  $(jq -r '.current_task // "No current task"' "$session_dir/session_config.json")"
                        ;;
                    "sync")
                        (cd "$session_dir" && git fetch origin && git status --porcelain)
                        ;;
                    "test")
                        echo -e "  Running tests for $agent_name..."
                        # Run tests in session context
                        ;;
                    *)
                        echo -e "  Unknown command: $command"
                        ;;
                esac
                echo ""
            fi
        fi
    done
}

merge_results() {
    echo -e "${YELLOW}🔀 Merging Results from Completed Agents${NC}"
    echo ""
    
    completed_sessions=()
    
    # Find completed sessions
    for session_dir in "$SESSIONS_DIR"/*; do
        if [[ -d "$session_dir" && -f "$session_dir/session_config.json" ]]; then
            status=$(jq -r '.status' "$session_dir/session_config.json")
            agent_name=$(jq -r '.agent_name' "$session_dir/session_config.json")
            
            if [[ "$status" == "completed" ]]; then
                completed_sessions+=("$agent_name")
                echo -e "${GREEN}✅ $agent_name - Ready for merge${NC}"
            fi
        fi
    done
    
    if [[ ${#completed_sessions[@]} -eq 0 ]]; then
        echo -e "${YELLOW}No completed sessions to merge${NC}"
        return
    fi
    
    echo ""
    echo -e "${CYAN}🔀 Merge Strategy:${NC}"
    echo "1. Review all pull requests from completed agents"
    echo "2. Test integrated changes"  
    echo "3. Merge pull requests in dependency order"
    echo "4. Run full integration tests"
    echo "5. Archive completed sessions"
    
    echo ""
    echo -e "${YELLOW}Pull Requests to Review:${NC}"
    
    for agent in "${completed_sessions[@]}"; do
        session_dir="${SESSIONS_DIR}/${agent}"
        issue_number=$(jq -r '.issue_number' "$session_dir/session_config.json")
        
        if [[ "$issue_number" != "null" ]]; then
            echo -e "  🔗 Agent $agent: gh pr list --search \"#$issue_number\" --repo $REPO"
        fi
    done
}

cleanup_sessions() {
    echo -e "${YELLOW}🧹 Cleaning up Completed Sessions${NC}"
    
    archived_count=0
    
    for session_dir in "$SESSIONS_DIR"/*; do
        if [[ -d "$session_dir" && -f "$session_dir/session_config.json" ]]; then
            status=$(jq -r '.status' "$session_dir/session_config.json")
            agent_name=$(jq -r '.agent_name' "$session_dir/session_config.json")
            
            if [[ "$status" == "completed" ]]; then
                # Check if PR is merged
                issue_number=$(jq -r '.issue_number' "$session_dir/session_config.json")
                
                if [[ "$issue_number" != "null" ]]; then
                    issue_state=$(gh issue view "$issue_number" --repo "$REPO" --json state --jq '.state' 2>/dev/null || echo "UNKNOWN")
                    
                    if [[ "$issue_state" == "CLOSED" ]]; then
                        echo -e "${GREEN}📦 Archiving completed session: $agent_name${NC}"
                        
                        # Archive the session
                        archive_dir=".archived_sessions/$(date +%Y%m%d)_${agent_name}"
                        mkdir -p "$(dirname "$archive_dir")"
                        mv "$session_dir" "$archive_dir"
                        
                        ((archived_count++))
                    else
                        echo -e "${YELLOW}⏳ Session $agent_name completed but issue #$issue_number still open${NC}"
                    fi
                else
                    echo -e "${BLUE}📦 Archiving unassigned completed session: $agent_name${NC}"
                    archive_dir=".archived_sessions/$(date +%Y%m%d)_${agent_name}"
                    mkdir -p "$(dirname "$archive_dir")"
                    mv "$session_dir" "$archive_dir"
                    ((archived_count++))
                fi
            fi
        fi
    done
    
    echo -e "${GREEN}✅ Archived $archived_count completed sessions${NC}"
}

# Main execution
main() {
    print_header
    setup_directories
    
    case "${1:-}" in
        "create-session")
            create_agent_session "$2" "$3"
            ;;
        "list-sessions")
            list_sessions
            ;;
        "session-status")
            session_status "$2"
            ;;
        "coordinate")
            coordinate_command "$2"
            ;;
        "merge-results")
            merge_results
            ;;
        "cleanup")
            cleanup_sessions
            ;;
        *)
            print_usage
            ;;
    esac
}

main "$@"