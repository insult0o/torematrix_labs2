#!/bin/bash
# Script to push TORE Matrix Labs to GitHub
# Run this after setting up your Personal Access Token

echo "🚀 PUSHING TORE MATRIX LABS TO GITHUB"
echo "======================================"
echo ""
echo "📋 Repository: https://github.com/insult0o/tore-matrix-labs"
echo "📊 Ready to push all commits with critical fixes!"
echo ""
echo "🔐 When prompted for password, enter your Personal Access Token"
echo ""

# Show what will be pushed
echo "📦 Commits to be pushed:"
git log --oneline origin/master..HEAD 2>/dev/null || git log --oneline -10

echo ""
echo "⬆️ Pushing to GitHub..."

# Push with upstream tracking (include username in URL to avoid username prompt)
git push -u https://insult0o@github.com/insult0o/tore-matrix-labs.git master

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! TORE Matrix Labs is now on GitHub!"
    echo ""
    echo "🌟 Your repository includes:"
    echo "   ✅ All critical fixes we implemented"
    echo "   ✅ Professional commit messages"
    echo "   ✅ Clean codebase with proper .gitignore"
    echo "   ✅ Complete documentation"
    echo ""
    echo "🔗 View your repository at:"
    echo "   https://github.com/insult0o/tore-matrix-labs"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Add a description to your GitHub repository"
    echo "   2. Add topics/tags for discoverability"
    echo "   3. Consider adding a detailed README with screenshots"
else
    echo ""
    echo "❌ Push failed. Please check your authentication."
    echo "💡 Make sure you're using your Personal Access Token as the password"
fi