# CLAUDE.md - TORE Matrix Labs V3 Context

## 🚀 Project Overview
TORE Matrix Labs V3 is a complete greenfield rewrite of the document processing platform. Starting from scratch with all lessons learned from V1 analysis.

## 🎯 Key Design Principles
1. **Clean Architecture** - No legacy constraints
2. **Unified Data Model** - Single element model for all types
3. **Event-Driven** - Modern async architecture
4. **Performance First** - Optimized for 10K+ elements
5. **Test-Driven** - Comprehensive testing from day 1

## 📋 Core Requirements (From V1 Analysis)
- Support 15+ element types from unstructured library
- Manual validation workflow with area selection
- Page-by-page corrections interface
- Quality assessment and approval workflow
- Multi-format export (JSON, XML, CSV, PDF, HTML, DOCX)
- Project persistence with .tore format compatibility
- Enterprise-ready with multi-backend storage

## 🏗️ V3 Architecture
```
Event Bus ← → State Manager ← → UI Components
     ↑              ↑              ↑
     |              |              |
Processing ← → Storage ← → Element Renderer
Pipeline      System      Factory
```

## 💻 Technology Choices
- **Python 3.11+** - Latest features and performance
- **PyQt6** - Modern Qt binding with better performance
- **AsyncIO** - Async/await throughout
- **Type Hints** - Full typing for reliability
- **Pydantic** - Data validation and settings
- **SQLAlchemy 2.0** - Modern ORM with async support

## 🚦 Current Status - Major Progress Achieved
- ✅ **Project structure complete** - Full enterprise-grade architecture
- ✅ **Core systems implemented** - Event Bus, State Management, Configuration, Storage
- ✅ **Unified Element Model complete** - 15+ element types with V1 compatibility
- ✅ **Unstructured.io Integration complete** - 19 file formats, optimization, validation
- 🚧 **Document Ingestion System** - 43% complete (Issue #7)
- ✅ **Clean architecture maintained** - Async, typed, tested throughout

## 📝 Development Guidelines
1. **API First** - Design interfaces before implementation
2. **Test First** - Write tests before code
3. **Document First** - Document decisions and APIs
4. **Performance First** - Profile and optimize early
5. **User First** - Focus on workflows and experience

## 🔗 GitHub Repository
- New repository: `torematrix_labs2`
- Clean commit history
- Proper branching strategy from start
- CI/CD pipeline setup

## 🎯 Completed Achievements
1. ✅ **Git repository initialized** - Clean branching strategy with 15+ merged PRs
2. ✅ **GitHub repository active** - Full CI/CD, issues, PRs, comprehensive tracking
3. ✅ **Core data models designed** - Unified Element Model with metadata framework
4. ✅ **Testing framework established** - >95% coverage across all components
5. ✅ **Major systems implemented** - Event Bus, State, Config, Storage, Unstructured integration

## 🎯 Next Priority: Document Ingestion System (Issue #7)
- Core Upload Manager & File Validation (Sub-issue #83)
- Queue Management & Batch Processing (Sub-issue #85)  
- API Endpoints & WebSocket Progress (Sub-issue #86)
- Integration & Testing (Sub-issue #87)

## 🤖 Agent Workflow - Standard Operating Procedure

### Trigger: "Let's work on issue X"
When this command is given, I will automatically execute the following comprehensive workflow:

### 📋 Workflow Steps:
1. **Analyze Parent Issue** - Understand requirements and identify 4 parallelizable components
2. **Create 4 Sub-Issues** - One for each agent with format: `[Parent Topic] Sub-Issue #X.Y: [Component]`
3. **Create 4 Agent Instruction Files**:
   - `AGENT_1_[TOPIC].md` - Core/Foundation (no dependencies)
   - `AGENT_2_[TOPIC].md` - Data/Persistence (depends on Agent 1)
   - `AGENT_3_[TOPIC].md` - Performance/Optimization (depends on Agent 1)
   - `AGENT_4_[TOPIC].md` - Integration/Polish (depends on all)
4. **Create Coordination Guide** - `[TOPIC]_COORDINATION.md` with timeline and integration points
5. **Update All GitHub Issues** - Parent and sub-issues with implementation details

### 📁 Agent Instruction File Structure:
- Your Assignment & Specific Tasks
- Files to Create (with tree structure)
- Technical Implementation Details (with code examples)
- Testing Requirements (>95% coverage)
- Integration Points
- GitHub Workflow
- Success Criteria
- Communication Protocol

### ⏱️ Standard Timeline:
- **Phase 1 (Days 1-2)**: Foundation building
- **Phase 2 (Days 3-4)**: Integration work
- **Phase 3 (Days 5-6)**: Testing and polish

### 📊 Standard Success Metrics:
- Test coverage >95%
- Performance targets defined and met
- Full API documentation
- Integration tests passing
- Type coverage 100%

### 🔄 This workflow ensures:
- Consistent parallel development
- Clear dependencies and integration points
- Daily progress tracking via GitHub
- High-quality deliverables
- Efficient 6-day development cycles

## 🏁 Agent "End Work" Routine

### Trigger: "end work"
When the user says "end work", execute this standardized completion routine:

### 1️⃣ Run All Tests
```bash
# Run tests for your specific component
source .venv/bin/activate && python -m pytest tests/unit/core/[your-component]/ -v

# Verify all tests pass before proceeding
# If any fail, fix them first
```

### 2️⃣ Stage and Commit Changes
```bash
# Stage all changes
git add -A

# Commit with standardized message format
git commit -m "$(cat <<'EOF'
🚀 FEATURE: [Component Name] Implementation

Implemented [brief description of what was built]

## Changes Made:
- ✅ [Key feature/component 1]
- ✅ [Key feature/component 2]
- ✅ [Key feature/component 3]
- ✅ [Additional features...]

## Technical Details:
- [Architecture decision 1]
- [Architecture decision 2]
- [Technical implementation detail]

## Testing:
- [X] tests across [Y] test files
- All tests passing
- >95% code coverage achieved

Fixes #[sub-issue-number]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 3️⃣ Push and Create Pull Request
```bash
# Push the feature branch
git push -u origin feature/[branch-name]

# Create PR with detailed description
gh pr create --title "🚀 FEATURE: [Component Name] (#[sub-issue-number])" --body "$(cat <<'EOF'
## Summary
Implemented [component description] as requested in Issue #[sub-issue-number].

## Implementation Details

### ✅ [Major Component 1]
- [Detail about implementation]
- [Key technical decisions]
- [Notable features]

### ✅ [Major Component 2]
- [Detail about implementation]
- [Key technical decisions]
- [Notable features]

### ✅ [Major Component 3]
- [Detail about implementation]
- [Key technical decisions]
- [Notable features]

## Testing
- **[X] comprehensive tests** across [Y] test files
- **All tests passing** ✅
- Thread safety verified (if applicable)
- Performance benchmarks met (if applicable)
- >95% code coverage

## Files Changed
- `src/torematrix/[path]/` - [Description of changes]
  - `file1.py` - [What it does]
  - `file2.py` - [What it does]
- `tests/unit/[path]/` - Comprehensive test suite
  - `test_file1.py` - [X] tests
  - `test_file2.py` - [Y] tests

## Acceptance Criteria ✅
1. ✅ [Criterion 1 from issue]
2. ✅ [Criterion 2 from issue]
3. ✅ [Criterion 3 from issue]
[... all criteria listed in the sub-issue]

## Integration Notes
[Any important notes for other agents about how to integrate with this component]

Closes #[sub-issue-number]

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)" --base main
```

### 4️⃣ Update Main Issue
```bash
# Comment on the main parent issue
gh issue comment [main-issue-number] --body "$(cat <<'EOF'
## ✅ Agent [X] - [Component Name] COMPLETE

I have successfully completed **Issue #[sub-issue-number]: [Component Description]**.

### Implementation Summary:
- ✅ **[Major Achievement 1]** - [Brief description]
- ✅ **[Major Achievement 2]** - [Brief description]
- ✅ **[Major Achievement 3]** - [Brief description]
- ✅ **[Additional achievements...]**

### Testing Results:
- **[X] tests** implemented and **ALL PASSING** ✅
- Thread safety verified (if applicable)
- Performance targets met (if applicable)
- >95% code coverage achieved

### Pull Request:
- PR #[PR-number]: [GitHub PR URL]
- Ready for review and merge

The [component name] is now complete and ready for integration by other agents!

🤖 Agent [X] signing off
EOF
)"
```

### 5️⃣ Cross-Check Implementation Tasks & Acceptance Criteria
```bash
# FIRST: Update issue body to tick all completed checkboxes
gh issue edit [sub-issue-number] --body "$(cat <<'EOF'
[Copy the entire original issue body and replace all [ ] with [x] for completed tasks]
EOF
)"

# THEN: Add comprehensive implementation checklist comment
gh issue comment [sub-issue-number] --body "$(cat <<'EOF'
## ✅ Implementation Tasks - All Done ☑️

### 🔧 **Core Implementation Tasks:**
- ☑️ [Task 1 from issue requirements]
- ☑️ [Task 2 from issue requirements]
- ☑️ [Task 3 from issue requirements]
- ☑️ [Additional implementation tasks...]

### 🧪 **Acceptance Criteria - All Met ☑️**
- ☑️ [Acceptance criterion 1]
- ☑️ [Acceptance criterion 2] 
- ☑️ [Acceptance criterion 3]
- ☑️ [Additional acceptance criteria...]

### 📊 **Testing Cross-Checked ☑️**
- ☑️ [Test category 1] - **PASSING**
- ☑️ [Test category 2] - **PASSING**
- ☑️ [Test category 3] - **PASSING**
- ☑️ Integration tests with other agents - **PASSING**
- ☑️ Performance benchmarks - **PASSING**

### 📋 **Reports Added to GitHub ☑️**
- ☑️ Complete implementation report
- ☑️ Test results and coverage report
- ☑️ Integration documentation
- ☑️ Performance benchmarks
- ☑️ API documentation and examples

**ALL IMPLEMENTATION TASKS COMPLETED AND CROSS-CHECKED** ✅
EOF
)"
```

### 6️⃣ Close Sub-Issue
```bash
# Close the sub-issue with final completion summary
gh issue close [sub-issue-number] --comment "$(cat <<'EOF'
## 🎯 Sub-Issue #[sub-issue-number] COMPLETED

**[Issue Title]** has been **100% completed** by Agent [X].

### ✅ **Final Status:**
- **All implementation tasks**: ☑️ DONE
- **All acceptance criteria**: ☑️ MET
- **Full testing coverage**: ☑️ VERIFIED
- **Reports and documentation**: ☑️ ADDED
- **Integration verified**: ☑️ CONFIRMED
- **Pull Request**: [#PR-number] ☑️ READY

### 📊 **Deliverables Summary:**
- **[X] files** implemented with **[Y] lines** of production code
- **100% core functionality** tested and verified
- **[Key capability 1]** implemented
- **[Key capability 2]** implemented
- **Full integration** with other agent components

**Agent [X] mission accomplished!** This sub-issue contributes to the overall **[Parent Issue Title] #[parent-issue-number]**.

Closing as completed. 🚀
EOF
)"
```

### 6️⃣ Update Issue Task Lists
```bash
# **CRITICAL**: Update both parent issue and sub-issue task lists to reflect completion
# This step is essential for proper project tracking and documentation

# Update the sub-issue to tick off completed implementation tasks
gh issue edit [sub-issue-number] --body "$(gh issue view [sub-issue-number] --json body -q .body | sed 's/- \[ \]/- [x]/g')"

# Update the parent issue to tick off completed acceptance criteria  
gh issue edit [parent-issue-number] --body "$(gh issue view [parent-issue-number] --json body -q .body | sed 's/- \[ \]/- [x]/g')"

# Add completion comment to parent issue if needed
gh issue comment [parent-issue-number] --body "📋 Updated task lists to reflect Agent [X] completion of Sub-Issue #[sub-issue-number]"
```

### 📝 Important Notes:
- **CRITICAL**: Always complete steps 5 & 6 - cross-check tasks and close sub-issue
- **MANDATORY**: In step 5, FIRST tick all checkboxes in the issue body, THEN add checklist comment
- Replace all placeholders in square brackets `[...]` with actual values
- Ensure all tests pass before proceeding
- Include specific metrics and achievements
- Reference the correct issue numbers
- Use consistent formatting across all agents
- **Never skip the final cross-check and closure steps**
- **Must visually tick all [ ] checkboxes to [x] in the GitHub issue**

### 🎯 This routine ensures:
- **Complete task verification** with cross-checking
- **Proper sub-issue closure** with full documentation
- Consistent completion reporting
- Proper GitHub workflow
- Clear communication to other agents
- Professional documentation
- Traceability of all work done

## 🔨 Work Session Log

### Major Achievements This Session
- ✅ **Completed Agent 4** - File Format Support & Testing Implementation (Issue #6.4/#80)
- ✅ **Enhanced Agent 3 Integration** - Intelligent strategy selection and optimization
- ✅ **Repository Cleanup** - Merged 15+ feature branches, cleaned outdated code
- ✅ **Issue #7 Assessment** - Automated success criteria testing (43% complete)
- ✅ **Documentation Updates** - CLAUDE.md reflects current advanced state

### Key Learnings & Advancements
1. **Multi-Agent Coordination** - Successfully coordinated 4 agents across 5 major issues
2. **Production-Ready Quality** - 19 file format support, >95% test coverage, async architecture
3. **Integration Patterns** - Bridge pattern for Agent 3 optimization with graceful fallbacks
4. **Repository Management** - Clean branch strategy, proper merge workflows, comprehensive tracking
5. **Assessment Tools** - Automated success criteria validation for project management

### Current Codebase State
- **15+ major system components** implemented and tested
- **5 major issues completed** (Event Bus, State, Config, Storage, Unstructured)
- **19 file format handlers** with validation and quality scoring
- **Comprehensive test coverage** across all components
- **Clean architecture** maintained with async, typing, and documentation

### Repository Status: SYNCHRONIZED
- ✅ Local repository fully synced with GitHub
- ✅ All branches cleaned and organized
- ✅ All completed work properly merged
- ✅ No outstanding conflicts or merge issues

---
*V3 Development - Major progress achieved through systematic multi-agent implementation*