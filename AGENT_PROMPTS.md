# Agent Prompts for TORE Matrix Labs Issues

## 🟥 Issue #47: Missing Visual Re-rendering of Image Areas After Page Change
**Agent:** PDF GUI rehydration agent (visual canvas sync logic)  
**Branch:** `fix/image-areas-visibility`

### Prompt:
You are a PDF GUI rehydration specialist working on TORE Matrix Labs. Your task is to fix issue #47 where image areas disappear from the PDF canvas when switching pages.

**Context:**
- Image areas are drawn as bounding boxes classified as "Image"
- They appear in the preview panel and area list but not on the PDF canvas after page changes
- The issue is specifically about visual rendering, not data persistence

**Your tasks:**
1. Checkout the branch `fix/image-areas-visibility`
2. Investigate the PDF viewer component in `tore_matrix_labs/ui/components/pdf_viewer.py`
3. Look at the `manual_validation_widget.py` to understand how areas are drawn
4. Find where page change events are handled and where area redrawing should occur
5. Implement proper area re-rendering logic when returning to a page
6. Ensure the `handle_page_change` method properly triggers area redraw for Image type areas
7. Test with a PDF containing image areas, verifying they persist visually across page navigation
8. Create a test file `test_image_area_visibility_fix.py` to verify the fix

**Key files to examine:**
- `tore_matrix_labs/ui/components/pdf_viewer.py`
- `tore_matrix_labs/ui/components/manual_validation_widget.py`
- `tore_matrix_labs/ui/components/enhanced_drag_select.py`

**Success criteria:**
- Image areas remain visible on the PDF canvas after page switching
- No regression in other area types
- Clear logging of area re-rendering process

---

## 🟥 Issue #48: Program Crashes When Highlighting Extracted Text
**Agent:** Text rendering + validation logic agent  
**Branch:** `fix/text-highlight-crash`

### Prompt:
You are a text rendering and validation specialist working on TORE Matrix Labs. Your task is to fix issue #48 where the program crashes when highlighting extracted text.

**Context:**
- The crash occurs when attempting to highlight extracted text in the viewer
- Likely due to invalid references or rendering hooks
- The issue affects text highlighting functionality

**Your tasks:**
1. Checkout the branch `fix/text-highlight-crash`
2. Investigate the text highlighting engine in `tore_matrix_labs/ui/highlighting/highlighting_engine.py`
3. Look at the `page_validation_widget.py` to understand text highlighting implementation
4. Add proper error handling and validation for text selection
5. Implement graceful handling of invalid selections
6. Add defensive programming to prevent crashes
7. Test with various PDFs and text selection scenarios
8. Create a test file `test_text_highlight_crash_fix.py` to verify stability

**Key files to examine:**
- `tore_matrix_labs/ui/highlighting/highlighting_engine.py`
- `tore_matrix_labs/ui/components/page_validation_widget.py`
- `tore_matrix_labs/ui/components/pdf_viewer.py`

**Success criteria:**
- No crashes when highlighting text
- Invalid selections handled gracefully with user feedback
- Text highlighting remains functional for valid selections

---

## 🟥 Issue #49: Drawn Areas Not Persisting After Project Reload
**Agent:** Storage state management agent  
**Branch:** `fix/area-state-rehydration`

### Prompt:
You are a storage state management specialist working on TORE Matrix Labs. Your task is to fix issue #49 where drawn areas don't appear after project reload.

**Context:**
- Areas exist in metadata but aren't rendered after reopening a project
- This is a state persistence and rehydration issue
- The manual validation workflow is affected

**Your tasks:**
1. Checkout the branch `fix/area-state-rehydration`
2. Investigate project loading in `tore_matrix_labs/core/project.py`
3. Examine how areas are saved and loaded from `.tore` files
4. Check the `manual_validation_widget.py` for area loading logic
5. Ensure areas are properly restored and rendered on project load
6. Implement proper state rehydration for all area types
7. Test save/load cycle with multiple area types
8. Create a test file `test_area_persistence_fix.py` to verify the fix

**Key files to examine:**
- `tore_matrix_labs/core/project.py`
- `tore_matrix_labs/ui/components/manual_validation_widget.py`
- `tore_matrix_labs/core/storage_handler.py`

**Success criteria:**
- All drawn areas appear correctly after project reload
- Area properties (type, position, metadata) are preserved
- No data loss during save/load cycle

---

## 🟥 Issue #50: Image Areas Re-disappear After Being Recreated Post-Load
**Agent:** PDF viewer component memory agent  
**Branch:** `fix/redraw-image-state`

### Prompt:
You are a PDF viewer component memory specialist working on TORE Matrix Labs. Your task is to fix issue #50 where newly drawn areas disappear after page navigation in a reloaded project.

**Context:**
- After reloading a project, new areas drawn don't persist during page navigation
- This is a runtime state management issue
- Different from the initial load problem

**Your tasks:**
1. Checkout the branch `fix/redraw-image-state`
2. Investigate runtime area management in `enhanced_drag_select.py`
3. Check how areas are stored in memory during runtime
4. Ensure newly created areas are properly added to the runtime state
5. Fix the page navigation logic to preserve new areas
6. Implement proper state synchronization between components
7. Test with creating new areas after project load
8. Create a test file `test_runtime_area_persistence_fix.py`

**Key files to examine:**
- `tore_matrix_labs/ui/components/enhanced_drag_select.py`
- `tore_matrix_labs/ui/components/manual_validation_widget.py`
- `tore_matrix_labs/core/storage_handler.py`

**Success criteria:**
- Newly created areas persist during page navigation
- Runtime state properly synchronized
- No difference in behavior between fresh and reloaded projects

---

## 🟥 Issue #51: Crash on Highlight After Project Load
**Agent:** Load-time linker agent  
**Branch:** `fix/highlight-linking`

### Prompt:
You are a load-time linker specialist working on TORE Matrix Labs. Your task is to fix issue #51 where highlighting crashes after project load.

**Context:**
- Highlighting works in fresh projects but crashes after reload
- Indicates failure in linking extracted elements to GUI state
- Deserialization process needs fixing

**Your tasks:**
1. Checkout the branch `fix/highlight-linking`
2. Investigate project deserialization in `project.py`
3. Check how extracted elements are linked to GUI components
4. Ensure proper initialization of highlighting engine after load
5. Fix the connection between loaded data and GUI state
6. Implement proper reference restoration
7. Test highlighting after various project load scenarios
8. Create a test file `test_highlight_linking_fix.py`

**Key files to examine:**
- `tore_matrix_labs/core/project.py`
- `tore_matrix_labs/ui/highlighting/highlighting_engine.py`
- `tore_matrix_labs/ui/components/page_validation_widget.py`

**Success criteria:**
- No crashes when highlighting after project load
- All highlighting features work identically before and after reload
- Proper error messages if linking fails

---

## 🟦 Issue #52: Feature Request - Display All Unstructured Elements
**Agent:** Unstructured-to-GUI renderer + metadata interpreter  
**Branch:** `feature/unstructured-visualizer`

### Prompt:
You are an unstructured document rendering specialist working on TORE Matrix Labs. Your task is to implement feature #52 to display all unstructured elements in the GUI.

**Context:**
- Need to support all element types from `unstructured.partition_pdf()`
- Each type needs visual representation and metadata handling
- Integration with existing area list and PDF viewer

**Your tasks:**
1. Checkout the branch `feature/unstructured-visualizer`
2. Study the enhanced unstructured processor in `enhanced_unstructured_processor.py`
3. Create a new component `unstructured_element_renderer.py`
4. Implement visual representations for all element types:
   - NarrativeText, Title, ListItem (text with styling)
   - Table (render HTML table from `text_as_html`)
   - Image (display from `image_base64`)
   - FigureCaption, CodeSnippet, Formula (specialized rendering)
   - Header, Footer, PageNumber, UncategorizedText
5. Add color-coded bounding boxes on PDF canvas
6. Implement icon system for area list
7. Add inline previews for rich content (tables, images, code)
8. Handle missing coordinates gracefully
9. Create comprehensive test file `test_unstructured_visualizer.py`

**Key implementation details:**
- Use Qt widgets for rich content display
- Color mapping for each element type
- Fallback rendering for malformed data
- Group elements by page number
- Preserve all metadata fields

**Success criteria:**
- All unstructured element types visible in GUI
- Rich content properly rendered (tables, images, code)
- Intuitive visual distinction between types
- Graceful handling of missing/malformed data
- Performance remains acceptable with many elements

---

## General Instructions for All Agents

1. **Git Workflow:**
   ```bash
   git checkout -b [branch-name]
   # Make changes
   git add -A
   git commit -m "🐛 Fix Issue #[number]: [description]"
   ```

2. **Testing:**
   - Create test files to verify fixes
   - Test with multiple PDF types
   - Ensure no regressions

3. **Documentation:**
   - Add clear comments explaining fixes
   - Update docstrings where needed
   - Log important operations for debugging

4. **Code Quality:**
   - Follow existing code style
   - Use type hints where appropriate
   - Handle errors gracefully

5. **PR Description:**
   - Reference the issue number
   - Describe the fix implementation
   - List files changed
   - Include test results