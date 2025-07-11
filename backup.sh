#!/bin/bash
# Backup Script for TORE Matrix Labs
echo "💾 Backup - TORE Matrix Labs"
echo "============================"

# Create backup branch
backup_name="backup-$(date '+%Y%m%d-%H%M%S')"
echo "ℹ️  Creating backup branch: $backup_name"

git checkout -b "$backup_name"

# Push to GitHub if remote exists
if git remote | grep -q "origin"; then
    git push -u origin "$backup_name"
    
    if [ $? -eq 0 ]; then
        echo "✅ Backup created and pushed: $backup_name"
    else
        echo "❌ Backup push failed! (backup branch created locally)"
    fi
else
    echo "ℹ️  Backup branch created locally: $backup_name"
    echo "ℹ️  Set up GitHub remote to enable cloud backups:"
    echo "    git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git"
fi

# Switch back to main
git checkout master
echo "ℹ️  Switched back to master branch"