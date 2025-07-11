# TORE Matrix Labs - Complete Installation Guide

## 🚀 Fresh Installation from GitHub

You can now download and run TORE Matrix Labs from GitHub on any machine!

### **Method 1: Quick Installation (Recommended)**

```bash
# 1. Clone the repository
git clone https://github.com/insult0o/tore-matrix-labs.git
cd tore-matrix-labs

# 2. Set up Python environment and run
./scripts/project_operations.sh setup-env
./scripts/project_operations.sh run
```

### **Method 2: Manual Installation**

```bash
# 1. Clone the repository
git clone https://github.com/insult0o/tore-matrix-labs.git
cd tore-matrix-labs

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements/base.txt

# 4. Run the application
python3 -m tore_matrix_labs
```

### **Method 3: Download ZIP (No Git Required)**

1. Go to: https://github.com/insult0o/tore-matrix-labs
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file
4. Open terminal in the extracted folder
5. Run the setup commands above

## 📋 System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows (with WSL)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space

## 🔧 What You Get

When you clone/download from GitHub, you get:

### **Complete Application**
- ✅ Full TORE Matrix Labs source code
- ✅ All UI components and processing engines
- ✅ All critical fixes we implemented
- ✅ Professional PyQt5 interface

### **All Critical Fixes Included**
- ✅ **Project Loading** - No reprocessing needed when opening projects
- ✅ **PDF Highlighting** - QA validation issues highlight properly
- ✅ **Area Display** - Areas show correctly in list and preview sections
- ✅ **Session Persistence** - All validation states save properly

### **Automation Scripts**
- ✅ `./scripts/git_operations.sh` - Git workflow automation
- ✅ `./scripts/project_operations.sh` - Run app, tests, health checks
- ✅ `./scripts/session_recovery.sh` - Session state recovery

### **Complete Documentation**
- ✅ `CLAUDE.md` - Comprehensive development guide
- ✅ `README.md` - Project overview and features
- ✅ This installation guide
- ✅ All technical documentation

## 🧪 Testing the Installation

After installation, test everything works:

```bash
# Check project health
./scripts/project_operations.sh status

# Run all critical tests
./scripts/project_operations.sh test all

# If tests pass, the application is ready!
./scripts/project_operations.sh run
```

## 🎯 Expected Behavior

After running the application, you should see:

1. **Main Window**: Professional PyQt5 interface opens
2. **Tabs Available**: 
   - Project Manager (create/load projects)
   - Manual Validation (area selection and classification)
   - QA Validation (page-by-page corrections review)
3. **All Fixes Working**:
   - Projects load immediately without reprocessing
   - PDF highlighting works in QA validation
   - Areas display properly in manual validation

## 🔍 Troubleshooting

### **Common Issues:**

**Python Version Error:**
```bash
# Check Python version
python3 --version
# Should be 3.8 or higher
```

**Missing Dependencies:**
```bash
# Install missing dependencies
pip install PyQt5 PyMuPDF pathlib
```

**Application Won't Start:**
```bash
# Check if all files are present
./scripts/project_operations.sh status
# Should show all key files present
```

### **Get Help:**

1. Check `CLAUDE.md` for comprehensive development guide
2. Run `./scripts/session_recovery.sh health` for diagnostics
3. All critical functionality has been tested and is working

## ✅ Verification Checklist

After installation, verify:

- [ ] Application starts without errors
- [ ] Can create new projects
- [ ] Can load PDF documents
- [ ] Manual validation interface works
- [ ] QA validation interface works
- [ ] All critical fixes are working

## 🌟 What's New

This version includes all recent critical fixes:

- **No More Reprocessing**: Projects load processed data immediately
- **Working PDF Highlights**: QA issues highlight properly in PDF viewer
- **Fixed Area Display**: Areas show in manual validation list and preview
- **Complete Automation**: Scripts for all common operations
- **Session Continuity**: Full state recovery system

Your TORE Matrix Labs is now a complete, professional document processing pipeline ready for production use!

---

**Repository**: https://github.com/insult0o/tore-matrix-labs
**Installation**: Clone and run `./scripts/project_operations.sh setup-env && ./scripts/project_operations.sh run`