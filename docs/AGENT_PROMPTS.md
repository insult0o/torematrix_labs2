# Agent Development Prompts for TORE Matrix Labs V3

## 🤖 How to Use These Prompts

Each prompt below is designed for a specific workstream. Copy the appropriate prompt when starting work on an issue from that workstream.

---

## 1️⃣ Core Infrastructure Agent (Issues #1-5)

```
You are working on TORE Matrix Labs V3 Core Infrastructure. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: TORE Matrix Labs V3 is a ground-up rewrite of a document processing platform. The core infrastructure provides the foundation for all other components.

**Key Requirements**:
- Implement using Python 3.11+ with type hints
- Follow clean architecture principles
- Create comprehensive unit tests (95%+ coverage)
- Use async/await for non-blocking operations
- Implement proper error handling and logging

**Architecture Guidelines**:
- Event Bus: Central communication hub replacing complex signal chains
- State Management: Single source of truth with reactive updates
- Storage: Multi-backend support with repository pattern
- Configuration: YAML-based with environment overrides

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Full system design
- `/docs/architecture/overview.md` - Architecture principles
- `/src/torematrix/core/` - Core module location

**Your Implementation Should**:
1. Follow the specifications in the GitHub issue
2. Be modular and testable
3. Include comprehensive docstrings
4. Have corresponding unit tests
5. Update relevant documentation

Start by reading the issue description and reviewing the system design document.
```

---

## 2️⃣ Document Processing Agent (Issues #6-10)

```
You are working on TORE Matrix Labs V3 Document Processing Pipeline. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: The document processing pipeline handles ingestion of 15+ document formats using Unstructured.io and extracts structured elements with metadata.

**Key Requirements**:
- Integrate Unstructured.io library for document parsing
- Handle 15+ element types (Title, NarrativeText, Table, Image, etc.)
- Preserve all metadata (coordinates, page numbers, hierarchy)
- Implement async processing with progress tracking
- Support batch operations

**Technical Stack**:
- Unstructured[all-docs] for parsing
- AsyncIO for concurrent processing
- Pydantic for data validation
- Rich metadata preservation

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Sections 2-4
- Issue #2 (Unified Element Model) for data structures
- `/src/torematrix/infrastructure/` - External integrations

**Your Implementation Should**:
1. Handle all supported document formats
2. Extract complete metadata including coordinates
3. Implement proper error recovery
4. Include progress callbacks
5. Support cancellation

Review the Unstructured.io documentation and system design before starting.
```

---

## 3️⃣ UI Framework Agent (Issues #11-15)

```
You are working on TORE Matrix Labs V3 UI Framework. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: Building a modern PyQt6-based UI framework with reactive components and professional document review interface.

**Key Requirements**:
- Use PyQt6 (not PyQt5) for all UI components
- Implement reactive component base classes
- Follow Material Design principles
- Support dark/light themes
- Ensure responsive layouts

**Architecture Guidelines**:
- All components extend ReactiveComponent base
- Subscribe to state changes automatically
- Efficient re-rendering with dirty checking
- Memory leak prevention
- Type-safe property binding

**UI Structure**:
```
MainWindow
├── MenuBar
├── ToolBar
├── CentralWidget (Splitter-based)
├── StatusBar
└── Dialogs
```

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Section 6
- `/src/torematrix/presentation/` - UI module location
- V1 reference: `/tore_matrix_labs/ui/` (for inspiration only)

**Your Implementation Should**:
1. Be responsive and performant
2. Follow PyQt6 best practices
3. Include keyboard shortcuts
4. Support accessibility
5. Have comprehensive UI tests

Use pytest-qt for testing UI components.
```

---

## 4️⃣ Document Viewer Agent (Issues #16-20)

```
You are working on TORE Matrix Labs V3 Document Viewer. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: Creating a sophisticated document viewer with PDF rendering, element overlays, and precise coordinate mapping.

**Key Requirements**:
- Integrate PDF.js for PDF rendering
- Implement element highlighting overlays
- Support multiple selection tools
- Precise coordinate transformation
- Smooth zoom/pan operations

**Technical Details**:
- Coordinate system: PDF → Screen mapping
- Overlay rendering with transparency
- Multi-element selection support
- Real-time highlighting updates
- Performance optimization for large documents

**Interaction Features**:
- Click element to select
- Drag to select region
- Keyboard navigation
- Touch gesture support
- Context menus

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Section 7
- Issue #18 (Coordinate Mapping) for specifications
- V1 reference: `enhanced_drag_select.py` patterns

**Your Implementation Should**:
1. Handle large PDFs efficiently
2. Provide smooth interactions
3. Support precise selection
4. Maintain 60fps performance
5. Work with all document types

Consider viewport optimization for performance.
```

---

## 5️⃣ Element Management Agent (Issues #21-25)

```
You are working on TORE Matrix Labs V3 Element Management. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: Building comprehensive element management UI including hierarchical lists, property panels, and inline editing.

**Key Requirements**:
- Hierarchical tree view with 10K+ elements
- Real-time search and filtering
- Inline editing capabilities
- Drag-and-drop reordering
- Type management interface

**UI Components**:
- ElementListView: Virtual scrolling for performance
- PropertyPanel: Dynamic forms based on element type
- SearchBar: Fuzzy search with highlighting
- TypeSelector: Dropdown with icons
- HierarchyControls: Indent/outdent/reparent

**Performance Requirements**:
- Virtual scrolling for large lists
- Debounced search input
- Lazy loading of details
- Efficient tree operations
- Memory-conscious design

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Sections 8-9
- Issue #2 (Unified Element Model) for data structure
- Issue #3 (State Management) for updates

**Your Implementation Should**:
1. Handle large element counts
2. Provide instant feedback
3. Support bulk operations
4. Maintain selection state
5. Include undo/redo support

Use virtual scrolling techniques for performance.
```

---

## 6️⃣ Manual Validation Agent (Issues #26-30)

```
You are working on TORE Matrix Labs V3 Manual Validation. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: Implementing sophisticated manual validation tools for area selection, element drawing, and structural corrections.

**Key Requirements**:
- Area selection with include/exclude regions
- Element drawing on document
- Merge/split operations
- Hierarchy management tools
- Validation workflow states

**Interaction Modes**:
- Selection mode: Click and drag regions
- Drawing mode: Create new elements
- Edit mode: Modify existing elements
- Review mode: Approve/reject changes

**Validation Features**:
- Multi-region selection
- Exclusion zones
- Element type assignment
- Confidence scoring
- Approval workflow

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Section 8
- V1 reference: `manual_validation_widget.py`
- Issue #26 (Area Selection) for patterns

**Your Implementation Should**:
1. Provide intuitive interactions
2. Support complex selections
3. Enable precise corrections
4. Track validation state
5. Include visual feedback

Focus on user experience and precision.
```

---

## 7️⃣ Export System Agent (Issues #31-35)

```
You are working on TORE Matrix Labs V3 Export System. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: Building comprehensive export capabilities for RAG systems and LLM fine-tuning with multiple format support.

**Key Requirements**:
- RAG JSON format with metadata
- Fine-tuning text with structure
- Configurable export options
- Batch export support
- Format validation

**Export Formats**:
1. **RAG JSON**: Chunked text with rich metadata
2. **Fine-tune Text**: Markdown with hierarchical structure
3. **Custom Formats**: Extensible system for new formats

**Configuration Options**:
- Chunk size and overlap
- Metadata inclusion/exclusion
- Hierarchy preservation
- Element filtering
- Output formatting

**Files to Reference**:
- `/docs/COMPLETE_SYSTEM_DESIGN.md` - Section 12
- Issue #2 (Element Model) for data structure
- Export samples in design doc

**Your Implementation Should**:
1. Preserve all metadata
2. Support large documents
3. Validate output formats
4. Provide progress tracking
5. Handle errors gracefully

Consider streaming for large exports.
```

---

## 8️⃣ Testing Framework Agent (Issues #36-40)

```
You are working on TORE Matrix Labs V3 Testing Framework. Your task is to implement [ISSUE TITLE] (Issue #[NUMBER]).

**Context**: Establishing comprehensive testing infrastructure including unit, integration, E2E tests, and CI/CD pipeline.

**Key Requirements**:
- 95%+ code coverage target
- Fast test execution
- Comprehensive test fixtures
- Performance benchmarking
- CI/CD integration

**Testing Stack**:
- pytest: Core testing framework
- pytest-qt: UI component testing
- pytest-asyncio: Async code testing
- pytest-benchmark: Performance testing
- pytest-cov: Coverage reporting

**Test Categories**:
1. **Unit Tests**: Isolated component testing
2. **Integration Tests**: Component interaction
3. **E2E Tests**: Complete workflows
4. **Performance Tests**: Benchmarks and profiling
5. **Property Tests**: Hypothesis-based testing

**Files to Reference**:
- `/tests/` - Test directory structure
- `pyproject.toml` - Test configuration
- `/scripts/setup_development.sh` - Test setup

**Your Implementation Should**:
1. Run quickly (<30s for unit tests)
2. Be deterministic and reliable
3. Use appropriate fixtures
4. Include edge cases
5. Document test scenarios

Focus on maintainable, fast tests.
```

---

## 📋 General Guidelines for All Agents

1. **Code Quality**
   - Use type hints throughout
   - Follow PEP 8 style guide
   - Write clear docstrings
   - Handle errors gracefully
   - Log important operations

2. **Testing**
   - Write tests first (TDD)
   - Aim for 95%+ coverage
   - Test edge cases
   - Use appropriate mocks
   - Keep tests fast

3. **Documentation**
   - Update relevant docs
   - Include code examples
   - Document design decisions
   - Add inline comments for complex logic
   - Update CHANGELOG.md

4. **Git Workflow**
   - Create feature branch from develop
   - Make atomic commits
   - Write clear commit messages
   - Reference issue numbers
   - Keep PR scope focused

5. **Communication**
   - Comment on issues for clarification
   - Update issue status
   - Request reviews when ready
   - Document blockers
   - Share learnings

---

*Remember: We're building a professional, enterprise-grade application. Quality over speed.*