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
- ✅ **Processing Pipeline Architecture** - Breakdown complete, ready for implementation (Issue #8)
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

## 🎯 Active Development Issues

### Document Ingestion System (Issue #7) - 43% Complete
- ✅ Core Upload Manager & File Validation (Sub-issue #83) - COMPLETED
- 🚧 Queue Management & Batch Processing (Sub-issue #85)  
- 🚧 API Endpoints & WebSocket Progress (Sub-issue #86)
- 🚧 Integration & Testing (Sub-issue #87)

### Document Element Parsers (Issue #9) - Multi-Agent Development Ready
- 🚧 Core Parser Framework & Base Classes (Sub-issue #96) - Agent 1 Ready
- 🚧 Table & List Parsers Implementation (Sub-issue #97) - Agent 2 Ready  
- 🚧 Image & Formula Parsers with OCR (Sub-issue #99) - Agent 3 Ready
- 🚧 Code Parser & Integration System (Sub-issue #101) - Agent 4 Ready

### Metadata Extraction Engine (Issue #10) - Multi-Agent Development Ready
- 🚧 Core Metadata Engine & Schema Framework (Sub-issue #98) - Agent 1 Ready
- 🚧 Relationship Detection & Graph Construction (Sub-issue #100) - Agent 2 Ready
- 🚧 Performance Optimization & Caching (Sub-issue #102) - Agent 3 Ready
- 🚧 Integration, Testing & Production Readiness (Sub-issue #103) - Agent 4 Ready

### Processing Pipeline Architecture (Issue #8) - Breakdown Complete
- 📋 Core Pipeline Manager & DAG Architecture (Sub-issue #88) - Ready for Agent 1
- 📋 Processor Plugin System & Interface (Sub-issue #90) - Ready for Agent 2
- 📋 Worker Pool & Progress Tracking (Sub-issue #91) - Ready for Agent 3
- 📋 Integration, Monitoring & Testing (Sub-issue #92) - Ready for Agent 4

## 24 Plan
- Plan a comprehensive 24-hour development sprint for critical issue resolution
- Define clear objectives and milestones for each component
- Implement continuous integration and testing strategies
- Prepare detailed documentation and progress tracking mechanisms
- Establish real-time communication channels for sprint coordination
- Set up monitoring and alerting systems for immediate issue detection
- Create sprint retrospective and post-mortem documentation template

## 🚀 Development Memories
- 28exe - New memory added to track project context and progress