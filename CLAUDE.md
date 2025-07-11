# CLAUDE.md - Context File

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
```bash
# Test corrections
python test_improved_corrections.py

# Test layout
python test_final_vertical_layout.py
```

## Notes
- Project uses PyQt5 for UI
- Documents stored in .tore format
- PDF processing with quality validation

## Memory Log
- Memory file updated
- Added to project memory
- add to memory
- Added additional memory entry to log
- to memorize
- Added memorization instruction to memory log
- to memorize
- add to memory
- Added new version 1.0
- add to memory
- Added area selection implementation to memory
- ready 2 go txt mining
- Added qa problems to memory log
- add to memory extraction debugged?
- Highlights problem added to memory log
- add to memory first major step
- recovery after surprise shutdown
- found critical todos
- trying to keep up
- new look
- going pro
- sleep
- after sleep debugging
- afternoon work end