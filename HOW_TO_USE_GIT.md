# 🚀 How to Use Git with TORE Matrix Labs

## ✅ Git is Already Set Up!

Your Git repository is ready to use! Here's how to work with it:

## 📅 Daily Workflow

### 1. Save Your Work (Most Important!)
```bash
./quick_save.sh
```
- Type a message describing what you changed
- Optionally push to GitHub for cloud backup
- **Use this daily or after any important changes!**

### 2. Check Status
```bash
python3 git_helper.py status
```
- See what files you've changed
- View recent commits

### 3. Create Backups
```bash
./backup.sh
```
- Creates a timestamped backup branch
- Safely stores your current state

## 🌿 Working on Features

### Create a New Feature Branch
```bash
python3 git_helper.py new-feature "my-feature-name"
```
- Lets you experiment without affecting main code
- Example: `python3 git_helper.py new-feature "pdf-improvements"`

### Switch Between Branches
```bash
python3 git_helper.py branches  # See all branches
python3 git_helper.py switch    # Switch to a different branch
```

## 🌐 Setting Up GitHub (Optional but Recommended)

1. **Go to GitHub.com** and create a new repository
2. **Name it:** `tore-matrix-labs` 
3. **Make it Private** (recommended)
4. **Don't initialize** with README (we already have files)

5. **Connect to GitHub:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/tore-matrix-labs.git
   git push -u origin master
   ```
   Replace `YOUR_USERNAME` with your GitHub username.

## 📋 Quick Reference

| What You Want to Do | Command |
|---------------------|---------|
| Save my changes | `./quick_save.sh` |
| Check what's changed | `python3 git_helper.py status` |
| Create backup | `./backup.sh` |
| Start new feature | `python3 git_helper.py new-feature "name"` |
| See all branches | `python3 git_helper.py branches` |
| Switch branches | `python3 git_helper.py switch` |
| View history | `python3 git_helper.py history` |
| Get help | `python3 git_helper.py help` |

## 🎯 What Git Gives You

- **🛡️ Safety:** Never lose your work again
- **📈 History:** See all changes over time
- **🔄 Undo:** Go back to any previous version
- **🌿 Branches:** Work on multiple features safely
- **☁️ Backup:** Store everything in the cloud
- **🤝 Collaboration:** Share with other developers

## 🆘 If Something Goes Wrong

Git is very safe! You can always:

1. **Check your branches:**
   ```bash
   python3 git_helper.py branches
   ```

2. **Switch to a backup:**
   ```bash
   python3 git_helper.py switch
   # Enter the backup branch name
   ```

3. **Your daily saves** create automatic recovery points

## 💡 Pro Tips

1. **Save often** - Use `./quick_save.sh` daily
2. **Use descriptive messages** - "Fixed PDF highlighting bug" not "fix stuff"
3. **Create backups before big changes** - Use `./backup.sh`
4. **Use feature branches** - For new features or experiments
5. **Push to GitHub regularly** - For cloud backup

## 🚨 Emergency: "I Broke Something!"

Don't panic! Git keeps everything:

```bash
# See all your saved versions
python3 git_helper.py history

# See all your backup branches
python3 git_helper.py branches

# Switch to a working version
python3 git_helper.py switch
# Then enter a backup branch name
```

## 📚 Learning More

- **Start simple:** Just use `./quick_save.sh` daily
- **Graduate to branches:** When you want to experiment
- **Use GitHub:** When you want cloud backup
- **Collaborate:** When working with others

---

**Remember:** The most important command is `./quick_save.sh` - use it every day! 🎯