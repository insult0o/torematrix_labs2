#!/bin/bash

# TORE Matrix Labs - GitHub Issues Management Script
# Automates issue creation, assignment, and parallel development coordination

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO="insult0o/tore-matrix-labs"
ISSUES_DIR=".github_issues"
AGENTS_DIR=".claude_agents"

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  TORE Matrix Labs - GitHub Issues Manager${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_usage() {
    echo -e "${CYAN}Usage: $0 [command] [options]${NC}"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  create-bug        Create a new bug report"
    echo "  create-feature    Create a new feature request"
    echo "  create-improve    Create a code improvement issue"
    echo "  list-issues       List all open issues"
    echo "  assign-agent      Assign issue to Claude agent session"
    echo "  create-parallel   Create multiple related issues for parallel work"
    echo "  status           Show current parallel development status"
    echo "  sync             Sync local and remote issue state"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 create-bug"
    echo "  $0 assign-agent 123 agent-ui-fixes"
    echo "  $0 create-parallel \"PDF Viewer Improvements\""
    echo "  $0 status"
}

ensure_gh_cli() {
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
        echo -e "${YELLOW}Install with: sudo apt install gh${NC}"
        exit 1
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        echo -e "${RED}❌ GitHub CLI not authenticated${NC}"
        echo -e "${YELLOW}Run: gh auth login${NC}"
        exit 1
    fi
}

setup_directories() {
    mkdir -p "$ISSUES_DIR"
    mkdir -p "$AGENTS_DIR"
    mkdir -p "logs"
}

create_bug_issue() {
    echo -e "${YELLOW}🐛 Creating Bug Report${NC}"
    
    read -p "Bug title: " title
    read -p "Component (manual-validation/qa-validation/pdf-viewer/project-manager/other): " component
    read -p "Severity (critical/high/medium/low): " severity
    read -p "Description: " description
    read -p "Steps to reproduce: " steps
    read -p "Expected behavior: " expected
    read -p "Actual behavior: " actual
    
    # Create issue body
    cat > "${ISSUES_DIR}/bug_temp.md" << EOF
## 🐛 Bug Description
$description

## 🔄 Steps to Reproduce
$steps

## ✅ Expected Behavior
$expected

## ❌ Actual Behavior
$actual

## 📋 Component Affected
- [x] $component

## 🔍 Severity
- [x] $severity

---
**Auto-created by GitHub Issues Manager**
**Ready for Claude Agent assignment**
EOF

    # Create the issue
    issue_url=$(gh issue create \
        --title "[BUG] $title" \
        --body-file "${ISSUES_DIR}/bug_temp.md" \
        --label "bug,needs-triage,$severity,$component" \
        --repo "$REPO")
    
    echo -e "${GREEN}✅ Bug issue created: $issue_url${NC}"
    
    # Extract issue number
    issue_number=$(echo "$issue_url" | grep -o '[0-9]*$')
    echo "$issue_number" > "${ISSUES_DIR}/latest_issue.txt"
    
    rm "${ISSUES_DIR}/bug_temp.md"
}

create_feature_issue() {
    echo -e "${YELLOW}🚀 Creating Feature Request${NC}"
    
    read -p "Feature title: " title
    read -p "Component target: " component
    read -p "Priority (high/medium/low): " priority
    read -p "Problem statement: " problem
    read -p "Proposed solution: " solution
    read -p "Complexity (simple/medium/complex): " complexity
    
    cat > "${ISSUES_DIR}/feature_temp.md" << EOF
## 🚀 Feature Description
$title

## 🎯 Problem Statement
$problem

## 💡 Proposed Solution
$solution

## 📋 Component Target
- [x] $component

## 🔧 Implementation Complexity
- [x] $complexity

## 📈 Priority
- [x] $priority

---
**Auto-created by GitHub Issues Manager**
**Ready for Claude Agent design and implementation**
EOF

    issue_url=$(gh issue create \
        --title "[FEATURE] $title" \
        --body-file "${ISSUES_DIR}/feature_temp.md" \
        --label "enhancement,needs-review,$priority,$component" \
        --repo "$REPO")
    
    echo -e "${GREEN}✅ Feature issue created: $issue_url${NC}"
    
    issue_number=$(echo "$issue_url" | grep -o '[0-9]*$')
    echo "$issue_number" > "${ISSUES_DIR}/latest_issue.txt"
    
    rm "${ISSUES_DIR}/feature_temp.md"
}

create_improvement_issue() {
    echo -e "${YELLOW}🎯 Creating Code Improvement Issue${NC}"
    
    read -p "Improvement title: " title
    read -p "Target file(s): " files
    read -p "Issue type (performance/readability/maintainability/security): " issue_type
    read -p "Description: " description
    read -p "Expected benefits: " benefits
    read -p "Complexity (simple/medium/complex): " complexity
    
    cat > "${ISSUES_DIR}/improve_temp.md" << EOF
## 🎯 Improvement Target
$title

**File(s)**: $files

## 📊 Current Issues
- [x] $issue_type

$description

## 💡 Proposed Improvements
$benefits

## 🔧 Implementation Complexity
- [x] $complexity

---
**Auto-created by GitHub Issues Manager**
**Ready for Claude Agent code analysis and refactoring**
EOF

    issue_url=$(gh issue create \
        --title "[IMPROVE] $title" \
        --body-file "${ISSUES_DIR}/improve_temp.md" \
        --label "improvement,refactoring,$complexity" \
        --repo "$REPO")
    
    echo -e "${GREEN}✅ Improvement issue created: $issue_url${NC}"
    
    issue_number=$(echo "$issue_url" | grep -o '[0-9]*$')
    echo "$issue_number" > "${ISSUES_DIR}/latest_issue.txt"
    
    rm "${ISSUES_DIR}/improve_temp.md"
}

list_issues() {
    echo -e "${YELLOW}📋 Current Open Issues${NC}"
    
    gh issue list --repo "$REPO" --state open --json number,title,labels,assignees \
        --template '{{range .}}{{printf "#%v" .number | color "blue"}} {{.title}}
  {{range .labels}}{{printf "[%s]" .name | color "yellow"}} {{end}}
  {{if .assignees}}{{range .assignees}}👤 {{.login}} {{end}}{{else}}🔓 Unassigned{{end}}

{{end}}'
}

assign_agent() {
    local issue_number="$1"
    local agent_name="$2"
    
    if [[ -z "$issue_number" || -z "$agent_name" ]]; then
        echo -e "${RED}❌ Usage: assign-agent <issue_number> <agent_name>${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🤖 Assigning Issue #$issue_number to Agent: $agent_name${NC}"
    
    # Create agent assignment record
    cat > "${AGENTS_DIR}/${agent_name}_assignment.md" << EOF
# Claude Agent Assignment: $agent_name

## Assigned Issue
- **Issue #**: $issue_number
- **Assigned At**: $(date)
- **Status**: Active

## Instructions for Claude Agent
1. Start new Claude session with name: \`$agent_name\`
2. Run: \`gh issue view $issue_number --repo $REPO\`
3. Follow the issue description and requirements
4. Create a working branch: \`git checkout -b issue-$issue_number-$agent_name\`
5. Implement the solution
6. Test thoroughly
7. Create pull request when ready
8. Update issue with progress

## Session Commands
\`\`\`bash
# Quick start commands for this agent
git checkout -b issue-$issue_number-$agent_name
gh issue view $issue_number --repo $REPO
./scripts/project_operations.sh status
\`\`\`

## Completion Checklist
- [ ] Code implemented
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Pull request created
- [ ] Issue updated with solution
EOF

    # Add assignment comment to the issue
    gh issue comment "$issue_number" --repo "$REPO" \
        --body "🤖 **Assigned to Claude Agent**: \`$agent_name\`

**Agent Instructions**: See \`.claude_agents/${agent_name}_assignment.md\`

**Working Branch**: \`issue-$issue_number-$agent_name\`

**Status**: 🟡 In Progress"

    echo -e "${GREEN}✅ Issue #$issue_number assigned to agent: $agent_name${NC}"
    echo -e "${CYAN}📋 Agent instructions saved to: ${AGENTS_DIR}/${agent_name}_assignment.md${NC}"
}

create_parallel_issues() {
    local topic="$1"
    
    if [[ -z "$topic" ]]; then
        echo -e "${RED}❌ Usage: create-parallel \"Topic Name\"${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🔄 Creating Parallel Development Issues for: $topic${NC}"
    
    # Define common issue patterns for parallel development
    declare -a subtasks=(
        "UI Components:Fix UI layout and styling issues"
        "Backend Logic:Improve core processing logic"
        "Error Handling:Add comprehensive error handling"
        "Testing:Add unit and integration tests"
        "Documentation:Update documentation and guides"
        "Performance:Optimize performance and memory usage"
    )
    
    echo -e "${CYAN}Creating ${#subtasks[@]} parallel issues...${NC}"
    
    # Create parent tracking issue
    parent_body="# $topic - Parallel Development Tracker

## Overview
This is the parent issue for coordinating parallel development work on: **$topic**

## Sub-Issues
"

    created_issues=()
    
    # Create each sub-issue
    for task in "${subtasks[@]}"; do
        IFS=':' read -r component description <<< "$task"
        
        sub_title="[$topic] $component"
        
        issue_url=$(gh issue create \
            --title "$sub_title" \
            --body "## Task: $component

**Parent Topic**: $topic

## Description
$description

## Implementation Notes
- This is part of parallel development for: $topic
- Coordinate with other agents working on related issues
- Update parent issue with progress

## Checklist
- [ ] Analysis completed
- [ ] Implementation done
- [ ] Tests added
- [ ] Documentation updated
- [ ] Ready for review

---
**Part of parallel development workflow**
**Ready for Claude Agent assignment**" \
            --label "parallel-dev,$topic,$(echo "$component" | tr '[:upper:]' '[:lower:]')" \
            --repo "$REPO")
        
        issue_number=$(echo "$issue_url" | grep -o '[0-9]*$')
        created_issues+=("#$issue_number")
        parent_body+="- [ ] #$issue_number - $component
"
        
        echo -e "${GREEN}  ✅ Created: #$issue_number - $component${NC}"
    done
    
    # Create parent tracking issue
    parent_url=$(gh issue create \
        --title "[PARALLEL] $topic - Development Coordination" \
        --body "$parent_body

## Agent Assignment
Use \`./scripts/github_issues.sh assign-agent <issue_number> <agent_name>\` to assign each sub-issue to different Claude agents.

## Parallel Development Status
🟡 **Ready for parallel development**

Created Issues: ${created_issues[*]}" \
        --label "parallel-dev,coordination,$topic" \
        --repo "$REPO")
    
    parent_number=$(echo "$parent_url" | grep -o '[0-9]*$')
    
    echo -e "${GREEN}🎉 Parallel development setup complete!${NC}"
    echo -e "${CYAN}📋 Parent Issue: #$parent_number${NC}"
    echo -e "${CYAN}🔧 Sub-Issues: ${created_issues[*]}${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Assign each sub-issue to different Claude agent sessions"
    echo "2. Each agent works on their assigned component"
    echo "3. Coordinate through the parent issue"
    echo ""
    echo -e "${YELLOW}Example assignments:${NC}"
    for i in "${!created_issues[@]}"; do
        issue_num="${created_issues[$i]#\#}"
        component="${subtasks[$i]%:*}"
        agent_name="agent-$(echo "$component" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
        echo "  ./scripts/github_issues.sh assign-agent $issue_num $agent_name"
    done
}

show_status() {
    echo -e "${YELLOW}📊 Parallel Development Status${NC}"
    echo ""
    
    # Show open issues by label
    echo -e "${CYAN}🔄 Active Issues:${NC}"
    gh issue list --repo "$REPO" --state open --limit 50 \
        --json number,title,labels,assignees,createdAt \
        --jq '.[] | select(.labels[]?.name | contains("parallel-dev")) | 
               "\(.number): \(.title)
               Labels: \(.labels | map(.name) | join(", "))
               \(if .assignees | length > 0 then "👤 " + (.assignees | map(.login) | join(", ")) else "🔓 Unassigned" end)
               Created: \(.createdAt | strptime("%Y-%m-%dT%H:%M:%SZ") | strftime("%Y-%m-%d %H:%M"))
               "'
    
    echo ""
    echo -e "${CYAN}🤖 Agent Assignments:${NC}"
    if ls "${AGENTS_DIR}"/*.md &> /dev/null; then
        for assignment in "${AGENTS_DIR}"/*.md; do
            agent_name=$(basename "$assignment" _assignment.md)
            if [[ -f "$assignment" ]]; then
                issue_num=$(grep "Issue #" "$assignment" | grep -o '[0-9]*')
                echo -e "  ${GREEN}$agent_name${NC} → Issue #$issue_num"
            fi
        done
    else
        echo -e "  ${YELLOW}No active agent assignments${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}📈 Summary:${NC}"
    open_issues=$(gh issue list --repo "$REPO" --state open --limit 1000 | wc -l)
    parallel_issues=$(gh issue list --repo "$REPO" --state open --label "parallel-dev" --limit 1000 | wc -l)
    
    echo -e "  Total Open Issues: ${GREEN}$open_issues${NC}"
    echo -e "  Parallel Dev Issues: ${GREEN}$parallel_issues${NC}"
}

sync_issues() {
    echo -e "${YELLOW}🔄 Syncing Issue State${NC}"
    
    # Update local tracking
    gh issue list --repo "$REPO" --state all --json number,title,state,labels \
        --jq '.[] | "\(.number),\(.title),\(.state),\(.labels | map(.name) | join(";"))"' \
        > "${ISSUES_DIR}/issues_state.csv"
    
    # Clean up closed issue assignments
    for assignment in "${AGENTS_DIR}"/*.md; do
        if [[ -f "$assignment" ]]; then
            issue_num=$(grep "Issue #" "$assignment" | grep -o '[0-9]*' | head -1)
            if [[ -n "$issue_num" ]]; then
                state=$(gh issue view "$issue_num" --repo "$REPO" --json state --jq '.state')
                if [[ "$state" == "CLOSED" ]]; then
                    echo -e "  ${YELLOW}Archiving closed assignment: $(basename "$assignment")${NC}"
                    mv "$assignment" "${AGENTS_DIR}/archived_$(basename "$assignment")"
                fi
            fi
        fi
    done
    
    echo -e "${GREEN}✅ Sync complete${NC}"
}

# Main script execution
main() {
    print_header
    
    case "${1:-}" in
        "create-bug")
            ensure_gh_cli
            setup_directories
            create_bug_issue
            ;;
        "create-feature")
            ensure_gh_cli
            setup_directories
            create_feature_issue
            ;;
        "create-improve")
            ensure_gh_cli
            setup_directories
            create_improvement_issue
            ;;
        "list-issues")
            ensure_gh_cli
            list_issues
            ;;
        "assign-agent")
            ensure_gh_cli
            setup_directories
            assign_agent "$2" "$3"
            ;;
        "create-parallel")
            ensure_gh_cli
            setup_directories
            create_parallel_issues "$2"
            ;;
        "status")
            ensure_gh_cli
            setup_directories
            show_status
            ;;
        "sync")
            ensure_gh_cli
            setup_directories
            sync_issues
            ;;
        *)
            print_usage
            ;;
    esac
}

# Execute main function with all arguments
main "$@"