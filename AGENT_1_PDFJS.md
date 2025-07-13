# AGENT 1: PDF.js Core Viewer Foundation

## 🎯 Mission
Implement the foundational PDF.js viewer integration with PyQt6, establishing the core rendering system and basic controls for Issue #124.

## 📋 Detailed Tasks

### Phase 1: PDF.js Bundle Setup (Day 1)
- [ ] Download and bundle PDF.js latest stable version
- [ ] Create offline-capable PDF.js distribution
- [ ] Set up resource directory structure
- [ ] Verify PDF.js integrity and functionality

### Phase 2: Core Viewer Implementation (Day 1-2)
- [ ] Implement `PDFViewer` class with QWebEngineView
- [ ] Create custom `viewer.html` template
- [ ] Set up basic PDF loading and rendering
- [ ] Implement error handling for invalid PDFs
- [ ] Add basic zoom controls (fit-to-width, fit-to-page, custom)
- [ ] Implement pan functionality with mouse/touch

### Phase 3: Navigation System (Day 2)
- [ ] Page navigation (next/previous/goto)
- [ ] Page counter and total pages display
- [ ] Keyboard shortcuts for navigation
- [ ] Mouse wheel navigation support

### Phase 4: Memory Management (Day 2)
- [ ] Implement PDF loading/unloading lifecycle
- [ ] Memory cleanup on document switch
- [ ] Resource monitoring and limits
- [ ] Garbage collection optimization

## 🏗️ Architecture Requirements

### Core Classes
```python
# src/torematrix/integrations/pdf/viewer.py
class PDFViewer(QWebEngineView):
    """Core PDF.js viewer widget"""
    
class PDFDocument:
    """PDF document model and lifecycle management"""
    
class ViewerConfig:
    """Viewer configuration and settings"""
```

### Resource Structure
```
resources/pdfjs/
├── pdf.min.js
├── pdf.worker.min.js
├── viewer.html
├── viewer.css
└── viewer.js
```

## 🔗 Integration Points

### Dependencies
- **PDF.js Library**: Latest stable version (3.11.x)
- **PyQt6**: QWebEngineView, QWebChannel
- **Event System**: Will integrate with Agent 2's bridge

### Output for Other Agents
- **Agent 2**: Viewer instance for bridge attachment
- **Agent 3**: Performance monitoring hooks
- **Agent 4**: Feature integration interfaces

## 📊 Success Metrics
- [ ] PDF rendering functional in QWebEngineView
- [ ] Basic navigation working (10+ page PDFs)
- [ ] Zoom functionality operational (25%-500%)
- [ ] Memory usage stable (<100MB for typical PDFs)
- [ ] Unit test coverage >95%
- [ ] Load time <2 seconds for average PDFs

## 🧪 Testing Requirements

### Unit Tests
- PDF loading/unloading
- Zoom level calculations
- Page navigation logic
- Memory management

### Integration Tests
- QWebEngineView integration
- Resource loading verification
- Error handling scenarios

## 📝 Documentation Deliverables
- API documentation for PDFViewer class
- Configuration options guide
- Troubleshooting common issues
- Performance characteristics

## ⚡ Performance Targets
- **Load Time**: <2s for 10MB PDFs
- **Memory Usage**: <50MB baseline + 5MB per 10 pages
- **Zoom Response**: <100ms for zoom operations
- **Navigation**: <50ms page transitions

## 🎯 Definition of Done
- [ ] PDFViewer class fully implemented and tested
- [ ] Custom viewer.html functional
- [ ] Basic controls working (zoom, pan, navigate)
- [ ] Memory management implemented
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Ready for Agent 2 bridge integration

**Timeline**: Day 1-2 (Critical Path - Blocks other agents)
**GitHub Issue**: #124
**Branch**: `feature/pdfjs-core-viewer`