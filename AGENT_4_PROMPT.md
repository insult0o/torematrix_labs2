# AGENT 4 PROMPT - PDF.js Advanced Features & UI Integration

## 📋 Your Mission
You are Agent 4, responsible for implementing advanced PDF.js features (search, annotations, print) and integrating with the main UI framework for seamless user experience. You deliver the final user-facing product.

## 📖 Required Reading (READ THESE FILES FIRST)
Before starting any work, you MUST read these files in order:

1. **Project Context**: `/home/insulto/torematrix_labs2/CLAUDE.md`
2. **Your Detailed Instructions**: `/home/insulto/torematrix_labs2/AGENT_4_PDFJS.md`
3. **Coordination Guide**: `/home/insulto/torematrix_labs2/PDFJS_COORDINATION.md`
4. **Agent 1's Work**: `/home/insulto/torematrix_labs2/AGENT_1_PDFJS.md` (the viewer foundation)
5. **Agent 2's Work**: `/home/insulto/torematrix_labs2/AGENT_2_PDFJS.md` (the communication bridge)
6. **Agent 3's Work**: `/home/insulto/torematrix_labs2/AGENT_3_PDFJS.md` (performance optimization)
7. **Your GitHub Issue**: Run `gh issue view 127` to see full requirements
8. **UI Framework Issues**: Run `gh issue view 11`, `gh issue view 12`, `gh issue view 13`, `gh issue view 14`, `gh issue view 15` to understand UI integration points

## 🕐 When You Start
**Timeline**: Day 4-6 (you start in parallel with Agent 3, complete last)

**Prerequisites**: 
- Agent 1's PDFViewer must be functional
- Agent 2's QWebChannel bridge must be operational
- Agent 3's optimization should be in progress (work in parallel)
- UI Framework (#11-15) integration points must be identified

## 🎯 Your Specific Tasks Summary
After reading the files above, you will implement:

### Day 4: Search & Text Selection
- Implement full-text search in PDF documents
- Create search UI with result highlighting
- Add search navigation (next/previous results)
- Implement text selection and copy-to-clipboard functionality
- Add context menus for selections

### Day 5: Annotations & Print System
- Implement annotation rendering (text, image, shapes)
- Add annotation interaction (click, hover)
- Create annotation overlay system
- Implement print functionality with options
- Add page range selection and print preview

### Day 6: UI Integration & Polish
- Integrate with main UI framework (#11-15)
- Create toolbar and controls
- Implement thumbnail navigation panel
- Add accessibility features (keyboard navigation, screen reader)
- Implement responsive design and final polish

## 📁 Files You Will Create
```
src/torematrix/integrations/pdf/features.py
src/torematrix/integrations/pdf/search.py
src/torematrix/integrations/pdf/annotations.py
src/torematrix/integrations/pdf/ui.py
resources/pdfjs/features.js
resources/pdfjs/search.js
resources/pdfjs/annotations.js
tests/integration/pdf/test_features.py
tests/accessibility/pdf/test_accessibility.py
```

## 🎨 UI Components You Must Implement

### Toolbar Features
- Zoom controls (fit-width, fit-page, custom %)
- Page navigation (first, previous, next, last)
- Search bar with options (case-sensitive, whole words, regex)
- Print and export buttons
- Fullscreen toggle
- Annotation controls (show/hide)

### Thumbnail Panel
- Page thumbnail grid with click-to-navigate
- Current page highlighting
- Thumbnail loading optimization
- Responsive grid layout

### Accessibility Features (MUST IMPLEMENT)
- [ ] Keyboard navigation support (Tab, Arrow keys, Enter, Esc)
- [ ] Screen reader compatibility (ARIA labels)
- [ ] High contrast mode support
- [ ] Focus management and visual indicators
- [ ] Alternative text for images and annotations

## ⚡ Performance Targets You Must Meet
- Search speed: <2s for full document search
- UI responsiveness: <100ms for user interactions
- Thumbnail loading: <500ms for panel population
- Print preparation: <5s for large documents
- Memory efficiency: <20MB overhead for features

## 🔗 Integration Requirements
Your work depends on:
- **Agent 1**: Core viewer for feature integration
- **Agent 2**: Bridge for feature communication with PDF.js
- **Agent 3**: Performance optimization integration
- **UI Framework (#11-15)**: For seamless UI integration

Your work delivers:
- **Complete PDF Viewer**: Production-ready user interface
- **Feature-Rich Experience**: Search, annotations, print, accessibility
- **UI Framework Integration**: Seamless integration with main application

## 🧪 Testing Requirements You Must Meet

### Feature Tests
- Search accuracy across different PDF formats
- Text selection precision and clipboard functionality
- Annotation rendering correctness
- Print output quality verification
- UI responsiveness across different screen sizes

### User Experience Tests
- Keyboard navigation completeness
- Accessibility compliance (WCAG 2.1)
- Cross-platform compatibility (Windows, macOS, Linux)
- Performance under different system loads

## ✅ Definition of Done
- [ ] All advanced features implemented and tested
- [ ] UI framework integration seamless
- [ ] Search functionality operational across PDF formats
- [ ] Text selection and copy working accurately
- [ ] Annotation rendering functional
- [ ] Print system operational with options
- [ ] Accessibility compliance achieved (WCAG 2.1)
- [ ] User experience polished and responsive
- [ ] Cross-platform compatibility verified
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Production ready for deployment

## 🚀 Getting Started
1. Read all the files listed above
2. Wait for Agent 2 to complete bridge (coordinate with Agent 3)
3. Create your branch: `git checkout -b feature/pdfjs-features`
4. Study all previous agents' implementations
5. Identify UI Framework integration points
6. Start with search functionality (foundational for other features)
7. Build features incrementally and test thoroughly
8. Integrate with UI framework progressively
9. Polish user experience and accessibility last

## 📞 Communication
- Coordinate with Agent 3 for shared resource usage
- Work closely with UI Framework team for integration
- Update your GitHub issue #127 with daily progress
- Conduct user testing sessions for feedback
- Coordinate final integration testing with all agents

**You deliver the final user experience - make it exceptional!**