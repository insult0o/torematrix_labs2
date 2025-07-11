#!/bin/bash
# TORE Matrix Labs - Git Operations Script
# Comprehensive script for all git operations with GitHub

set -e  # Exit on any error

PROJECT_ROOT="/home/insulto/tore_matrix_labs"
GITHUB_REPO="https://github.com/insult0o/tore-matrix-labs.git"
GITHUB_USER="insult0o"
USER_EMAIL="miguel.borges.cta@gmail.com"

echo "🚀 TORE Matrix Labs - Git Operations"
echo "====================================="

# Function to setup git configuration
setup_git_config() {
    echo "⚙️ Setting up git configuration..."
    cd "$PROJECT_ROOT"
    git config user.name "$GITHUB_USER"
    git config user.email "$USER_EMAIL"
    git config --global credential.helper store
    echo "✅ Git configuration complete"
}

# Function to setup GitHub remote
setup_github_remote() {
    echo "📡 Setting up GitHub remote..."
    cd "$PROJECT_ROOT"
    
    # Remove existing remote if it exists
    git remote remove origin 2>/dev/null || true
    
    # Add GitHub remote with username
    git remote add origin "https://${GITHUB_USER}@github.com/${GITHUB_USER}/tore-matrix-labs.git"
    
    echo "✅ GitHub remote configured"
    git remote -v
}

# Function to check git status
check_status() {
    echo "📊 Checking git status..."
    cd "$PROJECT_ROOT"
    git status
    echo ""
    echo "📝 Recent commits:"
    git log --oneline -5
}

# Function to stage and commit changes
commit_changes() {
    local commit_message="$1"
    
    if [ -z "$commit_message" ]; then
        echo "❌ Error: Commit message required"
        echo "Usage: $0 commit 'Your commit message'"
        exit 1
    fi
    
    echo "📝 Staging and committing changes..."
    cd "$PROJECT_ROOT"
    
    # Add all changes except excluded files
    git add .
    
    # Create commit with Claude Code attribution
    git commit -m "$(cat <<EOF
$commit_message

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
    
    echo "✅ Changes committed successfully"
}

# Function to push to GitHub
push_to_github() {
    echo "⬆️ Pushing to GitHub..."
    cd "$PROJECT_ROOT"
    
    # Check if we have commits to push
    if git diff --quiet origin/master..HEAD 2>/dev/null; then
        echo "ℹ️ No new commits to push"
        return 0
    fi
    
    echo "📦 Commits to be pushed:"
    git log --oneline origin/master..HEAD 2>/dev/null || git log --oneline -3
    
    echo ""
    echo "🚀 Pushing to GitHub..."
    git push origin master
    
    echo "✅ Successfully pushed to GitHub!"
    echo "🔗 View at: $GITHUB_REPO"
}

# Function to pull from GitHub
pull_from_github() {
    echo "⬇️ Pulling from GitHub..."
    cd "$PROJECT_ROOT"
    git pull origin master
    echo "✅ Successfully pulled from GitHub"
}

# Function to show help
show_help() {
    echo "TORE Matrix Labs Git Operations Script"
    echo ""
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  setup-config     - Setup git configuration and credentials"
    echo "  setup-remote     - Setup GitHub remote repository"
    echo "  status          - Show git status and recent commits"
    echo "  commit <msg>    - Stage all changes and commit with message"
    echo "  push            - Push commits to GitHub"
    echo "  pull            - Pull latest changes from GitHub"
    echo "  sync <msg>      - Commit changes and push to GitHub"
    echo "  full-setup      - Complete setup (config + remote)"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 commit 'Fix critical bug in area display'"
    echo "  $0 push"
    echo "  $0 sync 'Update documentation and fix bugs'"
}

# Function to sync (commit + push)
sync_with_github() {
    local commit_message="$1"
    
    if [ -z "$commit_message" ]; then
        echo "❌ Error: Commit message required for sync"
        echo "Usage: $0 sync 'Your commit message'"
        exit 1
    fi
    
    echo "🔄 Syncing with GitHub..."
    commit_changes "$commit_message"
    push_to_github
    echo "✅ Sync complete!"
}

# Function to do full setup
full_setup() {
    echo "🚀 Performing full GitHub setup..."
    setup_git_config
    setup_github_remote
    echo "✅ Full setup complete!"
}

# Main script logic
case "$1" in
    "setup-config")
        setup_git_config
        ;;
    "setup-remote")
        setup_github_remote
        ;;
    "status")
        check_status
        ;;
    "commit")
        commit_changes "$2"
        ;;
    "push")
        push_to_github
        ;;
    "pull")
        pull_from_github
        ;;
    "sync")
        sync_with_github "$2"
        ;;
    "full-setup")
        full_setup
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