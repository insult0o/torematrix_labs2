# Complete Testing Guide for Issue #47 Fix

## What Was Fixed
1. **Area Re-rendering**: Areas now reload when displaying each page
2. **Page Synchronization**: Manual Validation and PDF Viewer now stay in sync
3. **Page Numbering**: Fixed mismatch between 1-based and 0-based page numbers

## How to Test

### 1. Run the Application
```bash
python3 -m tore_matrix_labs
```

### 2. Test the Complete Fix

#### Test A: Basic Area Persistence
1. Load a PDF with multiple pages
2. Go to **Manual Validation** tab
3. Navigate to page 1 (should show "Page 1 of X")
4. Draw an image area (drag and select IMAGE)
5. Navigate to page 2 using the navigation buttons
6. Return to page 1
7. **✅ CHECK**: Image area should still be visible!

#### Test B: Page Sync Verification
1. In Manual Validation, note what page you're on
2. Switch to **Document Preview** tab (left side)
3. **✅ CHECK**: PDF viewer should show the same page
4. In Manual Validation, go to page 3
5. Check Document Preview again
6. **✅ CHECK**: PDF viewer should now show page 3

#### Test C: Correct Page Assignment
1. Go to Manual Validation page 2
2. Create an image area
3. Check the log messages
4. **✅ CHECK**: Should say "saved on page 2" (not page 1 or 3)
5. Navigate to page 1 - no area should appear
6. Navigate to page 3 - no area should appear
7. Return to page 2
8. **✅ CHECK**: Area should be visible only on page 2

### 3. What to Look For in Logs
Watch for these log messages:
- `SYNC_PDF: Syncing PDF viewer to page X`
- `AREA_CREATE PAGE DEBUG: Page for storage = X`
- `Re-loading persistent areas for document 'X', page Y`

## If Everything Works ✅

Push to GitHub and create PR:
```bash
# Push the branch
git push -u origin fix/image-areas-visibility

# Create the PR
gh pr create --title "🐛 Fix Issue #47: Image areas persist with proper page sync" \
  --body "## Summary
Fixed image areas disappearing when switching pages by:
- Implementing area reloading on page display
- Synchronizing Manual Validation and PDF Viewer page states
- Fixing page numbering mismatches (1-based vs 0-based)

## Root Cause
Manual Validation widget and PDF Viewer were not synchronized, causing:
1. Areas to be created on wrong pages
2. Areas to disappear when navigating

## Changes
- Added area reloading to pdf_viewer._display_current_page()
- Added page sync from Manual Validation to PDF Viewer
- Fixed page number conversions
- Added debug logging

## Test Results
- [x] Areas persist when navigating between pages
- [x] Areas appear on correct pages
- [x] Manual Validation and PDF Viewer stay in sync
- [x] No regression in other functionality

Fixes #47"
```

## If Something Still Doesn't Work ❌

1. **Areas still disappear**: Check if areas are being saved/loaded with correct document ID
2. **Wrong page**: Check log messages for page number conversions
3. **Not syncing**: Verify _sync_pdf_viewer_page is being called

Share the specific issue and log messages for further debugging.