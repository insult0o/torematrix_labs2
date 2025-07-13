# AGENT 2 PROMPT - PDF.js Qt-JavaScript Communication Bridge

## 📋 Your Mission
You are Agent 2, responsible for implementing bidirectional communication between Qt and PDF.js using QWebChannel. You enable element highlighting and event integration.

## 📖 Required Reading (READ THESE FILES FIRST)
Before starting any work, you MUST read these files in order:

1. **Project Context**: `/home/insulto/torematrix_labs2/CLAUDE.md`
2. **Your Detailed Instructions**: `/home/insulto/torematrix_labs2/AGENT_2_PDFJS.md`
3. **Coordination Guide**: `/home/insulto/torematrix_labs2/PDFJS_COORDINATION.md`
4. **Agent 1's Work**: `/home/insulto/torematrix_labs2/AGENT_1_PDFJS.md` (understand what you'll build on)
5. **Your GitHub Issue**: Run `gh issue view 125` to see full requirements
6. **Event Bus Documentation**: Find and read existing Event Bus implementation from Issue #1

## 🕐 When You Start
**Timeline**: Day 2-3 (you start AFTER Agent 1 completes foundation)

**Prerequisites**: 
- Agent 1 must have PDFViewer class working
- Basic PDF rendering must be functional
- QWebEngineView integration must be complete

## 🎯 Your Specific Tasks Summary
After reading the files above, you will implement:

### Day 2: Bridge Setup
- Configure QWebChannel in Agent 1's PDFViewer
- Create `PDFBridge(QObject)` class for Qt-side communication
- Implement `bridge.js` for PDF.js-side communication
- Set up basic message passing and verification

### Day 3: Advanced Communication
- Implement element highlighting system in PDF.js
- Create coordinate mapping between PDF and elements  
- Integrate with Event Bus from Issue #1
- Add error handling and recovery mechanisms

## 📁 Files You Will Create
```
src/torematrix/integrations/pdf/bridge.py
src/torematrix/integrations/pdf/communication.py
resources/pdfjs/bridge.js
tests/integration/pdf/test_bridge.py
tests/integration/pdf/__init__.py
```

## 🔌 Communication Protocol You Must Implement
```typescript
interface HighlightMessage {
    type: 'highlight'
    elements: ElementCoordinate[]
    style: HighlightStyle
}

interface SelectionMessage {
    type: 'selection'
    coordinates: PDFCoordinate
    element: ElementData
}

interface ErrorMessage {
    type: 'error'
    code: string
    message: string
    context: any
}
```

## ⚡ Performance Targets You Must Meet
- Message latency: <10ms for standard operations
- Highlight response: <50ms for element highlighting
- Event forwarding: <5ms to Event Bus
- Memory overhead: <10MB for bridge operations

## 🔗 Integration Requirements
Your work depends on:
- **Agent 1**: PDFViewer instance (must be completed first)
- **Event Bus (#1)**: For event forwarding (read existing implementation)

Your work enables:
- **Agent 3**: Performance monitoring through your bridge
- **Agent 4**: Advanced features using your communication layer

## ✅ Definition of Done
- [ ] Bidirectional Qt-JS communication functional
- [ ] Element highlighting working accurately
- [ ] Event forwarding to Event Bus operational
- [ ] QWebChannel properly configured
- [ ] Error recovery mechanisms robust
- [ ] Integration tests >90% coverage
- [ ] Documentation written
- [ ] Ready for Agent 3-4 feature integration

## 🚀 Getting Started
1. Read all the files listed above
2. Wait for Agent 1 to complete and notify you
3. Create your branch: `git checkout -b feature/pdfjs-bridge`
4. Study Agent 1's PDFViewer implementation
5. Set up QWebChannel integration first
6. Build bridge communication step by step
7. Test communication thoroughly before proceeding

## 📞 Communication
- Coordinate with Agent 1 for handoff timing
- Update your GitHub issue #125 with daily progress
- Test integration with Agent 1's viewer continuously
- Notify Agent 3 and 4 when your bridge is ready

**Your bridge is the foundation for all advanced features!**