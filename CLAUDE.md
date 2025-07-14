# CLAUDE.md - Context File

## 🚨 CRITICAL: Multi-Agent Branch Management
**MANDATORY for ALL agents before starting work:**

1. **Create unique feature branch** → `git checkout -b feature/[component]-agent[N]-issue[number]`
2. **Never share branches between agents** → Each agent MUST work on separate branch
3. **Verify branch before starting** → `git branch --show-current`

**Examples:**
- Agent 1: `git checkout -b feature/reactive-components-agent1-issue108`
- Agent 2: `git checkout -b feature/state-integration-agent2-issue109`
- Agent 3: `git checkout -b feature/performance-agent3-issue110`
- Agent 4: `git checkout -b feature/components-agent4-issue111`

**ENFORCEMENT**: Branch sharing causes PR conflicts and is NON-COMPLIANT.

## Current Work Status
- Working on new page-by-page corrections interface design
- Replacing problematic coordinate-based highlighting with side-by-side approach
- Creating new PageValidationWidget for better accuracy and user experience
- Focus on project file "4.tore" and "7.tore"

## Recent Tasks Completed
- Created test files for corrections logic
- Implemented vertical layout testing
- Working on improved corrections display
- Fixed corrections display issues:
  - Doubled vertical size of text boxes in corrections display (minimum 200px height)
  - Fixed error highlighting in extraction edition field (improved visibility with yellow background, red text, bold formatting)
  - Fixed error correlation between extraction and PDF display sections (improved coordinate conversion, page navigation)
  - Enhanced PDF highlighting with better visibility and automatic page navigation
- Fixed config file JSON parsing error (completed malformed config.json)
- Made OCR recognition text field bigger vertically (120px minimum height, editable text area)
- Implemented precise highlighting for exact error location in extraction text:
  - Multiple search strategies (exact match, cleaned text, character-level)
  - Bright yellow highlighting with red text and underline
  - Fuzzy matching for difficult-to-find errors
  - Automatic cursor positioning for visibility
- Implemented precise highlighting for exact error location in PDF:
  - Character-level text search using PyMuPDF
  - Automatic page navigation to error location
  - Multiple search strategies for problematic OCR characters
  - Enhanced coordinate conversion and bounds checking
  - Improved visibility with thicker borders and better colors
- Fixed QStandardPaths runtime directory permissions warning:
  - Added automatic runtime directory permissions fix on application startup
  - Handles WSL2 permission issues where /run/user/1000 has 755 instead of 700
  - Logs permission fixes for debugging
  - Prevents Qt warning about incorrect directory permissions

## Next Steps - Page-by-Page Interface Implementation
Current progress: ✅ **COMPLETED** - New PageValidationWidget implemented and integrated

**Completed tasks:**
1. ✅ Create new page-by-page validation widget file (page_validation_widget.py)
2. ✅ Add basic layout structure with splitter
3. ✅ Add page navigation controls  
4. ✅ Create extracted text display area
5. ✅ Add issue navigation buttons
6. ✅ Implement error data processing and navigation
7. ✅ Add issue information display
8. ✅ Add PDF highlighting synchronization
9. ✅ Integrate with main window (replaced QAValidationWidget)

**Key Improvements Made:**
- ✅ **Fixed widget display**: New PageValidationWidget now shows instead of old QA widget
- ✅ **Enhanced error location precision**: Leverages both bbox coordinates and text_position from .tore files
- ✅ **Better navigation**: Page-by-page and issue-by-issue navigation with clear labeling
- ✅ **Rich error context**: Shows error type, description, severity with color coding
- ✅ **Side-by-side layout**: PDF viewer + extracted text with synchronized highlighting
- ✅ **Data structure analysis**: Researched .tore file format showing comprehensive error location data
- ✅ **Text highlighting**: Implemented precise text highlighting using text_position coordinates
- ✅ **Multiple search strategies**: Fallback text search when coordinates are invalid
- ✅ **Smart navigation**: Automatic text loading and highlighting on page/issue changes
- ✅ **Professional UI**: Color-coded severity levels, responsive layout, clear information display

**Technical Implementation Details:**
- **Error data structure**: bbox coordinates + text_position + page + severity + type
- **Navigation logic**: Efficient page grouping and issue indexing for 184+ corrections
- **Highlighting strategy**: Primary text_position, fallback to text search, visual feedback
- **Signal compatibility**: Maintains highlight_pdf_location signal for PDF synchronization
- **Error types supported**: OCR errors, formatting issues, table problems, encoding errors

**New Design Approach (COMPLETED):**
✅ Side-by-side: PDF viewer (left) + extracted text (right)  
✅ Page-by-page navigation instead of issue list  
✅ Multiple issue colors per page (severity-based color coding)  
✅ Precise positioning between issues (automatic text cursor positioning)  
✅ Better coordinate matching (dual strategy: text_position + bbox coordinates)

**Result Summary:**
The new PageValidationWidget successfully replaces the problematic coordinate-based highlighting system with a more accurate and user-friendly approach. It now handles 184+ corrections across 54 pages with:

**✅ COMPLETED IMPROVEMENTS:**
- **Removed PDF viewer widget** - Uses document preview instead for better integration
- **Full-width extracted content** - Same size as document preview for consistent experience
- **Real-time page text extraction** - Shows all text from current page using PyMuPDF
- **Multi-strategy highlighting** - Text position → text search → bbox approximation
- **Severity-based color coding** - Critical (red), Major (yellow), Medium (orange), Minor (green)
- **Synchronized navigation** - Both document preview and extracted content jump to exact issue locations
- **Log widget integration** - Issue explanations and navigation details appear in log section
- **Professional interface** - Clean layout with clear navigation controls and issue information

**✅ LATEST ENHANCEMENTS:**
- **Precise coordinate mapping** - Character-level mapping between text positions and PDF coordinates
- **Cursor synchronization** - Text cursor position automatically shows corresponding PDF location
- **Text selection highlighting** - Selected text in extracted content highlights in PDF viewer
- **All issues visible** - All page issues highlighted simultaneously with active issue distinct
- **Correction workflow** - Approve/reject buttons with status tracking and save functionality
- **Editable text content** - Users can make corrections directly in the text area
- **Smart highlighting** - Active issue in bright orange, inactive issues in subtle colors
- **Status management** - Track approved/rejected corrections with visual feedback

**🔧 DEBUGGING & FIXES:**
- **PDF highlighting fixed** - Corrected coordinate validation and bbox handling in PDF viewer
- **Text position accuracy** - Using PyMuPDF word extraction for precise character-to-coordinate mapping  
- **Multi-strategy highlighting** - Text position → search fallback → bbox-only for robust highlighting
- **Debug logging added** - Comprehensive logging for coordinate conversion and highlighting process
- **Navigation improvements** - Fixed page navigation and highlighting refresh on issue changes
- **Coordinate system fixed** - Proper PDF-to-pixmap coordinate conversion with Y-axis flipping
- **Error data validation** - Coordinates from .tore files verified as accurate and within page bounds

**🔧 LATEST FIXES:**
- **Text formatting restored** - Using standard get_text() method to preserve original PDF formatting and spacing
- **Mouse interaction fixed** - Added proper mouse event handling for text selection and cursor positioning
- **Coordinate mapping improved** - Character-level mapping with fallback strategy for missing positions
- **Selection highlighting added** - Mouse drag selection automatically highlights corresponding PDF areas
- **PDF viewer methods added** - Added highlight_selection() and show_cursor_location() methods
- **Debug mapping validation** - Added mapping coverage statistics and sample position logging
- **Performance optimized** - Reduced log spam and improved coordinate lookup efficiency

## Commands to Run

### 🚀 Application Commands
```bash
# Run the application
python3 -m tore_matrix_labs
# or use project script
./scripts/project_operations.sh run

# Run all critical tests
./scripts/project_operations.sh test all

# Check project health
./scripts/project_operations.sh status
```

### 📝 Git & GitHub Commands
```bash
# Check git status and recent commits
./scripts/git_operations.sh status

# Commit changes with message
./scripts/git_operations.sh commit "Your commit message"

# Push to GitHub
./scripts/git_operations.sh push

# Commit and push in one command
./scripts/git_operations.sh sync "Your commit message"

# Setup git configuration (if needed)
./scripts/git_operations.sh full-setup
```

### 🔄 Session Recovery Commands
```bash
# Show current session state
./scripts/session_recovery.sh state

# Restore git configuration
./scripts/session_recovery.sh restore

# Quick health check
./scripts/session_recovery.sh health

# Show session summary
./scripts/session_recovery.sh summary
```

## Notes
- Project uses PyQt5 for UI
- Documents stored in .tore format
- PDF processing with quality validation

## 🔄 Session Continuity Guide

### **Quick Session Recovery (Start Here for New Sessions)**
```bash
# 1. Check current state
./scripts/session_recovery.sh summary

# 2. Restore configuration if needed
./scripts/session_recovery.sh restore

# 3. Check project health
./scripts/session_recovery.sh health

# 4. Show available operations
./scripts/session_recovery.sh operations
```

### **🎯 Critical Information for Claude**

**Project Status:** ✅ FULLY OPERATIONAL
- **GitHub Repository:** https://github.com/insult0o/tore-matrix-labs
- **All Critical Fixes:** Implemented and tested
- **Git Integration:** Fully configured with credentials

**Recent Major Achievements:**
1. ✅ **Project Loading Fix** - No more reprocessing needed when opening projects
2. ✅ **PDF Highlighting Fix** - QA validation issues highlight properly in PDF viewer
3. ✅ **Area Display Fix** - Areas show correctly in list and preview sections
4. ✅ **GitHub Integration** - Repository setup with automated scripts

**Essential Scripts Created:**
- `./scripts/git_operations.sh` - All git operations (commit, push, pull, etc.)
- `./scripts/project_operations.sh` - Run app, tests, status checks
- `./scripts/session_recovery.sh` - Quick session state recovery

**Git Configuration:**
- User: insult0o
- Email: miguel.borges.cta@gmail.com
- Remote: https://github.com/insult0o/tore-matrix-labs.git
- Credentials: Stored with token authentication

**Test Files Available:**
- `test_project_loading_fix.py` - Tests project loading improvements
- `test_pdf_highlighting_fix.py` - Tests PDF highlighting functionality
- `test_area_list_display_fix.py` - Tests area display fixes

### **🚀 Common Session Actions**

**To continue development:**
```bash
# Check what needs to be done
./scripts/git_operations.sh status

# Make changes, then commit and push
./scripts/git_operations.sh sync "Description of changes"

# Test the application
./scripts/project_operations.sh test all
```

**To run the application:**
```bash
./scripts/project_operations.sh run
```

**If git credentials are lost:**
```bash
./scripts/git_operations.sh full-setup
# Then add Personal Access Token when prompted
```

## Memory Log
- GitHub repository setup complete: https://github.com/insult0o/tore-matrix-labs
- All critical fixes implemented and tested
- Comprehensive automation scripts created for session continuity
- Git integration working with token authentication
- Project ready for continued development and collaboration
- nadadenada
- debbuging