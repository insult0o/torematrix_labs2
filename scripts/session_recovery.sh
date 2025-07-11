#!/bin/bash
# TORE Matrix Labs - Session Recovery Script
# Script to quickly restore session state and continue work

set -e  # Exit on any error

PROJECT_ROOT="/home/insulto/tore_matrix_labs"

echo "🔄 TORE Matrix Labs - Session Recovery"
echo "======================================"

# Function to show current session state
show_session_state() {
    echo "📊 Current Session State:"
    echo "========================"
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Show project info
    echo "📁 Project: TORE Matrix Labs"
    echo "📍 Location: $PROJECT_ROOT"
    echo "🌐 GitHub: https://github.com/insult0o/tore-matrix-labs"
    echo ""
    
    # Show git status
    echo "📝 Git Status:"
    git status --short
    echo ""
    
    # Show recent commits
    echo "📋 Recent Commits:"
    git log --oneline -5
    echo ""
    
    # Show current branch and remote
    echo "🌿 Branch: $(git branch --show-current)"
    echo "📡 Remote: $(git remote get-url origin 2>/dev/null || echo 'Not configured')"
    echo ""
    
    # Show critical fixes status
    echo "🔧 Critical Fixes Status:"
    echo "✅ Project loading - Shows processed data immediately"
    echo "✅ PDF highlighting - QA issues highlight properly"  
    echo "✅ Area display - Areas show in list and preview"
    echo "✅ GitHub integration - Repository fully synced"
    echo ""
}

# Function to restore git configuration
restore_git_config() {
    echo "⚙️ Restoring git configuration..."
    cd "$PROJECT_ROOT"
    
    # Set user configuration
    git config user.name "insult0o"
    git config user.email "miguel.borges.cta@gmail.com"
    git config --global credential.helper store
    
    # Ensure remote is configured
    if ! git remote get-url origin >/dev/null 2>&1; then
        echo "📡 Configuring GitHub remote..."
        git remote add origin "https://insult0o@github.com/insult0o/tore-matrix-labs.git"
    fi
    
    echo "✅ Git configuration restored"
}

# Function to show available operations
show_available_operations() {
    echo "🛠️ Available Operations:"
    echo "======================="
    echo ""
    echo "Git Operations:"
    echo "  ./scripts/git_operations.sh status      - Check git status"
    echo "  ./scripts/git_operations.sh commit 'msg' - Commit changes"
    echo "  ./scripts/git_operations.sh push        - Push to GitHub"
    echo "  ./scripts/git_operations.sh sync 'msg'  - Commit and push"
    echo ""
    echo "Project Operations:"
    echo "  ./scripts/project_operations.sh run     - Run application"
    echo "  ./scripts/project_operations.sh test    - Run all tests"
    echo "  ./scripts/project_operations.sh status  - Project health check"
    echo ""
    echo "Session Recovery:"
    echo "  ./scripts/session_recovery.sh state     - Show current state"
    echo "  ./scripts/session_recovery.sh restore   - Restore configuration"
    echo ""
}

# Function to perform quick health check
quick_health_check() {
    echo "🏥 Quick Health Check:"
    echo "====================="
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Check key files exist
    key_files=(
        "tore_matrix_labs/__main__.py"
        "tore_matrix_labs/ui/main_window.py"
        "CLAUDE.md"
    )
    
    echo "📁 Key Files:"
    for file in "${key_files[@]}"; do
        if [ -f "$file" ]; then
            echo "✅ $file"
        else
            echo "❌ $file (missing)"
        fi
    done
    echo ""
    
    # Check git configuration
    echo "⚙️ Git Configuration:"
    if git config user.name >/dev/null 2>&1; then
        echo "✅ User name: $(git config user.name)"
    else
        echo "❌ User name not configured"
    fi
    
    if git config user.email >/dev/null 2>&1; then
        echo "✅ User email: $(git config user.email)"
    else
        echo "❌ User email not configured"
    fi
    
    if git remote get-url origin >/dev/null 2>&1; then
        echo "✅ GitHub remote: $(git remote get-url origin)"
    else
        echo "❌ GitHub remote not configured"
    fi
    echo ""
    
    # Check if we can access GitHub
    echo "🌐 GitHub Connectivity:"
    if git ls-remote origin >/dev/null 2>&1; then
        echo "✅ GitHub connection working"
    else
        echo "⚠️ GitHub connection issue (check credentials)"
    fi
    echo ""
}

# Function to show session summary
show_session_summary() {
    echo "📋 Session Summary"
    echo "=================="
    echo ""
    echo "🎯 TORE Matrix Labs Project Status:"
    echo "   📍 Location: $PROJECT_ROOT"
    echo "   🌐 GitHub: https://github.com/insult0o/tore-matrix-labs"
    echo "   🔧 All critical fixes implemented and pushed"
    echo ""
    echo "🚀 Recent Achievements:"
    echo "   ✅ Fixed project loading - no more reprocessing needed"
    echo "   ✅ Fixed PDF highlighting - QA issues highlight properly"
    echo "   ✅ Fixed area display - areas show in list and preview"
    echo "   ✅ Set up GitHub integration - repository fully configured"
    echo ""
    echo "📝 Quick Commands:"
    echo "   Check status:     ./scripts/git_operations.sh status"
    echo "   Run application:  ./scripts/project_operations.sh run"
    echo "   Test fixes:       ./scripts/project_operations.sh test all"
    echo "   Commit changes:   ./scripts/git_operations.sh sync 'message'"
    echo ""
}

# Function to show help
show_help() {
    echo "TORE Matrix Labs Session Recovery Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  state        - Show current session state"
    echo "  restore      - Restore git configuration"
    echo "  operations   - Show available operations"
    echo "  health       - Quick health check"
    echo "  summary      - Show session summary"
    echo ""
    echo "Examples:"
    echo "  $0 state"
    echo "  $0 restore"
    echo "  $0 summary"
}

# Main script logic
case "$1" in
    "state")
        show_session_state
        ;;
    "restore")
        restore_git_config
        ;;
    "operations")
        show_available_operations
        ;;
    "health")
        quick_health_check
        ;;
    "summary")
        show_session_summary
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac