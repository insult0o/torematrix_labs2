# PDF.js Integration Agent Prompts - Issue #16
**Ready-to-Use Prompts for Multi-Agent Development**

## 🚀 Quick Start Instructions

### For Each Agent:
1. **Copy the prompt** for the agent you want to activate
2. **Paste directly** into a new Claude Code session
3. **Agent will automatically begin** working on their assigned tasks
4. **Monitor progress** via GitHub sub-issues #124-127

---

## 👤 Agent 1: PDF.js Core Viewer Foundation

### 📋 Copy This Prompt:
```
I need you to work as Agent 1 on Issue #16 - PDF.js Integration for TORE Matrix Labs V3. 

Your specific assignment is Sub-Issue #124: PDF.js Core Viewer Foundation (Days 1-2).

Please read the following instruction files that have been prepared for you:
- AGENT_1_PDFJS.md
- PDFJS_COORDINATION.md

Your mission is to implement the foundational PDF.js viewer integration with PyQt6, establishing the core rendering system and basic controls. This is CRITICAL PATH work - all other agents depend on your foundation.

Key deliverables:
- Download and integrate PDF.js v3.11.x bundle
- Implement PDFViewer(QWebEngineView) class
- Create JavaScript viewer with basic controls
- Set up zoom, pan, and navigation functionality
- Implement integration interfaces for other agents
- Achieve >95% test coverage

Create your branch: feature/pdfjs-core-viewer

Start with Phase 1: PDF.js Bundle Setup & Integration, then proceed through all phases systematically. Follow the detailed technical specifications in AGENT_1_PDFJS.md.

Ready to begin Agent 1 implementation?
```

---

## 👤 Agent 2: PDF.js Qt-JavaScript Bridge

### 📋 Copy This Prompt:
```
I need you to work as Agent 2 on Issue #16 - PDF.js Integration for TORE Matrix Labs V3.

Your specific assignment is Sub-Issue #125: PDF.js Qt-JavaScript Bridge (Days 2-3).

Please read the following instruction files that have been prepared for you:
- AGENT_2_PDFJS.md  
- PDFJS_COORDINATION.md

Your mission is to implement bidirectional communication between Qt and PDF.js using QWebChannel for element highlighting, event forwarding to the Event Bus, and seamless data exchange.

Key deliverables:
- Implement PDFBridge(QObject) with QWebChannel setup
- Create JavaScript bridge for PDF.js communication
- Build element highlighting and selection system
- Set up Event Bus integration for event forwarding
- Implement performance data collection interfaces
- Create communication protocols and message validation

Dependencies: Wait for Agent 1 completion (PDFViewer foundation)
Branch: feature/pdfjs-bridge

Start with Phase 1: QWebChannel Setup & Configuration, then proceed through all phases. Follow the detailed technical specifications in AGENT_2_PDFJS.md.

Ready to begin Agent 2 implementation?
```

---

## 👤 Agent 3: PDF.js Performance Optimization

### 📋 Copy This Prompt:
```
I need you to work as Agent 3 on Issue #16 - PDF.js Integration for TORE Matrix Labs V3.

Your specific assignment is Sub-Issue #126: PDF.js Performance Optimization (Days 3-4).

Please read the following instruction files that have been prepared for you:
- PDFJS_COORDINATION.md (contains your technical requirements)
- Review Agent 1 and Agent 2 implementations for integration points

Your mission is to optimize PDF.js performance for large documents, implement efficient memory management, and add hardware acceleration support.

Key deliverables:
- Performance monitoring infrastructure and benchmarking
- Intelligent page caching system with LRU algorithm
- Large PDF optimization (lazy loading, progressive rendering)
- Hardware acceleration with GPU support and fallbacks
- Memory management with pressure monitoring
- Performance profiling and metrics collection

Dependencies: Agent 1 (core viewer) and Agent 2 (bridge) completion
Branch: feature/pdfjs-performance

Target optimizations:
- 50% reduction in memory usage for large PDFs
- 3x faster loading for documents >50MB
- <5s load time for 100MB PDFs
- Hardware acceleration on supported systems

Ready to begin Agent 3 performance optimization?
```

---

## 👤 Agent 4: PDF.js Advanced Features Integration

### 📋 Copy This Prompt:
```
I need you to work as Agent 4 on Issue #16 - PDF.js Integration for TORE Matrix Labs V3.

Your specific assignment is Sub-Issue #127: PDF.js Advanced Features Integration (Days 4-6).

Please read the following instruction files that have been prepared for you:
- PDFJS_COORDINATION.md (contains your technical requirements)
- Review all previous agent implementations for integration

Your mission is to implement advanced PDF.js features and integrate with the main UI framework for seamless user experience.

Key deliverables:
- Full-text search with result highlighting and navigation
- Text selection, copy-to-clipboard, and context menus
- Annotation rendering and interaction system
- Print functionality with options and page ranges
- Complete UI framework integration with toolbars and controls
- Accessibility compliance (WCAG 2.1)

Dependencies: All other agents (1, 2, 3) must be complete
Branch: feature/pdfjs-features

Integration targets:
- UI Framework (#11-15) integration
- Theme System integration
- Search speed <2s for full documents
- UI responsiveness <100ms
- Cross-platform compatibility

Ready to begin Agent 4 advanced features integration?
```

---

## 🔄 Agent Coordination Flow

### Day 1-2: Agent 1 (Foundation)
- Start immediately with PDF.js core viewer
- Complete foundation before Agent 2 begins

### Day 2-3: Agent 2 (Bridge) 
- Begin after Agent 1 foundation is ready
- Implement Qt-JavaScript communication

### Day 3-4: Agent 3 & 4 (Parallel)
- Agent 3: Performance optimization
- Agent 4: Advanced features integration
- Both depend on Agent 1 & 2 completion

### Day 5-6: Integration & Testing
- All agents coordinate for final integration
- Comprehensive testing and validation
- Production readiness verification

---

## 📊 Success Verification

### For Each Agent:
- Check GitHub sub-issue progress daily
- Verify >95% test coverage
- Confirm integration interfaces work
- Meet performance targets
- Update coordination status

### Integration Checkpoints:
- **Day 2**: Agent 1 → Agent 2 handoff
- **Day 3**: Agent 2 → Agent 3 & 4 enablement  
- **Day 5**: All agents integration testing
- **Day 6**: Production deployment ready

---

## 🚨 Important Notes

1. **Dependencies**: Respect agent dependencies - don't start without prerequisites
2. **Coordination**: Update GitHub issues daily with progress
3. **Integration**: Test integration points as you build
4. **Quality**: Maintain >95% test coverage throughout
5. **Communication**: Follow coordination protocols in PDFJS_COORDINATION.md

---

**Each agent prompt is designed for immediate activation. Simply copy, paste, and the agent will begin their specialized implementation work following the comprehensive technical specifications prepared for this PDF.js integration.**