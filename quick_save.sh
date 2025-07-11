#!/bin/bash
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
        echo "ℹ️  Make sure you've set up the GitHub remote:"
        echo "    git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git"
    fi
fi