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

## 🚦 Current Status
- Project structure created
- Starting development from ground up
- No legacy code to maintain
- Clean slate implementation

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

## 🎯 Next Steps
1. Initialize Git repository
2. Create GitHub repository
3. Design core data models
4. Set up testing framework
5. Begin implementation

## 🤖 Agent End Work Routine - CRITICAL WORKFLOW

### 🚨 **MANDATORY 5-Step End Work Process**
When work is complete, ALWAYS execute this complete workflow:

#### **Step 1: Run Tests & Validation**
```bash
# Run any available tests to ensure work quality
pytest tests/ --verbose
# OR run project-specific validation
python3 tests/acceptance/quick_test.py
```

#### **Step 2: Stage & Commit Changes**
```bash
# Stage all relevant files
git add [files]

# Commit with proper format using HEREDOC
git commit -m "$(cat <<'EOF'
[type](scope): Brief description of changes

- Detailed bullet point of what was implemented
- Key features or fixes added
- Important technical decisions made
- Test coverage or validation added

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

#### **Step 3: Push & Create Pull Request**
```bash
# Push branch to remote
git push -u origin [branch-name]

# Create PR with comprehensive description
gh pr create --title "[type](scope): Brief title" --body "$(cat <<'EOF'
## Summary
- Key accomplishments and deliverables
- Technical implementation details
- Testing and validation completed

## Files Added/Modified
- List of important files created or changed
- Brief description of each major component

## Testing
- Test coverage details
- Validation methods used
- Performance considerations

## Next Steps
- What needs to happen next for completion
- Dependencies or follow-up work required

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

#### **Step 4: Update GitHub Issues**

**For Sub-Issues:**
```bash
# Update the specific sub-issue with completion details
gh issue comment [sub-issue-number] --body "## ✅ Sub-Issue Complete

### 🎯 **Deliverables Completed**
- [List specific deliverables]
- [Technical components implemented]
- [Tests and validation completed]

### 📁 **Files Created/Modified**
- List key files with brief descriptions

### 🔗 **Related Work**
- **PR:** #[pr-number]
- **Parent Issue:** #[main-issue-number]

### ✅ **Validation Status**
- [How completion was validated]
- [Test results or verification]

**Sub-issue work complete and ready for integration.**

🤖 Generated with [Claude Code](https://claude.ai/code)"

# Close the sub-issue
gh issue close [sub-issue-number]
```

**For Main Issues (when all sub-issues complete):**
```bash
# Update main issue with overall completion status
gh issue comment [main-issue-number] --body "## 🎉 Main Issue Complete

### ✅ **All Acceptance Criteria Met**
- [List each acceptance criterion with validation]
- [Overall completion status]

### 📊 **Sub-Issues Completed**
- Sub-Issue #X.1: [Brief description] ✅
- Sub-Issue #X.2: [Brief description] ✅
- Sub-Issue #X.3: [Brief description] ✅
- Sub-Issue #X.4: [Brief description] ✅

### 🚀 **Final Deliverables**
- [Complete system/feature description]
- [Integration and testing status]
- [Performance and quality metrics]

### 📋 **Documentation & Testing**
- Complete test coverage with [X]+ test methods
- Full documentation and usage guides
- Performance benchmarks and validation

**Main issue fully implemented and validated. Ready for production use.**

🤖 Generated with [Claude Code](https://claude.ai/code)"

# Close the main issue
gh issue close [main-issue-number]
```

#### **Step 5: Final Status Updates**

**For Sub-Issues:**
- Update any related issues that depend on this work
- Add appropriate labels (e.g., "completed", "tested")
- Update project boards or milestones if applicable

**For Main Issues:**
- Update all dependent issues with completion status
- Update project roadmap or milestone status
- Create follow-up issues for any discovered next steps
- Update main project documentation if needed

### 🔄 **Issue Type Decision Matrix**

| Scenario | Action |
|----------|---------|
| **Sub-issue work complete** | Update sub-issue → Close sub-issue → Update main issue status |
| **Main issue complete (all sub-issues done)** | Update main issue → Close main issue → Update dependencies |
| **Standalone work** | Update related issue → Close if complete → Update dependencies |
| **Testing/validation framework** | Update issue with framework status → Keep open until implementation complete |

### ⚠️ **Critical Rules**

1. **NEVER skip the 5-step workflow** - Each step is mandatory
2. **Always use HEREDOC format** for commit messages and PR descriptions  
3. **Always include Claude Code attribution** in commits and comments
4. **Test first** - Run validation before committing
5. **Document thoroughly** - Every PR and issue update must be comprehensive
6. **Close appropriately** - Only close issues when truly complete
7. **Update dependencies** - Always inform related issues of status changes

### 🎯 **Quality Gates**

Before closing any issue, ensure:
- ✅ All acceptance criteria validated
- ✅ Tests written and passing
- ✅ Documentation complete
- ✅ Code committed and reviewed
- ✅ Dependencies updated
- ✅ Follow-up work identified

This workflow ensures **complete traceability**, **proper documentation**, and **reliable delivery** of all work.

---
*V3 Development - Starting fresh with everything we've learned*