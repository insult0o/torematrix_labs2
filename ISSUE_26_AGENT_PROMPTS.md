# Issue #26: Agent Deployment Prompts for Manual Validation Area Selection Tools

## 🎯 **Deployment Instructions**

This document contains the exact prompts to deploy each agent for Issue #26 implementation. Use these prompts in sequence to ensure proper multi-agent coordination and dependency management.

---

## 🚀 **Agent 1 Deployment - Core Validation Framework**

### **Pre-Deployment Checklist**
- [ ] Current branch: Clean main branch or designated starting branch
- [ ] No conflicting validation files in working directory
- [ ] All previous work committed and pushed

### **Agent 1 Deployment Command**
```bash
git checkout -b feature/validation-core-agent1-issue26-1
```

### **Agent 1 Deployment Prompt**
```
I need you to work on Sub-Issue #26.1 - Core Validation Framework. 

Implement the foundational validation framework with state management, basic area selection, and integration hooks for the TORE Matrix Labs manual validation system.

Key Requirements:
1. Create DrawingStateManager with complete PyQt6 signal-based state machine (IDLE, SELECTING, SELECTED, DRAWING, CONFIRMING modes)
2. Implement ValidationAreaSelector with basic rectangle and polygon selection support
3. Build SelectionShape infrastructure (base classes, RectangleShape, PolygonShape)
4. Create integration hooks and event system for Agent 2-4 coordination
5. Achieve >95% test coverage with comprehensive unit tests
6. Establish performance benchmarks for Agent 2-4 optimization

Files to create/modify:
- src/torematrix/ui/tools/validation/drawing_state.py
- src/torematrix/ui/tools/validation/area_select.py  
- src/torematrix/ui/tools/validation/shapes.py
- src/torematrix/ui/tools/validation/__init__.py
- tests/unit/validation/test_drawing_state.py
- tests/unit/validation/test_area_select.py
- tests/unit/validation/test_shapes.py

Technical Specifications:
- Use PyQt6 6.6+ exclusively
- Full type hints throughout all code
- Clean architecture with dependency injection
- Event-driven design with Qt signals
- Memory-efficient for 1000+ element documents
- Cross-platform compatibility (Windows, macOS, Linux)

Success Criteria:
- All core APIs implemented and documented
- >95% unit test coverage achieved
- Performance benchmarks established (<100ms selection response)
- Integration hooks ready for Agent 2-4
- Signal framework fully operational

This is Agent 1 of a 4-agent implementation. Agent 2 and 3 will build on your foundation, so focus on creating stable, well-documented APIs that they can extend.
```

---

## 🔧 **Agent 2 Deployment - Advanced Area Selection Tools**

### **Pre-Deployment Requirements**
- [ ] Agent 1 implementation complete and tested
- [ ] Agent 1 branch merged to integration branch
- [ ] Agent 1 APIs documented and stable

### **Agent 2 Deployment Command**
```bash
git checkout -b feature/validation-selection-agent2-issue26-2
git merge feature/validation-core-agent1-issue26-1  # Include Agent 1 work
```

### **Agent 2 Deployment Prompt**
```
I need you to work on Sub-Issue #26.2 - Advanced Area Selection Tools.

Build enhanced selection tools with intelligent snapping algorithms, magnetic edge detection, and performance-optimized selection capabilities on top of Agent 1's core validation framework.

Dependencies:
- Agent 1 core framework (DrawingStateManager, ValidationAreaSelector, SelectionShape)
- Build on existing Agent 1 APIs without breaking changes

Key Requirements:
1. Implement SnapEngine with magnetic field detection and sub-5ms snap response
2. Create advanced shape tools (FreehandShape with smoothing, enhanced polygon editing)
3. Build SmartBoundaryDetector for intelligent element boundary detection
4. Implement MultiAreaSelectionManager for concurrent area selection
5. Develop SpatialIndex for efficient collision detection in large documents
6. Create performance optimization system (60 FPS operation, <10MB memory overhead)

Files to create/modify:
- src/torematrix/ui/tools/validation/snapping.py
- src/torematrix/ui/tools/validation/enhanced_shapes.py
- src/torematrix/ui/tools/validation/selection_algorithms.py
- src/torematrix/ui/tools/validation/performance.py
- Extend src/torematrix/ui/tools/validation/area_select.py (EnhancedValidationAreaSelector)
- tests/unit/validation/test_snapping.py
- tests/unit/validation/test_enhanced_shapes.py
- tests/performance/test_selection_performance.py

Technical Specifications:
- Integrate seamlessly with Agent 1's DrawingStateManager
- Extend Agent 1's SelectionShape classes
- Use Agent 1's PyQt6 signal framework
- Maintain Agent 1's performance benchmarks
- Prepare integration points for Agent 3 UI components

Advanced Features:
- Magnetic snapping with customizable strength and radius
- Catmull-Rom spline smoothing for freehand selections
- Real-time boundary suggestions and selection improvements
- Batch collision detection for performance
- Multi-threaded processing for large documents

Success Criteria:
- Snap detection <5ms for 1000+ targets
- Boundary detection <50ms for complex elements
- Multi-area operations <100ms for 50+ selections
- Memory usage <10MB for 10,000+ elements
- 60 FPS rendering with 100+ active selections
- Full integration with Agent 1 foundation
- APIs ready for Agent 3 UI integration

This is Agent 2 of a 4-agent implementation. You're building on Agent 1's foundation and preparing for Agent 3's UI components. Focus on performance and creating smooth, responsive selection tools.
```

---

## 🎨 **Agent 3 Deployment - UI Components & User Experience**

### **Pre-Deployment Requirements**
- [ ] Agent 1 foundation complete and stable
- [ ] Agent 2 advanced selection tools implemented
- [ ] Agent 1+2 integration tested successfully

### **Agent 3 Deployment Command**
```bash
git checkout -b feature/validation-ui-agent3-issue26-3
git merge feature/validation-core-agent1-issue26-1      # Include Agent 1 work
git merge feature/validation-selection-agent2-issue26-2  # Include Agent 2 work
```

### **Agent 3 Deployment Prompt**
```
I need you to work on Sub-Issue #26.3 - UI Components & User Experience.

Create professional, intuitive UI components and comprehensive user experience workflows that integrate Agent 1's core framework and Agent 2's advanced selection tools into a cohesive manual validation system.

Dependencies:
- Agent 1: DrawingStateManager, ValidationAreaSelector, SelectionShape infrastructure
- Agent 2: SnapEngine, SmartBoundaryDetector, MultiAreaSelectionManager, enhanced selection tools

Key Requirements:
1. Create ValidationWizard with 6-step workflow (Welcome → Area Selection → OCR → Text Review → Element Type → Final Review)
2. Implement ValidationToolbar with contextual controls and real-time status display
3. Build advanced OCRDialog with confidence highlighting and text editing capabilities
4. Design professional UI components with accessibility compliance (WCAG 2.1 AA)
5. Create responsive, intuitive user experience with <100ms response times
6. Integrate seamlessly with Agent 1 state management and Agent 2 selection tools

Files to create/modify:
- src/torematrix/ui/tools/validation/wizard.py
- src/torematrix/ui/tools/validation/toolbar.py
- src/torematrix/ui/tools/validation/ocr_dialog.py
- src/torematrix/ui/tools/validation/ui_components.py
- Extend src/torematrix/ui/tools/validation/__init__.py
- tests/unit/validation/test_wizard.py
- tests/unit/validation/test_toolbar.py
- tests/unit/validation/test_ocr_dialog.py
- tests/ui/validation/test_ui_workflows.py

Technical Specifications:
- Use PyQt6 6.6+ with modern Qt styling
- Integrate with Agent 1's DrawingStateManager signals
- Utilize Agent 2's SnapEngine for UI feedback
- Professional visual design with consistent styling
- Full keyboard navigation and accessibility support
- Responsive design that scales with different screen sizes

UI Component Details:
ValidationWizard:
- Multi-step workflow with progress tracking
- Integration with Agent 1 area selection
- Real-time feedback from Agent 2 snapping
- OCR processing and text review steps
- Element classification and metadata entry

ValidationToolbar:
- Tool selection (rectangle, polygon, freehand, magic select)
- Mode controls (snapping, multi-selection)
- Status indicators and progress display
- Contextual button states based on Agent 1 drawing state

OCRDialog:
- Confidence-based text highlighting
- Side-by-side original/corrected text view
- Word-level confidence visualization
- Text editing tools and spell checking

Success Criteria:
- Complete 6-step validation wizard functional
- Toolbar integrates with Agent 1+2 selection tools
- OCR dialog provides professional text editing experience
- <100ms UI response times achieved
- WCAG 2.1 AA accessibility compliance
- Professional visual design and consistent styling
- Full integration with Agent 1 state management
- Utilizes Agent 2 advanced selection features
- APIs ready for Agent 4 integration layer

This is Agent 3 of a 4-agent implementation. You're creating the user-facing components that bring together Agent 1's foundation and Agent 2's advanced tools into an intuitive, professional interface.
```

---

## 🔗 **Agent 4 Deployment - Integration & Production Readiness**

### **Pre-Deployment Requirements**
- [ ] Agent 1 foundation complete and tested
- [ ] Agent 2 advanced selection tools implemented and integrated
- [ ] Agent 3 UI components complete and functional
- [ ] Agent 1+2+3 integration testing successful

### **Agent 4 Deployment Command**
```bash
git checkout -b feature/validation-integration-agent4-issue26-4
git merge feature/validation-core-agent1-issue26-1      # Include Agent 1 work
git merge feature/validation-selection-agent2-issue26-2  # Include Agent 2 work
git merge feature/validation-ui-agent3-issue26-3        # Include Agent 3 work
```

### **Agent 4 Deployment Prompt**
```
I need you to work on Sub-Issue #26.4 - Integration & Production Readiness.

Create the unified ValidationToolsIntegration interface, comprehensive testing framework, production configuration system, and complete documentation to make the manual validation system enterprise-ready for deployment.

Dependencies:
- Agent 1: DrawingStateManager, ValidationAreaSelector, SelectionShape infrastructure
- Agent 2: SnapEngine, SmartBoundaryDetector, advanced selection tools, performance optimization
- Agent 3: ValidationWizard, ValidationToolbar, OCRDialog, complete UI workflows

Key Requirements:
1. Create ValidationToolsIntegration unified interface that coordinates all Agent 1-3 components
2. Implement comprehensive testing framework (unit, integration, performance, load tests)
3. Build production configuration system with monitoring and alerting
4. Generate complete API documentation with working examples
5. Create deployment automation and production readiness features
6. Achieve >95% test coverage across entire validation system

Files to create/modify:
- src/torematrix/ui/tools/validation/integration.py
- src/torematrix/ui/tools/validation/production_config.py
- src/torematrix/ui/tools/validation/monitoring.py
- tests/integration/validation/test_full_workflow.py
- tests/integration/validation/test_agent_coordination.py
- tests/performance/validation/test_system_performance.py
- tests/load/validation/test_concurrent_sessions.py
- docs/api/validation_tools_api.md
- docs/user_guides/validation_workflow_guide.md
- examples/validation_examples.py

Technical Specifications:
- Coordinate all Agent 1-3 components seamlessly
- Provide single unified API for external systems
- Production-ready error handling and recovery
- Comprehensive logging and monitoring
- Configuration management for different environments
- Performance monitoring and alerting system

Integration Requirements:
ValidationToolsIntegration API:
- start_validation_session() - Initialize complete workflow
- process_page() - Coordinate page processing across components
- validate_element() - Handle element validation with OCR
- complete_session() - Finalize and cleanup validation session

Testing Framework:
- Unit tests for all components (>95% coverage)
- Integration tests for cross-component workflows
- Performance tests against established benchmarks
- Load tests for concurrent session handling
- UI workflow tests for complete user experience

Production Features:
- Structured logging with rotation and archiving
- Health checks and monitoring endpoints
- Configuration validation and environment management
- Error recovery and graceful degradation
- Performance alerting and optimization suggestions

Success Criteria:
- Unified ValidationToolsIntegration interface functional
- >95% test coverage across all components
- All performance benchmarks met consistently
- Production configuration system operational
- Complete API documentation with examples
- Load testing successful (10+ concurrent sessions)
- Monitoring and alerting system functional
- Deployment automation complete

This is Agent 4 of a 4-agent implementation. You're responsible for bringing everything together into a production-ready system that enterprises can deploy with confidence. Focus on integration quality, comprehensive testing, and operational readiness.
```

---

## 🔄 **Multi-Agent Coordination Commands**

### **Sequential Deployment Strategy**
```bash
# Deploy Agent 1 first (Foundation)
"I need you to work on Sub-Issue #26.1 - Core Validation Framework..."

# Wait for Agent 1 completion, then deploy Agent 2 and 3 in parallel
"I need you to work on Sub-Issue #26.2 - Advanced Area Selection Tools..."
"I need you to work on Sub-Issue #26.3 - UI Components & User Experience..."

# Wait for Agent 2 and 3 completion, then deploy Agent 4
"I need you to work on Sub-Issue #26.4 - Integration & Production Readiness..."
```

### **Integration Verification Commands**
```bash
# After each agent completion
"Run integration tests for validation components"
"Verify Agent X APIs are ready for next agent"
"Confirm performance benchmarks are met"
"Check cross-agent compatibility"
```

### **Final Deployment Command**
```bash
# After all agents complete
"Complete Issue #26 integration and prepare for production deployment"
```

---

## ✅ **Deployment Checklist**

### **Pre-Agent 1 Deployment**
- [ ] Clean working directory
- [ ] GitHub sub-issues created (#26.1, #26.2, #26.3, #26.4)
- [ ] Branch strategy confirmed
- [ ] Agent instruction files reviewed

### **Pre-Agent 2 Deployment**
- [ ] Agent 1 implementation complete
- [ ] Agent 1 tests passing (>95% coverage)
- [ ] Agent 1 APIs documented
- [ ] Agent 1 performance benchmarks established

### **Pre-Agent 3 Deployment**  
- [ ] Agent 1 foundation stable
- [ ] Agent 2 advanced features implemented
- [ ] Agent 1+2 integration tested
- [ ] APIs ready for UI integration

### **Pre-Agent 4 Deployment**
- [ ] Agent 1 foundation complete
- [ ] Agent 2 advanced tools functional
- [ ] Agent 3 UI components implemented
- [ ] Agent 1+2+3 integration successful

### **Post-Agent 4 Deployment**
- [ ] Complete system integration tested
- [ ] All performance benchmarks met
- [ ] Production configuration validated
- [ ] Documentation complete
- [ ] Deployment readiness confirmed

---

**Agent Deployment Prompts Ready** 🚀

These prompts ensure proper sequential deployment of all 4 agents with clear dependencies, integration points, and success criteria for implementing Issue #26 Manual Validation Area Selection Tools.