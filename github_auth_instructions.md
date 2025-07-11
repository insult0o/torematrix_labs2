# GitHub Authentication Instructions

## Option 1: Personal Access Token (Recommended)

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: `TORE Matrix Labs`
4. Scopes: Check `repo` (Full control of private repositories)
5. Click "Generate token"
6. Copy the token

Then run:
```bash
# When prompted for username, enter: insult0o
# When prompted for password, enter: YOUR_PERSONAL_ACCESS_TOKEN

git push -u origin master
```

## Option 2: SSH Key (Alternative)

1. Generate SSH key:
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

2. Add to GitHub: Settings → SSH and GPG keys → New SSH key

3. Change remote to SSH:
```bash
git remote set-url origin git@github.com:insult0o/tore-matrix-labs.git
git push -u origin master
```

## What Will Be Pushed

Your GitHub repository will contain:
- ✅ All critical fixes (project loading, PDF highlighting, area display)
- ✅ Complete commit history with professional messages
- ✅ Clean codebase with proper .gitignore
- ✅ Full TORE Matrix Labs source code
- ✅ Documentation and configuration files

## Commit History That Will Be Pushed:
- c406363: 🔧 Prepare for GitHub: Update .gitignore and final cleanup
- 843b067: 🔧 CRITICAL FIX: Areas now display in list and preview sections  
- 6240a02: 🔧 CRITICAL FIX: PDF highlighting now works properly
- e06d8e3: 🔧 CRITICAL FIX: Project loading now shows processed data immediately
- a44a1cd: Fix critical session reload and validation UI freeze bugs
- db6e32e: Implement advanced highlighting system architecture
- (and all previous commits...)