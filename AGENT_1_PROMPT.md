# AGENT 1 PROMPT - PDF.js Core Viewer Foundation

## 📋 Your Mission
You are Agent 1, responsible for implementing the foundational PDF.js viewer integration with PyQt6. You are the critical path that enables all other agents.

## 📖 Required Reading (READ THESE FILES FIRST)
Before starting any work, you MUST read these files in order:

1. **Project Context**: `/home/insulto/torematrix_labs2/CLAUDE.md`
2. **Your Detailed Instructions**: `/home/insulto/torematrix_labs2/AGENT_1_PDFJS.md`
3. **Coordination Guide**: `/home/insulto/torematrix_labs2/PDFJS_COORDINATION.md`
4. **Your GitHub Issue**: Run `gh issue view 124` to see full requirements

## 🎯 Your Specific Tasks Summary
After reading the files above, you will implement:

### Day 1: Foundation Setup
- Download and bundle PDF.js v3.11.x 
- Create `resources/pdfjs/` directory structure
- Implement `PDFViewer(QWebEngineView)` class in `src/torematrix/integrations/pdf/viewer.py`
- Create custom `viewer.html` template

### Day 2: Core Functionality  
- Add zoom controls (25%-500%, fit-width, fit-page)
- Implement pan functionality (mouse/touch)
- Add page navigation (next/prev/goto)
- Implement memory management and cleanup

## 📁 Files You Will Create
```
src/torematrix/integrations/pdf/viewer.py
src/torematrix/integrations/pdf/__init__.py
resources/pdfjs/pdf.min.js
resources/pdfjs/pdf.worker.min.js
resources/pdfjs/viewer.html
resources/pdfjs/viewer.css
resources/pdfjs/viewer.js
tests/unit/pdf/test_viewer.py
tests/unit/pdf/__init__.py
```

## ⚡ Performance Targets You Must Meet
- Load time: <2s for 10MB PDFs
- Memory: <50MB baseline + 5MB per 10 pages  
- Zoom response: <100ms
- Navigation: <50ms page transitions

## 🔗 Integration Requirements
Your work enables:
- **Agent 2**: Will attach QWebChannel bridge to your PDFViewer
- **Agent 3**: Will optimize performance of your implementation
- **Agent 4**: Will add advanced features to your viewer

## ✅ Definition of Done
- [ ] PDFViewer class functional and tested
- [ ] PDF rendering working in QWebEngineView
- [ ] Basic controls operational (zoom, pan, navigate)
- [ ] Memory management implemented
- [ ] Unit tests >95% coverage
- [ ] Documentation written
- [ ] Ready for Agent 2 bridge integration

## 🚀 Getting Started
1. Read all the files listed above
2. Create your branch: `git checkout -b feature/pdfjs-core-viewer`
3. Start with the directory structure and PDF.js bundle
4. Implement PDFViewer class step by step
5. Test each component as you build it

## 📞 Communication
- Update your GitHub issue #124 with daily progress
- Coordinate with other agents via the PDFJS_COORDINATION.md schedule
- Mark tasks complete as you finish them

**Your success is critical - all other agents depend on your foundation!**