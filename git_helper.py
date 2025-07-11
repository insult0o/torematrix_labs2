#!/usr/bin/env python3
"""
Simple Git Helper for TORE Matrix Labs
=====================================

This script provides easy Git operations for beginners.
All operations are safe and include confirmations.

Usage:
    python3 git_helper.py [command]

Commands:
    init        - Initialize Git repository (first time only)
    save        - Save current changes with a message
    backup      - Create backup branch and push to GitHub
    status      - Show current status
    history     - Show recent commits
    branches    - Show all branches
    switch      - Switch to a different branch
    new-feature - Create a new feature branch
    help        - Show this help message

Examples:
    python3 git_helper.py init
    python3 git_helper.py save "Added new PDF processing feature"
    python3 git_helper.py backup
    python3 git_helper.py new-feature "pdf-highlighting-improvements"
"""

import sys
import subprocess
import os
from datetime import datetime
from pathlib import Path


def run_command(cmd, capture_output=True, check=True):
    """Run a shell command safely."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode == 0, "", ""
    except subprocess.CalledProcessError as e:
        return False, "", str(e)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)


def print_success(message):
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print an error message."""
    print(f"❌ {message}")


def print_info(message):
    """Print an info message."""
    print(f"ℹ️  {message}")


def confirm_action(message):
    """Ask for user confirmation."""
    response = input(f"❓ {message} (y/N): ").strip().lower()
    return response in ['y', 'yes']


def init_repo():
    """Initialize Git repository."""
    print_section("Initializing Git Repository")
    
    # Check if already a Git repo
    success, _, _ = run_command("git status")
    if success:
        print_info("Repository is already initialized!")
        return True
    
    # Initialize Git
    success, output, error = run_command("git init")
    if not success:
        print_error(f"Failed to initialize Git: {error}")
        return False
    
    print_success("Git repository initialized")
    
    # Set up user name and email if not configured
    success, name, _ = run_command("git config user.name")
    if not success or not name:
        print_info("Setting up Git user configuration...")
        username = input("Enter your name for Git commits: ").strip()
        email = input("Enter your email for Git commits: ").strip()
        
        run_command(f'git config user.name "{username}"')
        run_command(f'git config user.email "{email}"')
        print_success("Git user configuration set")
    
    # Initial commit
    if confirm_action("Create initial commit with current files?"):
        success, _, error = run_command("git add .")
        if success:
            success, _, error = run_command('git commit -m "Initial commit - TORE Matrix Labs base"')
            if success:
                print_success("Initial commit created")
            else:
                print_error(f"Failed to create initial commit: {error}")
        else:
            print_error(f"Failed to add files: {error}")
    
    return True


def save_changes():
    """Save current changes with a commit message."""
    print_section("Saving Changes")
    
    # Check status
    success, status, _ = run_command("git status --porcelain")
    if not success:
        print_error("Failed to check Git status")
        return False
    
    if not status.strip():
        print_info("No changes to save!")
        return True
    
    # Show status
    print("📋 Current changes:")
    run_command("git status --short", capture_output=False)
    
    # Get commit message
    print("\n💬 Enter a commit message describing your changes:")
    print("   Examples:")
    print("   - 'Fixed PDF highlighting bug'")
    print("   - 'Added new area selection feature'")
    print("   - 'Improved error handling in validation'")
    
    message = input("\nCommit message: ").strip()
    if not message:
        message = f"Auto-save: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        print_info(f"Using auto-generated message: {message}")
    
    # Confirm changes
    if not confirm_action("Save these changes?"):
        print_info("Save cancelled")
        return False
    
    # Add and commit
    success, _, error = run_command("git add .")
    if not success:
        print_error(f"Failed to stage changes: {error}")
        return False
    
    success, _, error = run_command(f'git commit -m "{message}"')
    if not success:
        print_error(f"Failed to commit changes: {error}")
        return False
    
    print_success(f"Changes saved: {message}")
    return True


def backup_to_github():
    """Create backup and push to GitHub."""
    print_section("Creating Backup")
    
    # Get current branch
    success, current_branch, _ = run_command("git branch --show-current")
    if not success:
        print_error("Failed to get current branch")
        return False
    
    print_info(f"Current branch: {current_branch}")
    
    # Check for remote
    success, remotes, _ = run_command("git remote -v")
    if not success or not remotes:
        print_info("No GitHub remote configured yet.")
        print_info("To set up GitHub:")
        print_info("1. Create a repository on GitHub")
        print_info("2. Run: git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git")
        return False
    
    # Create backup branch
    backup_branch = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    if confirm_action(f"Create backup branch '{backup_branch}' and push to GitHub?"):
        # Create backup branch
        success, _, error = run_command(f"git checkout -b {backup_branch}")
        if not success:
            print_error(f"Failed to create backup branch: {error}")
            return False
        
        # Push to GitHub
        success, _, error = run_command(f"git push -u origin {backup_branch}")
        if not success:
            print_error(f"Failed to push to GitHub: {error}")
            print_info("Make sure you have:")
            print_info("1. Created the repository on GitHub")
            print_info("2. Added the remote: git remote add origin <URL>")
            print_info("3. Have proper authentication set up")
            return False
        
        print_success(f"Backup created and pushed: {backup_branch}")
        
        # Switch back to original branch
        run_command(f"git checkout {current_branch}")
        print_info(f"Switched back to {current_branch}")
        
        return True
    
    return False


def show_status():
    """Show current Git status."""
    print_section("Repository Status")
    
    # Current branch
    success, branch, _ = run_command("git branch --show-current")
    if success:
        print_info(f"Current branch: {branch}")
    
    # Status
    print("\n📋 Working directory status:")
    run_command("git status", capture_output=False)
    
    # Recent commits
    print("\n📚 Recent commits:")
    run_command("git log --oneline -5", capture_output=False)


def show_history():
    """Show commit history."""
    print_section("Commit History")
    run_command("git log --oneline --graph -10", capture_output=False)


def show_branches():
    """Show all branches."""
    print_section("Branches")
    
    print("📍 Local branches:")
    run_command("git branch", capture_output=False)
    
    print("\n🌐 Remote branches:")
    run_command("git branch -r", capture_output=False)


def switch_branch():
    """Switch to a different branch."""
    print_section("Switch Branch")
    
    # Show available branches
    print("📍 Available branches:")
    run_command("git branch", capture_output=False)
    
    branch_name = input("\nEnter branch name to switch to: ").strip()
    if not branch_name:
        print_info("No branch specified")
        return False
    
    success, _, error = run_command(f"git checkout {branch_name}")
    if success:
        print_success(f"Switched to branch: {branch_name}")
        return True
    else:
        print_error(f"Failed to switch branch: {error}")
        return False


def create_feature_branch():
    """Create a new feature branch."""
    print_section("Create Feature Branch")
    
    print("🌿 Creating a new feature branch allows you to work on")
    print("   new features without affecting the main code.")
    
    feature_name = input("\nEnter feature name (e.g., 'pdf-improvements'): ").strip()
    if not feature_name:
        print_info("No feature name provided")
        return False
    
    # Clean up feature name
    feature_name = feature_name.lower().replace(' ', '-').replace('_', '-')
    branch_name = f"feature/{feature_name}"
    
    print_info(f"Creating branch: {branch_name}")
    
    if confirm_action(f"Create and switch to branch '{branch_name}'?"):
        success, _, error = run_command(f"git checkout -b {branch_name}")
        if success:
            print_success(f"Created and switched to branch: {branch_name}")
            print_info("You can now work on your feature. When done, use 'save' to commit changes.")
            return True
        else:
            print_error(f"Failed to create branch: {error}")
            return False
    
    return False


def show_help():
    """Show help message."""
    print(__doc__)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🚀 TORE Matrix Labs Git Helper")
        print("==============================")
        print("\nAvailable commands:")
        print("  init        - Initialize Git repository")
        print("  save        - Save current changes")
        print("  backup      - Create backup and push to GitHub")
        print("  status      - Show current status")
        print("  history     - Show commit history")
        print("  branches    - Show all branches")
        print("  switch      - Switch to different branch")
        print("  new-feature - Create new feature branch")
        print("  help        - Show detailed help")
        print("\nUsage: python3 git_helper.py [command]")
        return
    
    command = sys.argv[1].lower()
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Command routing
    if command == "init":
        init_repo()
    elif command == "save":
        save_changes()
    elif command == "backup":
        backup_to_github()
    elif command == "status":
        show_status()
    elif command == "history":
        show_history()
    elif command == "branches":
        show_branches()
    elif command == "switch":
        switch_branch()
    elif command == "new-feature":
        create_feature_branch()
    elif command == "help":
        show_help()
    else:
        print_error(f"Unknown command: {command}")
        print_info("Use 'python3 git_helper.py help' for available commands")


if __name__ == "__main__":
    main()