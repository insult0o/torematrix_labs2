# Agent Task Assignments for Issues #5-8

## 🎯 **Agent Coordination Summary**

All GitHub issues and branches have been created successfully. Each agent has a specific focus area with clear deliverables and coordination requirements.

## 🤖 **Agent 1: Visual Areas Persistence**
- **GitHub Issue**: [#10 - Visual Areas Persistence: Cut areas disappear and preview not working](https://github.com/insult0o/tore-matrix-labs/issues/10)
- **Branch**: `fix/visual-areas-persistence`
- **Priority**: 🔴 **HIGH** 
- **Status**: Ready to start

### **Focus**
Fix area cutting, preview, and persistence across page changes in Manual Validation

### **Key Tasks**
1. **Fix area preview in Manual Validation widget**
   - Debug why cut areas show in list but no preview displays
   - Implement proper area preview loading from selection data
   - Ensure preview updates when user selects different areas from list

2. **Fix area visibility persistence on PDF**
   - Areas should remain visible on PDF after cutting
   - Fix disappearing areas when changing pages
   - Implement proper area rendering across page navigation

3. **Fix area selection and preview logic**
   - First area auto-previews, others preview on selection
   - Areas persist across page changes
   - Multiple areas per page display correctly

### **Files to Focus On**
- `tore_matrix_labs/ui/components/manual_validation_widget.py`
- `tore_matrix_labs/ui/components/pdf_viewer.py` 
- `tore_matrix_labs/ui/components/enhanced_drag_select.py`
- `tore_matrix_labs/core/area_storage_manager.py`

### **Testing Instructions**
```bash
# Checkout the branch
git checkout fix/visual-areas-persistence

# Test workflow
python tore_matrix_labs
# 1. Process a multi-page PDF
# 2. Go to Manual Validation tab
# 3. Cut several areas on different pages
# 4. Verify areas remain visible and preview correctly
# 5. Navigate between pages and verify persistence
```

---

## 🤖 **Agent 2: QA Validation Tab** 
- **GitHub Issue**: [#11 - QA Validation Tab Completely Empty & Cannot Complete Validation](https://github.com/insult0o/tore-matrix-labs/issues/11)
- **Branch**: `fix/qa-validation-empty`
- **Priority**: 🔴🔴 **CRITICAL**
- **Status**: Ready to start (HIGH PRIORITY - Others depend on this)

### **Focus**
Fix empty QA Validation tab and complete validation workflow

### **Key Tasks**
1. **Fix empty QA Validation tab**
   - Debug why QA validation shows grey space instead of content
   - Implement proper content loading for QA validation widget
   - Ensure corrections and validation interface displays

2. **Fix "Complete Validation" functionality**
   - Fix blocking issue in manual validation completion
   - Implement proper transition from manual validation to QA validation
   - Ensure validation completion triggers QA tab population

3. **End-to-end validation workflow**
   - Manual validation → Complete validation → QA validation
   - Test complete workflow with real document processing

### **Files to Focus On**
- `tore_matrix_labs/ui/components/page_validation_widget.py`
- `tore_matrix_labs/ui/components/manual_validation_widget.py`
- `tore_matrix_labs/ui/main_window.py` (validation completion handlers)

### **Testing Instructions**
```bash
# Checkout the branch
git checkout fix/qa-validation-empty

# Test workflow
python tore_matrix_labs
# 1. Process a document with known OCR errors
# 2. Complete Manual Validation workflow
# 3. Verify "Complete Validation" option exists and works
# 4. Verify QA Validation tab populates with content
# 5. Test page navigation and correction interface
```

### **⚠️ CRITICAL DEPENDENCY**
**Agent #4 (QA Highlights Testing) is BLOCKED until this is completed.**

---

## 🤖 **Agent 3: UI Redesign Special Areas**
- **GitHub Issue**: [#12 - UI Redesign: Remove Project Management Tab & Rename to Special Areas](https://github.com/insult0o/tore-matrix-labs/issues/12)
- **Branch**: `feat/special-areas-redesign`
- **Priority**: 🟡 **MEDIUM**
- **Status**: Ready to start (Can work independently)

### **Focus**
UI restructuring and special areas workflow improvements

### **Key Tasks**
1. **Remove/Hide Project Management tab**
   - Since it shouldn't exist according to requirements
   - Focus only on Ingestion → Manual Validation → QA workflow

2. **Rename and redesign areas section as "Special Areas"**
   - Update UI labels and navigation
   - Restructure interface for tables, images, diagrams workflow
   - Prepare for next phase: table/image/diagram processing

3. **Streamline document workflow**
   - Documents processed in Ingestion tab are the source of truth
   - Remove redundant project management functionality
   - Focus on core document processing pipeline

### **Files to Focus On**
- `tore_matrix_labs/ui/main_window.py` (tab structure)
- `tore_matrix_labs/ui/components/manual_validation_widget.py` (labels)
- `tore_matrix_labs/config/constants.py` (area type enums)
- UI text and label files

### **Testing Instructions**
```bash
# Checkout the branch
git checkout feat/special-areas-redesign

# Test workflow
python tore_matrix_labs
# 1. Verify Project Management tab is hidden/removed
# 2. Check all area references are now "Special Areas"
# 3. Test complete workflow: Ingestion → Manual Validation → QA
# 4. Verify no broken functionality
```

---

## 🤖 **Agent 4: QA Highlights Testing**
- **GitHub Issue**: [#13 - QA Highlights Testing: Cannot test highlighting system due to empty QA tab](https://github.com/insult0o/tore-matrix-labs/issues/13)
- **Branch**: `fix/qa-highlights-testing`
- **Priority**: 🟡 **MEDIUM**
- **Status**: ⏳ **BLOCKED** - Waiting for Agent #2

### **Focus**
Comprehensive testing of QA validation highlighting system

### **⚠️ DEPENDENCY**
**BLOCKED BY**: Issue #6 (Agent #2) - QA Validation tab is empty
**MUST WAIT FOR**: Agent #2 to complete QA Validation fixes before starting

### **Key Tasks (Once Unblocked)**
1. **Fix QA validation access dependency**
   - Coordinate with Agent #2 for working QA validation
   - Test highlighting system once QA validation is working

2. **Comprehensive highlighting system testing**
   - Test precise error highlighting in both text and PDF
   - Test page synchronization between text and PDF panels
   - Test multi-line highlighting and coordinate mapping

3. **Highlighting system validation**
   - Ensure highlights appear correctly in QA validation
   - Test highlighting accuracy and performance
   - Document any highlighting issues found

### **Files to Focus On**
- `tore_matrix_labs/ui/highlighting/highlighting_engine.py`
- `tore_matrix_labs/ui/highlighting/coordinate_mapper.py`
- `tore_matrix_labs/ui/highlighting/multi_box_renderer.py`
- `tore_matrix_labs/ui/components/page_validation_widget.py`

### **Testing Instructions (When Ready)**
```bash
# Wait for Agent #2 to complete QA validation fixes
# Then checkout the branch
git checkout fix/qa-highlights-testing

# Test comprehensive highlighting
python tore_matrix_labs
# 1. Process document with known OCR errors
# 2. Complete Manual Validation 
# 3. Access QA Validation tab (should work after Agent #2)
# 4. Test highlighting for each error/correction
# 5. Generate comprehensive test report
```

---

## 📋 **Coordination Instructions**

### **Work Order Priority**
1. **Agent #2 (CRITICAL)**: Must complete first - others depend on working QA tab
2. **Agent #1 & #3**: Can work in parallel on their respective areas
3. **Agent #4**: Starts after Agent #2 completes QA validation fixes

### **Communication Protocol**
- **Agent #2**: Notify when QA validation is working so Agent #4 can begin
- **All Agents**: Update GitHub issues with progress and findings
- **Coordination**: Use issue comments for cross-agent communication

### **Success Criteria**
- ✅ **Agent #1**: Cut areas persist and preview correctly
- ✅ **Agent #2**: QA validation tab shows content and works end-to-end
- ✅ **Agent #3**: UI is streamlined with "Special Areas" terminology
- ✅ **Agent #4**: Comprehensive highlighting test report with 95%+ accuracy

### **Branch Management**
Each agent works on their dedicated branch:
- `fix/visual-areas-persistence` (Agent #1)
- `fix/qa-validation-empty` (Agent #2)
- `feat/special-areas-redesign` (Agent #3)
- `fix/qa-highlights-testing` (Agent #4)

### **Testing Command**
All agents use the same command to test:
```bash
python tore_matrix_labs
```

### **Final Integration**
Once all issues are resolved:
1. Each agent creates a pull request from their branch
2. Code review and testing of combined changes
3. Merge to main branch
4. Comprehensive integration testing

---

## 🚀 **Ready to Deploy Agents!**

All GitHub issues are created with proper labels, branches are set up, and detailed instructions are provided. Agents can begin work immediately with clear coordination guidelines.

**The parallel development workflow is ready! 🎯**