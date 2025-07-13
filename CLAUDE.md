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

---
*V3 Development - Starting fresh with everything we've learned*