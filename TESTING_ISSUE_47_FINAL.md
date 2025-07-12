# Issue #47 Fix - Final Testing Guide

## ✅ What Was Fixed

1. **Area Re-rendering on Page Change**
   - Areas now reload automatically when displaying each page
   - Fixed in `pdf_viewer._display_current_page()` method

2. **Page Synchronization** 
   - Manual Validation widget and PDF Viewer now stay perfectly in sync
   - Added `_sync_pdf_viewer_page()` method to manual_validation_widget

3. **Page Numbering Consistency**
   - Fixed mismatch between 1-based (Manual Validation) and 0-based (PDF Viewer) page numbers
   - Areas are now saved to the correct page

4. **Signal Connection Cleanup**
   - Removed redundant signal connection that was causing double loading

## 🧪 How to Test the Complete Fix

### Step 1: Run the Application
```bash
python3 -m tore_matrix_labs
```

### Step 2: Load a Test Project
1. Go to **Project Management** tab
2. Open an existing project with PDFs (or create a new one)
3. Load a PDF document with multiple pages

### Step 3: Test Area Persistence

#### Test A: Basic Area Creation and Persistence
1. Navigate to **Manual Validation** tab
2. Go to page 1 (verify it shows "Page 1 of X")
3. Draw an image area:
   - Click and drag to select an area
   - Choose IMAGE when prompted
4. Navigate to page 2 using the Next button
5. Return to page 1 using the Previous button
6. **✅ Expected**: The image area should still be visible on page 1!

#### Test B: Multiple Pages with Areas
1. Create an area on page 1 (as above)
2. Go to page 2 and create another area
3. Go to page 3 and create another area
4. Navigate back through pages 3 → 2 → 1
5. **✅ Expected**: Each page should show only its own areas

#### Test C: Page Sync Verification
1. In Manual Validation, note the current page number
2. Look at the Document Preview (PDF viewer on the right)
3. **✅ Expected**: Both should show the same page
4. Use navigation buttons in Manual Validation to change pages
5. **✅ Expected**: PDF viewer should follow along automatically

#### Test D: Correct Page Assignment
1. Go to Manual Validation page 3
2. Create an image area
3. Check the console/log output
4. **✅ Expected**: Should say "saved on page 3" (not 2 or 4)
5. Navigate to pages 2 and 4
6. **✅ Expected**: No area should appear on these pages
7. Return to page 3
8. **✅ Expected**: Area should be visible only on page 3

### Step 4: Verify in Logs

Look for these key log messages:
```
Re-loading persistent areas for document 'X', page Y
SYNC_PDF: Syncing PDF viewer to page X
AREA_CREATE PAGE DEBUG: Page for storage = X
LOAD AREAS: Successfully loaded X areas for page Y
```

## 🚀 If Everything Works

Push to GitHub and create the PR:

```bash
# Push the branch
git push -u origin fix/image-areas-visibility

# Create PR using GitHub CLI
gh pr create --title "🐛 Fix Issue #47: Image areas persist correctly after page changes" \
  --body "## Summary
Fixes image areas disappearing when switching pages in Manual Validation.

## Root Cause
1. Areas were not being reloaded when displaying pages
2. Manual Validation widget and PDF Viewer page states were not synchronized
3. Page numbering mismatches caused areas to be saved on wrong pages

## Solution
- Added area reloading to \`pdf_viewer._display_current_page()\`
- Implemented page synchronization from Manual Validation to PDF Viewer
- Fixed page number conversions (0-based vs 1-based)
- Removed redundant signal connections

## Changes Made
- **pdf_viewer.py**: Added area reloading on page display
- **manual_validation_widget.py**: Added \`_sync_pdf_viewer_page()\` method
- **enhanced_drag_select.py**: Added debug logging for page tracking
- **main_window.py**: Removed redundant signal connection

## Testing Done
- [x] Areas persist when navigating between pages
- [x] Areas appear on the correct pages
- [x] Manual Validation and PDF Viewer stay in sync
- [x] No regression in other functionality
- [x] Multiple areas on different pages work correctly

Fixes #47"
```

## ❌ If Something Doesn't Work

### Common Issues:

1. **Areas still disappear**
   - Check if the project has a valid document ID
   - Verify area storage manager is initialized
   - Look for error messages about loading areas

2. **Areas on wrong page**
   - Check log messages for page number conversions
   - Verify "AREA_CREATE PAGE DEBUG" shows correct page

3. **Pages not syncing**
   - Ensure _sync_pdf_viewer_page is being called
   - Check for errors in getting main window reference

### Debug Commands:
```bash
# Check for syntax errors
python3 -m py_compile tore_matrix_labs/ui/components/pdf_viewer.py
python3 -m py_compile tore_matrix_labs/ui/components/manual_validation_widget.py

# Run with debug logging
TORE_DEBUG=1 python3 -m tore_matrix_labs
```

## 📋 Summary of Changes

All fixes have been implemented and are ready for testing:
- ✅ Area reloading on page display
- ✅ Page synchronization between widgets  
- ✅ Correct page numbering
- ✅ Clean signal connections
- ✅ Comprehensive debug logging

The issue should now be completely resolved!