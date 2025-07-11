#!/usr/bin/env python3
"""
Automatic Git Setup for TORE Matrix Labs
========================================

This script automatically sets up Git and GitHub for your project.
It's designed for beginners and handles everything automatically.

Usage:
    python3 setup_git.py
"""

import subprocess
import os
import sys
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


def print_step(step, message):
    """Print a numbered step."""
    print(f"\n🔧 Step {step}: {message}")
    print("-" * 50)


def print_success(message):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print error message."""
    print(f"❌ {message}")


def print_info(message):
    """Print info message."""
    print(f"ℹ️  {message}")


def confirm_action(message):
    """Ask for confirmation."""
    response = input(f"❓ {message} (y/N): ").strip().lower()
    return response in ['y', 'yes']


def setup_git_config():
    """Set up Git user configuration."""
    print_step(1, "Setting up Git Configuration")
    
    # Check if already configured
    success, name, _ = run_command("git config --global user.name")
    success2, email, _ = run_command("git config --global user.email")
    
    if success and success2 and name and email:
        print_success(f"Git already configured:")
        print_info(f"  Name: {name}")
        print_info(f"  Email: {email}")
        
        if not confirm_action("Reconfigure Git user settings?"):
            return True
    
    print_info("Setting up your Git identity...")
    print_info("This information will appear in your commits.")
    
    while True:
        username = input("Enter your full name: ").strip()
        if username:
            break
        print_error("Name cannot be empty!")
    
    while True:
        email = input("Enter your email address: ").strip()
        if email and "@" in email:
            break
        print_error("Please enter a valid email address!")
    
    # Set global Git config
    success1, _, error1 = run_command(f'git config --global user.name "{username}"')
    success2, _, error2 = run_command(f'git config --global user.email "{email}"')
    
    if success1 and success2:
        print_success("Git configuration completed!")
        return True
    else:
        print_error(f"Configuration failed: {error1} {error2}")
        return False


def initialize_repository():
    """Initialize the Git repository."""
    print_step(2, "Initializing Git Repository")
    
    # Check if already a Git repo
    success, _, _ = run_command("git status")
    if success:
        print_success("Repository already initialized!")
        return True
    
    # Initialize
    success, _, error = run_command("git init")
    if not success:
        print_error(f"Failed to initialize repository: {error}")
        return False
    
    print_success("Git repository initialized!")
    
    # Set default branch to main
    run_command("git branch -M main")
    print_info("Default branch set to 'main'")
    
    return True


def create_initial_commit():
    """Create the initial commit."""
    print_step(3, "Creating Initial Commit")
    
    # Check if there are already commits
    success, _, _ = run_command("git log --oneline -1")
    if success:
        print_success("Repository already has commits!")
        return True
    
    print_info("Adding all project files to Git...")
    
    # Add all files
    success, _, error = run_command("git add .")
    if not success:
        print_error(f"Failed to add files: {error}")
        return False
    
    # Show what will be committed
    print_info("Files to be committed:")
    run_command("git status --short", capture_output=False)
    
    if not confirm_action("Create initial commit with these files?"):
        print_info("Skipping initial commit")
        return True
    
    # Create initial commit
    commit_message = "🚀 Initial commit - TORE Matrix Labs Enhanced V1"
    success, _, error = run_command(f'git commit -m "{commit_message}"')
    
    if success:
        print_success("Initial commit created!")
        return True
    else:
        print_error(f"Failed to create commit: {error}")
        return False


def setup_github_instructions():
    """Provide GitHub setup instructions."""
    print_step(4, "GitHub Setup Instructions")
    
    print_info("To complete the setup, you need to:")
    print("")
    print("1. 🌐 Go to https://github.com")
    print("2. 📝 Create a new repository")
    print("3. 📛 Name it: 'tore-matrix-labs' (or your preferred name)")
    print("4. 🔒 Make it Private (recommended) or Public")
    print("5. ❌ Don't initialize with README (we already have files)")
    print("")
    print("After creating the repository on GitHub:")
    print("")
    
    # Get the current project directory name
    project_name = Path.cwd().name.replace("_", "-")
    
    print("6. 🔗 Connect your local repository to GitHub:")
    print(f"   git remote add origin https://github.com/YOUR_USERNAME/{project_name}.git")
    print("")
    print("7. 📤 Push your code to GitHub:")
    print("   git push -u origin main")
    print("")
    
    print_info("Replace 'YOUR_USERNAME' with your actual GitHub username!")
    print("")
    
    if confirm_action("Have you created the GitHub repository?"):
        username = input("Enter your GitHub username: ").strip()
        repo_name = input(f"Enter repository name (default: {project_name}): ").strip() or project_name
        
        github_url = f"https://github.com/{username}/{repo_name}.git"
        
        print_info(f"Setting up remote: {github_url}")
        
        # Add remote
        success, _, error = run_command(f"git remote add origin {github_url}")
        if success:
            print_success("GitHub remote added!")
            
            # Try to push
            if confirm_action("Push code to GitHub now?"):
                print_info("Pushing to GitHub...")
                success, _, error = run_command("git push -u origin main")
                if success:
                    print_success("Code pushed to GitHub successfully!")
                    print_info(f"Your repository is now available at: https://github.com/{username}/{repo_name}")
                else:
                    print_error(f"Push failed: {error}")
                    print_info("You may need to authenticate with GitHub")
                    print_info("Try: git push -u origin main")
        else:
            if "already exists" in error:
                print_info("Remote already exists")
            else:
                print_error(f"Failed to add remote: {error}")
    
    return True


def create_automation_scripts():
    """Create helpful automation scripts."""
    print_step(5, "Creating Automation Scripts")
    
    # Create quick save script
    save_script = """#!/bin/bash
# Quick Save Script for TORE Matrix Labs
echo "🔄 Quick Save - TORE Matrix Labs"
echo "================================="

# Check for changes
if [ -z "$(git status --porcelain)" ]; then
    echo "ℹ️  No changes to save!"
    exit 0
fi

# Show changes
echo "📋 Changes to save:"
git status --short

# Get commit message
echo ""
read -p "💬 Enter commit message (or press Enter for auto-message): " message

if [ -z "$message" ]; then
    message="Auto-save: $(date '+%Y-%m-%d %H:%M')"
    echo "ℹ️  Using auto-message: $message"
fi

# Save changes
git add .
git commit -m "$message"

if [ $? -eq 0 ]; then
    echo "✅ Changes saved successfully!"
else
    echo "❌ Save failed!"
    exit 1
fi

# Ask about GitHub push
echo ""
read -p "❓ Push to GitHub? (y/N): " push_choice
if [[ $push_choice =~ ^[Yy]$ ]]; then
    git push
    if [ $? -eq 0 ]; then
        echo "✅ Pushed to GitHub!"
    else
        echo "❌ Push to GitHub failed!"
    fi
fi
"""
    
    with open("quick_save.sh", "w") as f:
        f.write(save_script)
    
    # Make executable
    os.chmod("quick_save.sh", 0o755)
    print_success("Created quick_save.sh script")
    
    # Create backup script
    backup_script = """#!/bin/bash
# Backup Script for TORE Matrix Labs
echo "💾 Backup - TORE Matrix Labs"
echo "============================"

# Create backup branch
backup_name="backup-$(date '+%Y%m%d-%H%M%S')"
echo "ℹ️  Creating backup branch: $backup_name"

git checkout -b "$backup_name"
git push -u origin "$backup_name"

if [ $? -eq 0 ]; then
    echo "✅ Backup created and pushed: $backup_name"
    
    # Switch back to main
    git checkout main
    echo "ℹ️  Switched back to main branch"
else
    echo "❌ Backup failed!"
    git checkout main
fi
"""
    
    with open("backup.sh", "w") as f:
        f.write(backup_script)
    
    os.chmod("backup.sh", 0o755)
    print_success("Created backup.sh script")
    
    print_info("You can now use:")
    print_info("  ./quick_save.sh  - Quick save with commit")
    print_info("  ./backup.sh      - Create backup branch")
    print_info("  python3 git_helper.py - Full Git helper")
    
    return True


def show_final_instructions():
    """Show final usage instructions."""
    print("")
    print("🎉 Git Setup Complete!")
    print("=" * 50)
    print("")
    print("📚 How to use Git with your project:")
    print("")
    print("🔧 Daily workflow:")
    print("  1. Make changes to your code")
    print("  2. Run: ./quick_save.sh")
    print("  3. Enter a message describing your changes")
    print("  4. Choose whether to push to GitHub")
    print("")
    print("💾 For backups:")
    print("  ./backup.sh  - Creates timestamped backup")
    print("")
    print("🔍 For advanced operations:")
    print("  python3 git_helper.py status      - Check status")
    print("  python3 git_helper.py history     - View history")
    print("  python3 git_helper.py new-feature - Create feature branch")
    print("  python3 git_helper.py help        - Full help")
    print("")
    print("🚨 Emergency recovery:")
    print("  If something goes wrong, your code is safely backed up!")
    print("  Use 'python3 git_helper.py branches' to see all backups")
    print("")
    print("🔗 GitHub benefits:")
    print("  ✅ Automatic cloud backup")
    print("  ✅ Version history and recovery")
    print("  ✅ Share with collaborators")
    print("  ✅ Track all changes safely")


def main():
    """Main setup function."""
    print("🚀 TORE Matrix Labs - Git Setup")
    print("=" * 40)
    print("")
    print("This script will set up Git version control for your project.")
    print("It's safe and you can stop at any time with Ctrl+C.")
    print("")
    
    if not confirm_action("Continue with Git setup?"):
        print_info("Setup cancelled")
        return
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print_info(f"Working in: {project_dir}")
    
    # Run setup steps
    steps = [
        setup_git_config,
        initialize_repository,
        create_initial_commit,
        setup_github_instructions,
        create_automation_scripts
    ]
    
    for step_func in steps:
        if not step_func():
            print_error("Setup failed! You can run this script again to retry.")
            return
    
    show_final_instructions()
    print_success("Git setup completed successfully! 🎉")


if __name__ == "__main__":
    main()