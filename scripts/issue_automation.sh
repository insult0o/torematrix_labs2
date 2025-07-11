#!/bin/bash

# TORE Matrix Labs - Issue Automation Script
# Automates issue assignment, agent setup, and GitHub integration

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
REPO="insult0o/tore-matrix-labs"

print_header() {
    echo -e "${PURPLE}================================================${NC}"
    echo -e "${PURPLE}  TORE Matrix Labs - Issue Automation${NC}"
    echo -e "${PURPLE}================================================${NC}"
}

assign_issue_to_agent() {
    local issue_number="$1"
    local agent_name="$2"
    local issue_title="$3"
    local description="$4"
    local expected_files="$5"
    local priority="$6"
    
    echo -e "${YELLOW}🤖 Assigning Issue #$issue_number to $agent_name${NC}"
    
    # Create assignment comment for GitHub
    local comment_body="🤖 **Assigned to Claude Agent**: \`$agent_name\`

**Working Branch**: \`issue-$issue_number-$agent_name\`
**Status**: 🟡 Ready for agent pickup

**Agent Focus**: $description
**Expected Files**: 
$expected_files

**Priority**: $priority

**Agent Instructions**:
1. Create working branch: \`git checkout -b issue-$issue_number-$agent_name\`
2. Focus on the specific problem described in this issue
3. Test your changes thoroughly
4. Create pull request when ready
5. Update this issue with progress comments

**Testing Requirements**: 
- Verify the fix works with existing test projects
- Test with projects \"4.tore\" and \"7.tore\" mentioned in CLAUDE.md
- Ensure no regressions in other functionality"

    # Add comment to GitHub issue
    gh issue comment "$issue_number" --repo "$REPO" --body "$comment_body"
    
    # Create local agent assignment file
    mkdir -p ".claude_agents"
    cat > ".claude_agents/${agent_name}_assignment.md" << EOF
# Claude Agent Assignment: $agent_name

## Assigned Issue
- **Issue #**: $issue_number
- **Title**: $issue_title
- **Assigned At**: $(date)
- **Status**: Active

## Problem Description
$description

## Expected Files to Modify
$expected_files

## Priority Level
$priority

## Instructions for Claude Agent
1. **Start Command**: 
   \`\`\`
   You are "$agent_name" working on GitHub issue #$issue_number.
   
   Repository: https://github.com/$REPO
   Issue: https://github.com/$REPO/issues/$issue_number
   
   Task: $description
   Working branch: issue-$issue_number-$agent_name
   \`\`\`

2. **Setup Working Branch**:
   \`\`\`bash
   git checkout -b issue-$issue_number-$agent_name
   \`\`\`

3. **Check Project Status**:
   \`\`\`bash
   ./scripts/project_operations.sh status
   \`\`\`

4. **Test Projects**: Use "4.tore" and "7.tore" for testing

5. **Progress Updates**: Comment on GitHub issue #$issue_number

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
git checkout issue-$issue_number-$agent_name
gh issue view $issue_number --repo $REPO
\`\`\`
EOF

    echo -e "${GREEN}✅ Issue #$issue_number assigned to $agent_name${NC}"
    echo -e "${CYAN}📋 Assignment file: .claude_agents/${agent_name}_assignment.md${NC}"
}

setup_all_current_issues() {
    echo -e "${YELLOW}🚀 Setting up all current TORE Matrix issues${NC}"
    echo ""
    
    # Issue #3: Areas not displayed
    echo -e "${CYAN}Setting up Issue #3: Areas not displayed${NC}"
    assign_issue_to_agent \
        "3" \
        "agent-ui-areas" \
        "bug_cut_areas_not_displayed" \
        "Fix areas not displaying in document preview - areas that were cut/selected are not showing in the preview" \
        "- \`tore_matrix_labs/ui/components/manual_validation_widget.py\`
- \`tore_matrix_labs/ui/components/pdf_viewer.py\`
- \`tore_matrix_labs/core/area_storage_manager.py\`
- \`tore_matrix_labs/ui/highlighting/highlighting_engine.py\`" \
        "High - Critical UI functionality"
    
    echo ""
    
    # Issue #2: Multiple docs loaded
    echo -e "${CYAN}Setting up Issue #2: Multiple docs duplication${NC}"
    assign_issue_to_agent \
        "2" \
        "agent-project-docs" \
        "bug_multiple_docs_loaded" \
        "Fix duplicate documents appearing when reprocessing and reloading projects" \
        "- \`tore_matrix_labs/ui/main_window.py\`
- \`tore_matrix_labs/ui/components/project_manager_widget.py\`
- \`tore_matrix_labs/core/document_processor.py\`
- \`tore_matrix_labs/models/project_models.py\`" \
        "Medium - Project state integrity issue"
    
    echo ""
    
    # Issue #1: Text highlighting
    echo -e "${CYAN}Setting up Issue #1: Text highlighting broken${NC}"
    assign_issue_to_agent \
        "1" \
        "agent-highlight-sync" \
        "bug_text_highlight" \
        "Fix text highlighting synchronization between extracted content and PDF coordinates" \
        "- \`tore_matrix_labs/ui/highlighting/highlighting_engine.py\`
- \`tore_matrix_labs/ui/highlighting/coordinate_mapper.py\`
- \`tore_matrix_labs/ui/components/pdf_viewer.py\`
- \`tore_matrix_labs/ui/components/page_validation_widget.py\`" \
        "High - Core functionality broken"
    
    echo ""
    echo -e "${GREEN}🎉 All issues assigned to agents!${NC}"
}

create_claude_prompts() {
    echo -e "${YELLOW}📝 Creating Claude Agent Startup Prompts${NC}"
    
    mkdir -p ".claude_prompts"
    
    # Agent 1: UI Areas
    cat > ".claude_prompts/agent-ui-areas.txt" << 'EOF'
You are "agent-ui-areas" working on GitHub issue #3 in the tore-matrix-labs repository.

Issue: "bug_cut_areas_not_displayed" - Areas not displaying in document preview

Repository: https://github.com/insult0o/tore-matrix-labs
Issue URL: https://github.com/insult0o/tore-matrix-labs/issues/3

**Problem**: Areas that were cut/selected in previous sessions are not being displayed in the document preview, even though they exist in the project data.

**Your Task**: 
1. Investigate why areas aren't showing in the preview
2. Check manual_validation_widget.py area display logic
3. Verify area storage and retrieval in area_storage_manager.py
4. Fix the highlighting/display synchronization
5. Test with projects "4.tore" and "7.tore"

**Working Branch**: issue-3-agent-ui-areas

**Focus Areas**:
- Manual validation widget area list display
- PDF viewer area highlighting
- Area storage and retrieval mechanisms
- Highlighting engine integration

Please start by examining the current state and identifying why areas aren't displaying properly.
EOF

    # Agent 2: Project Docs
    cat > ".claude_prompts/agent-project-docs.txt" << 'EOF'
You are "agent-project-docs" working on GitHub issue #2 in the tore-matrix-labs repository.

Issue: "bug_multiple_docs_loaded" - Duplicate documents appearing in projects

Repository: https://github.com/insult0o/tore-matrix-labs
Issue URL: https://github.com/insult0o/tore-matrix-labs/issues/2

**Problem**: When reprocessing documents inside a saved project, after restarting session and reopening the project, duplicate documents appear in the project document list. The more you process/save/reopen, the more duplicates appear.

**Your Task**:
1. Investigate document loading and storage logic
2. Find where duplicate documents are being added
3. Fix the project state management to prevent duplicates
4. Ensure proper cleanup when reprocessing
5. Test with existing projects to verify fix

**Working Branch**: issue-2-agent-project-docs

**Focus Areas**:
- Project loading logic in main_window.py
- Document list management in project_manager_widget.py
- Document processor state handling
- Project model data integrity

Please start by examining how documents are loaded and stored in projects to identify the duplication source.
EOF

    # Agent 3: Highlight Sync
    cat > ".claude_prompts/agent-highlight-sync.txt" << 'EOF'
You are "agent-highlight-sync" working on GitHub issue #1 in the tore-matrix-labs repository.

Issue: "bug_text_highlight" - Text highlighting not synchronizing between areas

Repository: https://github.com/insult0o/tore-matrix-labs
Issue URL: https://github.com/insult0o/tore-matrix-labs/issues/1

**Problem**: When highlighting text in the extracted content area, the corresponding text is not being highlighted at the accurate coordinates in the document viewing area. The synchronization between text selection and PDF coordinates is broken.

**Your Task**:
1. Investigate text-to-coordinate mapping logic
2. Fix highlighting synchronization between extracted content and PDF viewer
3. Ensure accurate coordinate conversion
4. Test highlighting in both directions (content → PDF and PDF → content)
5. Verify with QA validation and manual validation workflows

**Working Branch**: issue-1-agent-highlight-sync

**Focus Areas**:
- Highlighting engine coordinate mapping
- PDF viewer highlighting display
- Page validation widget text synchronization
- Coordinate mapper accuracy

Please start by examining the current highlighting workflow to identify where the synchronization breaks.
EOF

    echo -e "${GREEN}✅ Claude prompts created in .claude_prompts/${NC}"
    echo -e "${CYAN}📋 Ready-to-use prompts for each agent${NC}"
}

add_github_labels() {
    echo -e "${YELLOW}🏷️ Adding GitHub labels to issues${NC}"
    
    # Issue #3 labels
    gh issue edit 3 --add-label "bug,ui-component,agent-ui,high-priority,manual-validation" --repo "$REPO" 2>/dev/null || echo "Labels may already exist"
    
    # Issue #2 labels  
    gh issue edit 2 --add-label "bug,project-management,agent-project,medium-priority,data-integrity" --repo "$REPO" 2>/dev/null || echo "Labels may already exist"
    
    # Issue #1 labels
    gh issue edit 1 --add-label "bug,highlighting,agent-highlight,high-priority,core-functionality" --repo "$REPO" 2>/dev/null || echo "Labels may already exist"
    
    echo -e "${GREEN}✅ GitHub labels added${NC}"
}

push_to_github() {
    echo -e "${YELLOW}📤 Pushing automation files to GitHub${NC}"
    
    # Add all automation files
    git add .claude_agents/
    git add .claude_prompts/
    git add scripts/issue_automation.sh
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        echo -e "${YELLOW}No new changes to commit${NC}"
    else
        # Commit changes
        git commit -m "🤖 AUTOMATION: Complete issue assignment system for parallel development

✅ Issue Assignments:
- Issue #3: agent-ui-areas (areas display fix)
- Issue #2: agent-project-docs (duplicate docs fix)  
- Issue #1: agent-highlight-sync (text highlighting fix)

✅ Agent Setup:
- Assignment files in .claude_agents/
- Ready-to-use prompts in .claude_prompts/
- Complete automation in scripts/issue_automation.sh

✅ GitHub Integration:
- Agent assignments commented on issues
- Labels added for organization
- Working branches specified

🚀 Ready for parallel development with 3 Claude agents!

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
        
        # Push to GitHub
        git push origin main
        
        echo -e "${GREEN}✅ Automation files pushed to GitHub${NC}"
    fi
}

show_next_steps() {
    echo -e "${GREEN}🎉 PARALLEL DEVELOPMENT SETUP COMPLETE!${NC}"
    echo ""
    echo -e "${CYAN}📋 What's Been Set Up:${NC}"
    echo "✅ Issue #3 → agent-ui-areas (areas display)"
    echo "✅ Issue #2 → agent-project-docs (duplicate docs)"  
    echo "✅ Issue #1 → agent-highlight-sync (text highlighting)"
    echo ""
    echo -e "${YELLOW}🚀 Next Steps - Start Your 3 Claude Agents:${NC}"
    echo ""
    echo -e "${PURPLE}Agent 1 (UI Areas):${NC}"
    echo "Open Claude tab and paste:"
    echo -e "${BLUE}$(cat .claude_prompts/agent-ui-areas.txt | head -5)${NC}"
    echo ""
    echo -e "${PURPLE}Agent 2 (Project Docs):${NC}"
    echo "Open Claude tab and paste:"
    echo -e "${BLUE}$(cat .claude_prompts/agent-project-docs.txt | head -5)${NC}"
    echo ""
    echo -e "${PURPLE}Agent 3 (Highlight Sync):${NC}"
    echo "Open Claude tab and paste:"
    echo -e "${BLUE}$(cat .claude_prompts/agent-highlight-sync.txt | head -5)${NC}"
    echo ""
    echo -e "${GREEN}🎯 Result: 3 agents working on 3 different problems simultaneously!${NC}"
    echo ""
    echo -e "${CYAN}📊 Monitor Progress:${NC}"
    echo "- Check GitHub issues for agent comments"
    echo "- Run: ./scripts/github_issues.sh status"
    echo "- Watch for pull requests from each agent"
}

print_usage() {
    echo -e "${CYAN}Usage: $0 [command]${NC}"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  setup-all      Set up all current issues (3, 2, 1) with agents"
    echo "  create-prompts Create ready-to-use Claude prompts"
    echo "  add-labels     Add GitHub labels to issues"
    echo "  push           Push automation files to GitHub"
    echo "  full-setup     Do everything (setup + prompts + labels + push)"
    echo "  show-prompts   Display the Claude prompts to copy/paste"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 full-setup     # Complete automated setup"
    echo "  $0 show-prompts   # Show prompts for manual use"
}

show_prompts() {
    echo -e "${YELLOW}📝 Claude Agent Prompts (Copy & Paste These):${NC}"
    echo ""
    
    echo -e "${PURPLE}=== AGENT 1: UI Areas (Issue #3) ===${NC}"
    echo -e "${BLUE}"
    cat .claude_prompts/agent-ui-areas.txt
    echo -e "${NC}"
    echo ""
    
    echo -e "${PURPLE}=== AGENT 2: Project Docs (Issue #2) ===${NC}"
    echo -e "${BLUE}"
    cat .claude_prompts/agent-project-docs.txt
    echo -e "${NC}"
    echo ""
    
    echo -e "${PURPLE}=== AGENT 3: Highlight Sync (Issue #1) ===${NC}"
    echo -e "${BLUE}"
    cat .claude_prompts/agent-highlight-sync.txt
    echo -e "${NC}"
    echo ""
    
    echo -e "${GREEN}📋 Copy each prompt into a separate Claude session to start parallel development!${NC}"
}

# Main execution
main() {
    print_header
    
    case "${1:-}" in
        "setup-all")
            setup_all_current_issues
            ;;
        "create-prompts")
            create_claude_prompts
            ;;
        "add-labels")
            add_github_labels
            ;;
        "push")
            push_to_github
            ;;
        "full-setup")
            setup_all_current_issues
            create_claude_prompts
            add_github_labels
            push_to_github
            show_next_steps
            ;;
        "show-prompts")
            show_prompts
            ;;
        *)
            print_usage
            ;;
    esac
}

main "$@"