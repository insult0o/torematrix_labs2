#!/bin/bash

# TORE Matrix Labs - Issue #4 Setup Script
# Creates automation structure for issue #4

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}================================================${NC}"
    echo -e "${PURPLE}  TORE Matrix Labs - Issue #4 Setup${NC}"
    echo -e "${PURPLE}================================================${NC}"
}

setup_issue_4() {
    local issue_title="$1"
    local issue_description="$2" 
    local agent_name="$3"
    local expected_files="$4"
    local priority="$5"
    
    if [[ -z "$issue_title" ]]; then
        echo -e "${RED}❌ Please provide issue details${NC}"
        echo -e "${YELLOW}Usage: $0 \"Issue Title\" \"Description\" \"agent-name\" \"Files\" \"Priority\"${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}🚀 Setting up Issue #4: $issue_title${NC}"
    echo ""
    
    # Create agent assignment file
    mkdir -p ".claude_agents"
    cat > ".claude_agents/${agent_name}_assignment.md" << EOF
# Claude Agent Assignment: $agent_name

## Assigned Issue
- **Issue #**: 4
- **Title**: $issue_title
- **Assigned At**: $(date)
- **Status**: Active

## Problem Description
$issue_description

## Expected Files to Modify
$expected_files

## Priority Level
$priority

## Instructions for Claude Agent
1. **Start Command**: 
   \`\`\`
   You are "$agent_name" working on GitHub issue #4.
   
   Repository: https://github.com/insult0o/tore-matrix-labs
   Issue: https://github.com/insult0o/tore-matrix-labs/issues/4
   
   Task: $issue_description
   Working branch: issue-4-$agent_name
   \`\`\`

2. **Setup Working Branch**:
   \`\`\`bash
   git checkout -b issue-4-$agent_name
   \`\`\`

3. **Check Project Status**:
   \`\`\`bash
   ./scripts/project_operations.sh status
   \`\`\`

4. **Test Projects**: Use "4.tore" and "7.tore" for testing

5. **Progress Updates**: Comment on GitHub issue #4

## Completion Checklist
- [ ] Problem identified and understood
- [ ] Solution implemented
- [ ] Code tested with test projects
- [ ] No regressions introduced
- [ ] Pull request created
- [ ] Issue updated with solution

## Session Recovery
If session is interrupted, restart with:
\`\`\`bash
git checkout issue-4-$agent_name
gh issue view 4 --repo insult0o/tore-matrix-labs
\`\`\`
EOF

    # Create Claude prompt
    mkdir -p ".claude_prompts"
    cat > ".claude_prompts/$agent_name.txt" << EOF
You are "$agent_name" working on GitHub issue #4 in the tore-matrix-labs repository.

Issue: "$issue_title"

Repository: https://github.com/insult0o/tore-matrix-labs
Issue URL: https://github.com/insult0o/tore-matrix-labs/issues/4

**Problem**: $issue_description

**Your Task**: 
1. Investigate the root cause of this issue
2. Analyze the affected components and code
3. Implement a comprehensive solution
4. Test thoroughly with existing projects
5. Ensure no regressions are introduced

**Working Branch**: issue-4-$agent_name

**Expected Files to Modify**:
$expected_files

**Priority**: $priority

Please start by examining the current codebase to understand the issue and identify the best approach for a solution.
EOF

    # Create GitHub comment template
    cat > ".github_issue_4_comment.txt" << EOF
🤖 **Assigned to Claude Agent**: \`$agent_name\`

**Working Branch**: \`issue-4-$agent_name\`
**Status**: 🟡 Ready for agent pickup

**Agent Focus**: $issue_description

**Expected Files**: 
$expected_files

**Priority**: $priority

**Agent Instructions**:
1. Create working branch: \`git checkout -b issue-4-$agent_name\`
2. Focus on the specific problem described in this issue
3. Test your changes thoroughly
4. Create pull request when ready
5. Update this issue with progress comments

**Testing Requirements**: 
- Verify the fix works with existing test projects
- Test with projects "4.tore" and "7.tore" mentioned in CLAUDE.md
- Ensure no regressions in other functionality
EOF
    
    echo -e "${GREEN}✅ Issue #4 setup complete!${NC}"
    echo -e "${CYAN}📁 Agent assignment: .claude_agents/${agent_name}_assignment.md${NC}"
    echo -e "${CYAN}📝 Claude prompt: .claude_prompts/$agent_name.txt${NC}"
    echo -e "${CYAN}💬 GitHub comment: .github_issue_4_comment.txt${NC}"
    echo ""
    echo -e "${YELLOW}🔗 Manual Steps:${NC}"
    echo "1. Copy .github_issue_4_comment.txt content to GitHub issue #4"
    echo "2. Start Claude session with .claude_prompts/$agent_name.txt content"
    echo "3. Let the agent work on the issue"
}

show_usage() {
    echo -e "${CYAN}Usage: $0 \"Issue Title\" \"Description\" \"agent-name\" \"Files\" \"Priority\"${NC}"
    echo ""
    echo -e "${YELLOW}Example:${NC}"
    echo "$0 \\"
    echo "  \"Performance Issue\" \\"
    echo "  \"Application is slow when loading large PDFs\" \\"
    echo "  \"agent-performance\" \\"
    echo "  \"- document_processor.py
- pdf_viewer.py
- memory_manager.py\" \\"
    echo "  \"Medium - Performance optimization\""
    echo ""
    echo -e "${YELLOW}Quick Templates:${NC}"
    echo "  $0 ui-bug       # UI/display related bug"
    echo "  $0 pdf-bug      # PDF viewer related bug"
    echo "  $0 data-bug     # Data processing bug"
    echo "  $0 perf-issue   # Performance issue"
}

# Quick templates
setup_quick_template() {
    case "$1" in
        "ui-bug")
            setup_issue_4 \
                "UI Display Bug" \
                "UI component not displaying correctly or behaving unexpectedly" \
                "agent-ui-fix" \
                "- tore_matrix_labs/ui/components/
- tore_matrix_labs/ui/main_window.py
- Related UI files" \
                "High - UI functionality broken"
            ;;
        "pdf-bug")
            setup_issue_4 \
                "PDF Viewer Bug" \
                "PDF viewer not working correctly - display, highlighting, or navigation issues" \
                "agent-pdf-fix" \
                "- tore_matrix_labs/ui/components/pdf_viewer.py
- tore_matrix_labs/ui/highlighting/
- PDF-related components" \
                "High - Core PDF functionality broken"
            ;;
        "data-bug")
            setup_issue_4 \
                "Data Processing Bug" \
                "Data processing, storage, or retrieval not working correctly" \
                "agent-data-fix" \
                "- tore_matrix_labs/core/document_processor.py
- tore_matrix_labs/models/
- Data processing components" \
                "Medium - Data integrity issue"
            ;;
        "perf-issue")
            setup_issue_4 \
                "Performance Issue" \
                "Application performance problems - slow loading, high memory usage, or lag" \
                "agent-performance" \
                "- tore_matrix_labs/core/
- Performance-critical components
- Memory management files" \
                "Low - Performance optimization"
            ;;
        *)
            show_usage
            ;;
    esac
}

commit_and_push() {
    echo -e "${YELLOW}📤 Committing and pushing Issue #4 setup${NC}"
    
    git add .claude_agents/ .claude_prompts/ .github_issue_4_comment.txt scripts/setup_issue_4.sh
    
    if git diff --staged --quiet; then
        echo -e "${YELLOW}No changes to commit${NC}"
    else
        git commit -m "🤖 AUTOMATION: Issue #4 setup - $(cat .claude_agents/*_assignment.md | grep "Title:" | head -1 | cut -d: -f2 | xargs)

✅ Agent Setup:
- Assignment file created
- Claude prompt ready
- GitHub comment template prepared
- Working branch specified

🚀 Ready for parallel development!

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
        
        git push origin main
        echo -e "${GREEN}✅ Issue #4 setup pushed to GitHub${NC}"
    fi
}

# Main execution
main() {
    print_header
    
    if [[ $# -eq 5 ]]; then
        setup_issue_4 "$1" "$2" "$3" "$4" "$5"
        commit_and_push
    elif [[ $# -eq 1 ]]; then
        setup_quick_template "$1"
        commit_and_push
    else
        show_usage
    fi
}

main "$@"