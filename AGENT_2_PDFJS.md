# AGENT 2: PDF.js Qt-JavaScript Communication Bridge

## 🎯 Mission
Implement bidirectional communication between Qt and PDF.js using QWebChannel for element highlighting, events, and data exchange for Issue #125.

## 📋 Detailed Tasks

### Phase 1: QWebChannel Setup (Day 2)
- [ ] Configure QWebChannel in PDFViewer
- [ ] Create JavaScript bridge object registration
- [ ] Set up communication protocols and message formats
- [ ] Implement connection verification and health checks

### Phase 2: Bridge Implementation (Day 2-3)
- [ ] Implement `PDFBridge` class for Qt-side communication
- [ ] Create `bridge.js` for PDF.js-side communication
- [ ] Set up event forwarding system
- [ ] Implement data serialization/deserialization
- [ ] Add error handling and retry mechanisms

### Phase 3: Element Highlighting System (Day 3)
- [ ] Coordinate mapping between PDF coordinates and elements
- [ ] Implement highlight overlay system
- [ ] Create selection event handling
- [ ] Add multi-element selection support
- [ ] Implement highlight persistence and retrieval

### Phase 4: Event Bus Integration (Day 3)
- [ ] Connect bridge events to main Event Bus (#1)
- [ ] Implement event filtering and routing
- [ ] Add event prioritization system
- [ ] Create event logging and debugging tools

## 🏗️ Architecture Requirements

### Core Classes
```python
# src/torematrix/integrations/pdf/bridge.py
class PDFBridge(QObject):
    """Qt-side communication bridge"""
    
class EventForwarder:
    """Event Bus integration and forwarding"""
    
class CoordinateMapper:
    """PDF coordinate to element mapping"""

# src/torematrix/integrations/pdf/communication.py
class MessageProtocol:
    """Communication protocol definitions"""
    
class EventSerializer:
    """Event serialization for Qt-JS communication"""
```

### JavaScript Bridge
```javascript
// resources/pdfjs/bridge.js
class PDFJSBridge {
    // PDF.js side communication
}

class HighlightManager {
    // Element highlighting in PDF.js
}
```

## 🔗 Integration Points

### Dependencies
- **Agent 1**: PDFViewer instance for bridge attachment
- **Event Bus (#1)**: For event forwarding and integration
- **Element Models**: For coordinate mapping

### Output for Other Agents
- **Agent 3**: Performance monitoring hooks
- **Agent 4**: Feature communication channels

## 📊 Success Metrics
- [ ] Bidirectional Qt-JS communication functional
- [ ] Element highlighting working accurately
- [ ] Event forwarding to Event Bus operational
- [ ] Message latency <10ms for typical operations
- [ ] Error recovery functional
- [ ] Integration test coverage >90%

## 🧪 Testing Requirements

### Unit Tests
- QWebChannel setup and configuration
- Message serialization/deserialization
- Event forwarding logic
- Error handling scenarios

### Integration Tests
- End-to-end communication testing
- Element highlighting accuracy
- Event Bus integration
- Performance under load

## 🔄 Communication Protocol

### Message Types
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

## 📝 Documentation Deliverables
- Communication protocol specification
- Bridge API documentation
- Event integration guide
- Debugging and troubleshooting guide

## ⚡ Performance Targets
- **Message Latency**: <10ms for standard operations
- **Highlight Response**: <50ms for element highlighting
- **Event Forwarding**: <5ms to Event Bus
- **Memory Overhead**: <10MB for bridge operations

## 🎯 Definition of Done
- [ ] PDFBridge class fully implemented
- [ ] JavaScript bridge operational
- [ ] Element highlighting functional
- [ ] Event Bus integration complete
- [ ] Error handling robust
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Ready for Agent 3-4 integration

**Timeline**: Day 2-3 (Dependent on Agent 1, Enables Agent 3-4)
**GitHub Issue**: #125
**Branch**: `feature/pdfjs-bridge`