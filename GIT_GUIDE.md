# 🚀 Git Guide for TORE Matrix Labs

This guide explains how to use Git version control for your TORE Matrix Labs project. Everything is designed to be simple and automatic!

## 🔧 Quick Setup (First Time Only)

1. **Run the setup script:**
   ```bash
   python3 setup_git.py
   ```

2. **Follow the prompts** - the script will:
   - Configure Git with your name/email
   - Initialize the repository
   - Create initial commit
   - Guide you through GitHub setup
   - Create automation scripts

## 📅 Daily Workflow

### Save Your Work (Most Common)
```bash
./quick_save.sh
```
- Automatically saves all your changes
- Asks for a description of what you changed
- Optionally pushes to GitHub for backup

### Check What Changed
```bash
python3 git_helper.py status
```
- Shows what files you've modified
- Shows recent commits

### Create Backup
```bash
./backup.sh
```
- Creates a timestamped backup branch
- Pushes it to GitHub automatically
- Keeps your main work safe

## 🌿 Working on New Features

### Start a New Feature
```bash
python3 git_helper.py new-feature "pdf-improvements"
```
- Creates a separate branch for your feature
- Lets you experiment safely
- Won't affect your main code

### Switch Between Branches
```bash
python3 git_helper.py branches  # See all branches
python3 git_helper.py switch    # Switch to different branch
```

## 📚 Useful Commands

| Command | What It Does |
|---------|--------------|
| `./quick_save.sh` | Save all changes with a message |
| `./backup.sh` | Create timestamped backup |
| `python3 git_helper.py status` | Check current status |
| `python3 git_helper.py history` | See recent changes |
| `python3 git_helper.py branches` | List all branches |
| `python3 git_helper.py help` | Show all available commands |

## 🔒 Safety Features

- **Nothing is ever lost** - Git keeps everything
- **Multiple backups** - Local + GitHub + backup branches
- **Easy recovery** - Can undo any change
- **Parallel work** - Multiple features at once
- **Collaboration** - Share with others safely

## 🆘 Emergency Recovery

If something goes wrong:

1. **Check your backups:**
   ```bash
   python3 git_helper.py branches
   ```

2. **Switch to a backup:**
   ```bash
   python3 git_helper.py switch
   # Then enter the backup branch name
   ```

3. **Your GitHub repository** always has copies of everything

## 🌐 GitHub Benefits

- ☁️ **Cloud backup** - Your code is safe even if your computer breaks
- 🤝 **Collaboration** - Easy to share with developers
- 📊 **Project management** - Track issues and features
- 🔍 **Code review** - Review changes before merging
- 📈 **Statistics** - See project progress over time

## 🎯 Git Concepts Made Simple

| Git Term | Simple Explanation |
|----------|-------------------|
| **Repository** | Your project folder with version control |
| **Commit** | A saved snapshot of your code |
| **Branch** | A separate copy for working on features |
| **Push** | Send your changes to GitHub |
| **Pull** | Get changes from GitHub |
| **Merge** | Combine changes from different branches |

## 📋 Typical Development Cycle

1. **Start working** on main branch
2. **Make changes** to your code
3. **Save frequently** with `./quick_save.sh`
4. **Create feature branch** for big changes
5. **Work on feature** in separate branch
6. **Save and backup** regularly
7. **Switch back to main** when feature is done
8. **Merge feature** into main branch

## 🚨 Best Practices

### ✅ Do This
- Save your work frequently (daily or after each change)
- Use descriptive commit messages
- Create backups before major changes
- Use feature branches for new features
- Push to GitHub regularly

### ❌ Avoid This
- Working for days without saving
- Generic commit messages like "fix stuff"
- Making changes directly on main for big features
- Never backing up to GitHub
- Deleting files manually instead of using Git

## 🔧 Troubleshooting

### "Permission denied" or "Authentication failed"
1. Make sure you created the GitHub repository
2. Check your GitHub username in the remote URL
3. You might need to set up GitHub authentication

### "Nothing to commit"
- This means you haven't made any changes
- Git only saves when there are actual modifications

### "Merge conflict"
- This happens when Git can't automatically combine changes
- The helper scripts will guide you through resolution

## 📞 Getting Help

1. **Built-in help:**
   ```bash
   python3 git_helper.py help
   ```

2. **Check status when confused:**
   ```bash
   python3 git_helper.py status
   ```

3. **Git is very safe** - you can't easily break anything permanently

---

**Remember:** Git might seem complex, but these scripts make it simple. Just use `./quick_save.sh` daily and you'll be protected! 🛡️