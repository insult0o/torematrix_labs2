# TORE Matrix Labs - Parallel Development with Multiple Claude Agents

## 🚀 Overview

This guide explains how to use GitHub Issues and multiple Claude agent sessions to work on several problems simultaneously, enabling efficient parallel development.

## 🎯 Core Concept

Instead of fixing issues one by one, you can:
1. **Create multiple GitHub issues** for different problems
2. **Assign each issue** to a separate Claude agent session  
3. **Work in parallel** on multiple fixes simultaneously
4. **Coordinate** through GitHub Issues and pull requests

## 🔧 Quick Start

### Step 1: Create Issues for Your Problems

```bash
# Create a bug report
./scripts/github_issues.sh create-bug

# Create a feature request  
./scripts/github_issues.sh create-feature

# Create code improvement issue
./scripts/github_issues.sh create-improve

# Or create multiple related issues at once
./scripts/github_issues.sh create-parallel "PDF Viewer Improvements"
```

### Step 2: Assign Issues to Different Claude Agents

```bash
# Assign issue #123 to an agent named "agent-ui-fixes"
./scripts/github_issues.sh assign-agent 123 agent-ui-fixes

# Assign issue #124 to another agent  
./scripts/github_issues.sh assign-agent 124 agent-pdf-viewer

# Assign issue #125 to a third agent
./scripts/github_issues.sh assign-agent 125 agent-performance
```

### Step 3: Open Multiple Claude Sessions

1. **Session 1**: Load agent "agent-ui-fixes" 
   - Works on UI-related issues
   - Focuses on layout and styling problems

2. **Session 2**: Load agent "agent-pdf-viewer"
   - Works on PDF viewer functionality
   - Fixes highlighting and navigation issues

3. **Session 3**: Load agent "agent-performance"  
   - Works on performance optimizations
   - Improves memory usage and speed

### Step 4: Monitor Progress

```bash
# Check status of all parallel development
./scripts/github_issues.sh status

# List all open issues
./scripts/github_issues.sh list-issues

# Sync issue states
./scripts/github_issues.sh sync
```

## 📋 Detailed Workflow

### Creating Issues Efficiently

#### Option A: Individual Issues
Create specific issues for each problem:

```bash
# UI Layout Problem
./scripts/github_issues.sh create-bug
# Title: "Areas not displaying in list widget"
# Component: manual-validation  
# Severity: high

# PDF Highlighting Problem  
./scripts/github_issues.sh create-bug
# Title: "PDF highlights not showing for QA issues"
# Component: qa-validation
# Severity: high

# Performance Problem
./scripts/github_issues.sh create-improve
# Title: "Optimize document loading performance"
# Files: document_processor.py
# Type: performance
```

#### Option B: Parallel Issue Groups
Create multiple related issues automatically:

```bash
# Creates 6 related issues for PDF viewer improvements
./scripts/github_issues.sh create-parallel "PDF Viewer Improvements"

# Creates issues for:
# - UI Components (layout, styling)
# - Backend Logic (processing)  
# - Error Handling (robustness)
# - Testing (quality assurance)
# - Documentation (guides)
# - Performance (optimization)
```

### Agent Assignment Strategy

#### Approach 1: By Component
```bash
./scripts/github_issues.sh assign-agent 101 agent-ui          # UI issues
./scripts/github_issues.sh assign-agent 102 agent-pdf        # PDF issues  
./scripts/github_issues.sh assign-agent 103 agent-backend    # Core logic
./scripts/github_issues.sh assign-agent 104 agent-qa         # QA/Testing
```

#### Approach 2: By Complexity
```bash
./scripts/github_issues.sh assign-agent 105 agent-simple     # Simple fixes
./scripts/github_issues.sh assign-agent 106 agent-medium     # Medium complexity
./scripts/github_issues.sh assign-agent 107 agent-complex    # Complex features
```

#### Approach 3: By Priority  
```bash
./scripts/github_issues.sh assign-agent 108 agent-critical   # Critical bugs
./scripts/github_issues.sh assign-agent 109 agent-features   # New features
./scripts/github_issues.sh assign-agent 110 agent-polish     # Improvements
```

## 🤖 Claude Agent Instructions

When you start a new Claude session for parallel development:

### For the Human User:
1. **Start new Claude session** with a descriptive name (e.g., "agent-ui-fixes")
2. **Load the assignment**: Look in `.claude_agents/agent-name_assignment.md`
3. **Give Claude the context**: "You are agent-ui-fixes working on issue #123. See assignment file for details."

### For Claude Agents:
Each agent should follow this workflow:

```bash
# 1. Check your assignment
cat .claude_agents/your-agent-name_assignment.md

# 2. View your assigned issue
gh issue view <issue_number> --repo insult0o/tore-matrix-labs

# 3. Create working branch
git checkout -b issue-<number>-<agent-name>

# 4. Check project status
./scripts/project_operations.sh status

# 5. Work on the issue
# ... implement solution ...

# 6. Test your changes
./scripts/project_operations.sh test

# 7. Commit and push
git add .
git commit -m "Fix issue #<number>: <description>"
git push -u origin issue-<number>-<agent-name>

# 8. Create pull request
gh pr create --title "Fix #<number>: <description>" --body "Fixes #<number>"

# 9. Update issue with progress
gh issue comment <number> --body "✅ Solution implemented in PR #<pr_number>"
```

## 📊 Coordination & Communication

### Progress Tracking
- **Issues**: Track individual problems and solutions
- **Pull Requests**: Review code changes before merging  
- **Comments**: Communicate progress and blockers
- **Labels**: Organize by component, priority, complexity

### Avoiding Conflicts
- **Separate branches**: Each agent works on own branch
- **File coordination**: Avoid multiple agents editing same files
- **Communication**: Use issue comments for coordination
- **Testing**: Run tests before creating pull requests

### Example Coordination
```bash
# Agent 1 working on UI files
git checkout -b issue-123-agent-ui-fixes
# Modifies: manual_validation_widget.py, main_window.py

# Agent 2 working on PDF files  
git checkout -b issue-124-agent-pdf-viewer
# Modifies: pdf_viewer.py, highlighting_engine.py

# Agent 3 working on backend files
git checkout -b issue-125-agent-backend
# Modifies: document_processor.py, quality_assessor.py
```

## 🎯 Real-World Example

### Scenario: You have 5 problems in TORE Matrix Labs

1. **Areas not showing in UI** (critical bug)
2. **PDF highlighting broken** (high priority bug)  
3. **Slow document loading** (performance issue)
4. **Missing error messages** (usability improvement)
5. **Add export feature** (new feature request)

### Parallel Solution:

```bash
# Create all issues
./scripts/github_issues.sh create-bug      # Issue #201: Areas not showing
./scripts/github_issues.sh create-bug      # Issue #202: PDF highlighting  
./scripts/github_issues.sh create-improve  # Issue #203: Slow loading
./scripts/github_issues.sh create-improve  # Issue #204: Error messages
./scripts/github_issues.sh create-feature  # Issue #205: Export feature

# Assign to 5 different agents
./scripts/github_issues.sh assign-agent 201 agent-ui-critical
./scripts/github_issues.sh assign-agent 202 agent-pdf-fixes  
./scripts/github_issues.sh assign-agent 203 agent-performance
./scripts/github_issues.sh assign-agent 204 agent-usability
./scripts/github_issues.sh assign-agent 205 agent-features

# Open 5 Claude sessions simultaneously:
# Session 1: "agent-ui-critical" works on areas display
# Session 2: "agent-pdf-fixes" works on PDF highlighting
# Session 3: "agent-performance" works on loading speed  
# Session 4: "agent-usability" works on error messages
# Session 5: "agent-features" works on export functionality

# Result: All 5 problems get solved in parallel!
```

### Benefits:
- ✅ **5x faster development** - All issues worked on simultaneously
- ✅ **No blocking** - Agents work independently  
- ✅ **Clear organization** - Each issue has dedicated focus
- ✅ **Easy tracking** - Progress visible in GitHub Issues
- ✅ **Professional workflow** - Industry-standard practices

## 🔍 Monitoring & Management

### Check Overall Status
```bash
./scripts/github_issues.sh status
```

Shows:
- Active parallel development issues
- Agent assignments  
- Progress summary
- Next steps

### View All Issues
```bash
./scripts/github_issues.sh list-issues
```

### Update Status
```bash
./scripts/github_issues.sh sync
```

## 🚀 Advanced Patterns

### Pattern 1: Component-Based Parallel Development
Split work by application component:
- **Agent A**: Manual Validation Widget issues
- **Agent B**: QA Validation Widget issues  
- **Agent C**: PDF Viewer issues
- **Agent D**: Project Manager issues

### Pattern 2: Feature-Based Parallel Development  
Split large features into parallel sub-features:
- **Agent A**: UI design and layout
- **Agent B**: Backend processing logic
- **Agent C**: Data persistence and storage
- **Agent D**: Testing and validation

### Pattern 3: Priority-Based Parallel Development
Split by urgency and impact:
- **Agent A**: Critical bugs (blocking)
- **Agent B**: High priority features  
- **Agent C**: Performance optimizations
- **Agent D**: Code quality improvements

## 🎉 Success Metrics

With parallel development, you can achieve:

- **Multiple issues solved simultaneously** instead of sequentially
- **Faster time-to-resolution** for critical problems
- **Better code organization** through focused branches
- **Professional development workflow** using industry standards
- **Clear progress tracking** and accountability
- **Reduced context switching** - each agent focuses on one area

## 📚 Quick Reference

### Essential Commands
```bash
# Create issues
./scripts/github_issues.sh create-bug
./scripts/github_issues.sh create-feature  
./scripts/github_issues.sh create-parallel "Topic Name"

# Assign agents
./scripts/github_issues.sh assign-agent <issue#> <agent-name>

# Monitor progress
./scripts/github_issues.sh status
./scripts/github_issues.sh list-issues

# Sync state
./scripts/github_issues.sh sync
```

### File Locations
- **Issue Templates**: `.github/ISSUE_TEMPLATE/`
- **Agent Assignments**: `.claude_agents/`
- **Issue Tracking**: `.github_issues/`
- **Scripts**: `scripts/github_issues.sh`

---

**Result**: Transform chaotic bug-fixing into organized, parallel development that scales with your team and gets results faster! 🚀