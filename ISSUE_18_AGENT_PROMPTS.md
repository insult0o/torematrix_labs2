# ISSUE #18 AGENT DEPLOYMENT PROMPTS

## 🚀 Quick Deploy Commands

Copy and paste these prompts to deploy each agent for Issue #18 - Document Viewer Coordinate Mapping Engine.

---

## 🤖 Agent 1 - Core Transformation Engine

### Deploy Agent 1
```
I am Agent 1 working on the Document Viewer Coordinate Mapping Engine. I need to implement the Core Transformation Engine as described in AGENT_1_COORDINATES.md.

My specific assignment is Sub-Issue #149: Core Transformation Engine.

Key tasks:
1. Create CoordinateMapper class with document-to-viewer conversion
2. Implement AffineTransformation with matrix operations  
3. Add geometric utilities (Point, Rect, Size classes)
4. Build coordinate validation and caching framework
5. Achieve >95% test coverage with performance <1ms per transformation

I'll start by creating my feature branch and implementing the core coordinate mapping system.
```

### Agent 1 Branch Command
```bash
git checkout -b feature/coordinates-core-agent1-issue149
```

---

## 🤖 Agent 2 - Viewport & Screen Mapping

### Deploy Agent 2
```
I am Agent 2 working on the Document Viewer Coordinate Mapping Engine. I need to implement the Viewport & Screen Mapping system as described in AGENT_2_COORDINATES.md.

My specific assignment is Sub-Issue #150: Viewport & Screen Mapping.

Key tasks:
1. Create ViewportManager with viewer-to-screen conversion
2. Implement ScreenCoordinateSystem with DPI awareness
3. Add viewport clipping and bounds management
4. Build multi-monitor coordinate support
5. Achieve >95% test coverage with performance <0.5ms per conversion

I depend on Agent 1's CoordinateMapper and AffineTransformation classes.

I'll start by creating my feature branch and implementing the viewport management system.
```

### Agent 2 Branch Command
```bash
git checkout -b feature/coordinates-viewport-agent2-issue150
```

---

## 🤖 Agent 3 - Zoom, Pan & Rotation Optimization

### Deploy Agent 3
```
I am Agent 3 working on the Document Viewer Coordinate Mapping Engine. I need to implement the Zoom, Pan & Rotation Optimization system as described in AGENT_3_COORDINATES.md.

My specific assignment is Sub-Issue #151: Zoom, Pan & Rotation Optimization.

Key tasks:
1. Create ZoomManager with smooth zoom operations
2. Implement PanManager with momentum support
3. Add RotationManager with angle snapping
4. Build advanced caching system with LRU eviction
5. Achieve >95% test coverage with performance <5ms per operation

I depend on Agent 1's CoordinateMapper and AffineTransformation classes.

I'll start by creating my feature branch and implementing the high-performance transformation system.
```

### Agent 3 Branch Command
```bash
git checkout -b feature/coordinates-optimization-agent3-issue151
```

---

## 🤖 Agent 4 - Multi-Page Integration & Production

### Deploy Agent 4
```
I am Agent 4 working on the Document Viewer Coordinate Mapping Engine. I need to implement the Multi-Page Integration & Production system as described in AGENT_4_COORDINATES.md.

My specific assignment is Sub-Issue #153: Multi-Page Integration & Production.

Key tasks:
1. Create MultiPageCoordinateSystem with page management
2. Implement PDF.js integration for PDF coordinates
3. Add debug visualization and validation tools
4. Build production monitoring and performance profiling
5. Achieve >95% test coverage with performance <2ms per multi-page transformation

I depend on all previous agents: Agent 1 (core engine), Agent 2 (viewport), Agent 3 (optimization).

I'll start by creating my feature branch and implementing the complete integrated system.
```

### Agent 4 Branch Command
```bash
git checkout -b feature/coordinates-integration-agent4-issue153
```

---

## 📋 Pre-Deployment Checklist

### Before Starting Any Agent
- [ ] Read the main issue #18 for context
- [ ] Review your specific agent instruction file
- [ ] Check the COORDINATES_COORDINATION.md for dependencies
- [ ] Verify you're on the correct feature branch
- [ ] Confirm your agent number matches the branch name

### Agent-Specific Prerequisites

#### Agent 1 (Core Engine)
- [ ] No dependencies - you can start immediately
- [ ] Focus on mathematical accuracy and performance
- [ ] Your work enables all other agents

#### Agent 2 (Viewport/Screen)
- [ ] Wait for Agent 1 to complete CoordinateMapper
- [ ] Review Agent 1's coordinate transformation APIs
- [ ] Focus on Qt widget integration and DPI handling

#### Agent 3 (Optimization)
- [ ] Wait for Agent 1 to complete AffineTransformation
- [ ] Review Agent 1's transformation caching framework
- [ ] Focus on interactive performance and smooth animations

#### Agent 4 (Integration)
- [ ] Wait for Agents 1, 2, 3 to complete their components
- [ ] Review all previous agent APIs and interfaces
- [ ] Focus on system integration and production readiness

---

## 🎯 Success Criteria Reminder

### Each Agent Must Achieve
- [ ] >95% test coverage across all implemented files
- [ ] All performance targets met or exceeded
- [ ] Complete API documentation
- [ ] Integration tests passing
- [ ] Proper error handling and validation

### Agent-Specific Targets
- **Agent 1**: <1ms per coordinate transformation
- **Agent 2**: <0.5ms per screen coordinate conversion
- **Agent 3**: <5ms per zoom/pan/rotation operation
- **Agent 4**: <2ms per multi-page transformation

---

## 📞 Communication Protocol

### Daily Updates
```
Progress update for Issue #18 Agent [X]:

Completed today:
- [Task 1 completed]
- [Task 2 completed]

In progress:
- [Task currently working on]

Blockers:
- [Any blockers or dependencies]

Next steps:
- [What you'll work on next]

Performance metrics:
- [Any relevant performance measurements]
```

### Integration Points
- **Agent 1**: Notify when core APIs are ready
- **Agent 2**: Confirm Agent 1 integration working
- **Agent 3**: Confirm Agent 1 integration working
- **Agent 4**: Confirm all agent integrations working

---

## 🚀 Quick Start Summary

### Agent 1 (Days 1-2)
1. `git checkout -b feature/coordinates-core-agent1-issue149`
2. Create `src/torematrix/ui/viewer/coordinates.py`
3. Implement core coordinate mapping engine
4. Build geometric utilities and validation
5. Achieve >95% test coverage

### Agent 2 (Days 3-4)
1. `git checkout -b feature/coordinates-viewport-agent2-issue150`
2. Create `src/torematrix/ui/viewer/viewport.py`
3. Implement viewport and screen coordinate system
4. Add DPI awareness and multi-monitor support
5. Achieve >95% test coverage

### Agent 3 (Days 3-4)
1. `git checkout -b feature/coordinates-optimization-agent3-issue151`
2. Create `src/torematrix/ui/viewer/zoom.py`
3. Implement high-performance transformations
4. Build advanced caching and optimization
5. Achieve >95% test coverage

### Agent 4 (Days 5-6)
1. `git checkout -b feature/coordinates-integration-agent4-issue153`
2. Create `src/torematrix/ui/viewer/multipage.py`
3. Implement multi-page coordinate system
4. Add PDF.js integration and debug tools
5. Complete system integration and testing

---

## 🎉 Ready to Deploy!

All agents are now ready for deployment. Use the appropriate prompt above to start your assigned agent work. Remember to:

1. **Create your feature branch** with the correct naming convention
2. **Follow your agent instruction file** for detailed implementation
3. **Coordinate with other agents** via the main issue #18
4. **Test thoroughly** and maintain >95% coverage
5. **Document your work** and report progress daily

**Good luck building the Document Viewer Coordinate Mapping Engine!**