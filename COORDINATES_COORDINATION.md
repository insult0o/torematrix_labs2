# COORDINATES COORDINATION GUIDE

## 🎯 Project Overview
**Document Viewer Coordinate Mapping Engine** - A high-performance coordinate transformation system for precise document element positioning, viewport management, and multi-page document support.

## 📋 Agent Assignments & Timeline

### Agent 1: Core Transformation Engine
- **Sub-Issue**: #149 - Core Transformation Engine
- **Timeline**: Days 1-2 (Foundation Phase)
- **Dependencies**: None (Starting point)
- **Key Deliverables**:
  - `CoordinateMapper` class with document-to-viewer conversion
  - `AffineTransformation` with matrix operations
  - `Point`, `Rect`, `Size` geometric utilities
  - Coordinate validation and caching framework

### Agent 2: Viewport & Screen Mapping
- **Sub-Issue**: #150 - Viewport & Screen Mapping
- **Timeline**: Days 3-4 (Integration Phase)
- **Dependencies**: Agent 1 (Core transformation engine)
- **Key Deliverables**:
  - `ViewportManager` with viewer-to-screen conversion
  - `ScreenCoordinateSystem` with DPI awareness
  - Viewport clipping and bounds management
  - Multi-monitor coordinate support

### Agent 3: Zoom, Pan & Rotation Optimization
- **Sub-Issue**: #151 - Zoom, Pan & Rotation Optimization
- **Timeline**: Days 3-4 (Integration Phase)
- **Dependencies**: Agent 1 (Core transformation engine)
- **Key Deliverables**:
  - `ZoomManager` with smooth zoom operations
  - `PanManager` with momentum support
  - `RotationManager` with angle snapping
  - Advanced caching system with LRU eviction

### Agent 4: Multi-Page Integration & Production
- **Sub-Issue**: #153 - Multi-Page Integration & Production
- **Timeline**: Days 5-6 (Production Phase)
- **Dependencies**: Agents 1, 2, 3 (Complete integration)
- **Key Deliverables**:
  - `MultiPageCoordinateSystem` with page management
  - PDF.js integration for PDF coordinates
  - Debug visualization and validation tools
  - Production monitoring and performance profiling

## 🔗 Integration Points & Dependencies

### Phase 1: Foundation (Days 1-2)
```
Agent 1 (Core Engine)
├── CoordinateMapper
├── AffineTransformation
├── Geometric Utilities
└── Validation Framework
```

**Agent 1 Exports for Others:**
- `CoordinateMapper` class
- `AffineTransformation` class
- `Point`, `Rect`, `Size` utilities
- Coordinate validation methods
- Transformation caching framework

### Phase 2: Integration (Days 3-4)
```
Agent 2 (Viewport/Screen) ← Agent 1
├── ViewportManager
├── ScreenCoordinateSystem
├── DPI Awareness
└── Multi-Monitor Support

Agent 3 (Optimization) ← Agent 1
├── ZoomManager
├── PanManager
├── RotationManager
└── Advanced Caching
```

**Agent 2 Exports for Agent 4:**
- `ViewportManager` with screen coordinate conversion
- `ScreenCoordinateSystem` with DPI handling
- Viewport clipping algorithms
- Multi-monitor coordinate utilities

**Agent 3 Exports for Agent 4:**
- `ZoomManager` with performance optimization
- `PanManager` with momentum animation
- `RotationManager` with angle snapping
- Advanced caching framework

### Phase 3: Production (Days 5-6)
```
Agent 4 (Production) ← Agents 1, 2, 3
├── MultiPageCoordinateSystem
├── PDF.js Integration
├── Debug Visualization
├── System Integration
└── Performance Monitoring
```

## 📊 Key Integration Interfaces

### Agent 1 → Agent 2 Interface
```python
# Agent 1 provides:
from .coordinates import CoordinateMapper, CoordinateSpace
from .transformations import AffineTransformation
from ..utils.geometry import Point, Rect, Size

# Agent 2 uses:
class ViewportManager:
    def __init__(self, widget: QWidget):
        self._coordinate_mapper: Optional[CoordinateMapper] = None
        
    def set_coordinate_mapper(self, mapper: CoordinateMapper):
        self._coordinate_mapper = mapper
```

### Agent 1 → Agent 3 Interface
```python
# Agent 1 provides:
from .coordinates import CoordinateMapper
from .transformations import AffineTransformation
from .cache import TransformationCache

# Agent 3 uses:
class ZoomManager:
    def __init__(self, coordinate_mapper: CoordinateMapper):
        self.coordinate_mapper = coordinate_mapper
        self._transformation_cache = TransformationCache()
```

### Agents 1,2,3 → Agent 4 Interface
```python
# Agent 4 integrates all:
from .coordinates import CoordinateMapper
from .viewport import ViewportManager
from .zoom import ZoomManager
from .pan import PanManager
from .rotation import RotationManager

class CoordinateSystemIntegrator:
    def initialize(self, widget):
        self._viewport_manager = ViewportManager(widget)
        self._zoom_manager = ZoomManager(base_mapper)
        self._pan_manager = PanManager(base_mapper)
        self._rotation_manager = RotationManager(base_mapper)
```

## 🎯 Success Criteria & Milestones

### Agent 1 Success Criteria
- [ ] Core transformation engine implemented
- [ ] Sub-pixel accuracy in coordinate conversion
- [ ] Affine transformation matrices functional
- [ ] Geometric utilities complete
- [ ] >95% test coverage achieved
- [ ] Performance: <1ms per coordinate transformation

### Agent 2 Success Criteria
- [ ] Viewport management system operational
- [ ] DPI awareness fully functional
- [ ] Multi-monitor support working
- [ ] Screen coordinate conversion accurate
- [ ] >95% test coverage achieved
- [ ] Performance: <0.5ms per screen conversion

### Agent 3 Success Criteria
- [ ] Zoom, pan, rotation optimization complete
- [ ] Advanced caching system operational
- [ ] Smooth animations at 60fps
- [ ] Performance monitoring functional
- [ ] >95% test coverage achieved
- [ ] Performance: <5ms per zoom/pan/rotation

### Agent 4 Success Criteria
- [ ] Multi-page coordinate system complete
- [ ] PDF.js integration working
- [ ] Debug visualization operational
- [ ] System integration complete
- [ ] >95% test coverage achieved
- [ ] Performance: <2ms per multi-page transformation

## 📈 Performance Targets

### Overall System Performance
- **Single point transformation**: <1ms
- **Batch transformation (10k points)**: <100ms
- **Viewport updates**: <16ms (60fps)
- **Multi-page navigation**: <50ms
- **Memory usage**: <100MB for typical document
- **Cache hit rate**: >80%

### Agent-Specific Targets
- **Agent 1**: Coordinate accuracy to 0.01 pixel
- **Agent 2**: DPI scaling without precision loss
- **Agent 3**: Smooth zoom/pan at 60fps
- **Agent 4**: Multi-page switching in <50ms

## 🧪 Testing Strategy

### Unit Testing (Each Agent)
- **Agent 1**: Transformation accuracy tests
- **Agent 2**: Viewport and screen coordinate tests
- **Agent 3**: Performance and optimization tests
- **Agent 4**: Multi-page and integration tests

### Integration Testing (Agent 4)
- End-to-end coordinate mapping tests
- Multi-page document navigation tests
- PDF.js integration tests
- Performance regression tests

### Performance Testing (Agent 4)
- Load testing with large documents
- Memory usage monitoring
- Real-time performance profiling
- Stress testing with rapid transformations

## 🚀 Development Workflow

### Daily Coordination
1. **Morning Check-in**: Comment on main issue #18 with progress
2. **Dependency Updates**: Notify dependent agents of interface changes
3. **Integration Testing**: Run tests with latest dependencies
4. **Evening Report**: Update issue with completed tasks

### Weekly Milestones
- **Week 1**: Agents 1, 2, 3 complete core implementation
- **Week 2**: Agent 4 integrates all components
- **Week 3**: Performance optimization and testing
- **Week 4**: Production readiness and documentation

### Integration Events
- **Day 2**: Agent 1 completes core engine
- **Day 4**: Agents 2 & 3 integrate with Agent 1
- **Day 6**: Agent 4 begins full system integration
- **Day 8**: Complete system testing and validation

## 📝 Communication Protocol

### Standard Updates
- **Progress**: Comment on sub-issue with daily progress
- **Blockers**: Tag @insult0o for immediate assistance
- **Dependencies**: Notify dependent agents of interface changes
- **Integration**: Coordinate via main issue #18 comments

### Critical Communications
- **API Changes**: Immediate notification to dependent agents
- **Performance Issues**: Report to all agents for coordination
- **Integration Problems**: Escalate to main issue discussion
- **Production Readiness**: Final validation with all agents

## 🔧 Technical Standards

### Code Quality
- **Type Hints**: Full typing for all interfaces
- **Documentation**: Comprehensive API documentation
- **Testing**: >95% code coverage requirement
- **Performance**: Meet or exceed performance targets

### Integration Standards
- **Interface Contracts**: Clear API contracts between agents
- **Error Handling**: Comprehensive error handling and recovery
- **Thread Safety**: Thread-safe operations where required
- **Memory Management**: Efficient memory usage and cleanup

## 🎯 Risk Management

### High-Risk Dependencies
- **Agent 1 → All Others**: Core engine failure blocks all work
- **PDF.js Integration**: External dependency may have compatibility issues
- **Performance Targets**: Aggressive performance goals may require optimization

### Mitigation Strategies
- **Agent 1 Priority**: Ensure Agent 1 completes first
- **PDF.js Testing**: Early testing with PDF.js integration
- **Performance Monitoring**: Continuous performance tracking
- **Fallback Plans**: Graceful degradation for complex features

## 📚 Reference Documentation

### Technical References
- [Qt Coordinate System](https://doc.qt.io/qt-6/coordsys.html)
- [Affine Transformations](https://en.wikipedia.org/wiki/Affine_transformation)
- [PDF.js API](https://mozilla.github.io/pdf.js/api/)
- [Performance Optimization](https://docs.python.org/3/library/profile.html)

### Project Files
- `AGENT_1_COORDINATES.md` - Core transformation engine
- `AGENT_2_COORDINATES.md` - Viewport and screen mapping
- `AGENT_3_COORDINATES.md` - Zoom, pan, rotation optimization
- `AGENT_4_COORDINATES.md` - Multi-page integration and production

## 🎉 Success Metrics

### Feature Completion
- ✅ **Core Transformation Engine** - Sub-pixel accurate coordinate mapping
- ✅ **Viewport Management** - DPI-aware screen coordinate conversion
- ✅ **Interactive Transformations** - Smooth zoom, pan, rotation at 60fps
- ✅ **Multi-Page Support** - Complete document navigation system
- ✅ **PDF.js Integration** - Native PDF coordinate extraction
- ✅ **Debug Tools** - Comprehensive visualization and validation
- ✅ **Production Ready** - Performance monitoring and deployment

### Quality Metrics
- **Test Coverage**: >95% across all components
- **Performance**: All targets met or exceeded
- **Documentation**: Complete API and usage documentation
- **Integration**: Seamless component integration
- **Production**: Deployment-ready with monitoring

---

**This coordination guide ensures all agents work together efficiently to deliver a world-class coordinate mapping system for the document viewer. Follow the timeline, respect dependencies, and communicate regularly for success!**