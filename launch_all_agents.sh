#!/bin/bash

# TORE Matrix Labs - Launch All Agents Script
# Opens 4 terminal windows with each agent

echo "🚀 Launching 4 Parallel Development Agents..."

# Check if we're in the right directory
if [[ ! -d ".claude_sessions" ]]; then
    echo "❌ Please run this from the tore_matrix_labs directory"
    exit 1
fi

echo "📋 Agent Session Instructions:"
echo ""
echo "🤖 Agent 1 (Issue #4 - UI Areas List):"
echo "   cd .claude_sessions/agent-ui-areas-list && ./startup.sh"
echo ""
echo "🤖 Agent 2 (Issue #3 - Areas Display):"
echo "   cd .claude_sessions/agent-areas-display && ./startup.sh"
echo ""
echo "🤖 Agent 3 (Issue #2 - Multi Docs):"
echo "   cd .claude_sessions/agent-multi-docs && ./startup.sh"
echo ""
echo "🤖 Agent 4 (Issue #1 - Text Highlight):"
echo "   cd .claude_sessions/agent-text-highlight && ./startup.sh"
echo ""
echo "💡 To start working:"
echo "1. Open 4 separate Claude browser tabs"
echo "2. In each tab, run the respective agent command above"
echo "3. Each agent will automatically:"
echo "   - Create their working branch"
echo "   - Load their assigned GitHub issue"
echo "   - Start working independently"
echo ""
echo "📊 Monitor progress with:"
echo "   ./scripts/agent_coordinator.sh list-sessions"
echo "   ./scripts/github_issues.sh status"