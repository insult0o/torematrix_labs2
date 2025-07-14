# ISSUE #17 AGENT DEPLOYMENT PROMPTS
## Document Viewer Element Overlay System - Ready for Multi-Agent Implementation

## 🚀 Agent Deployment Commands
Use these exact prompts to deploy each agent for Issue #17 implementation:

### AGENT 1: Overlay Rendering Engine & Canvas Management
```
AGENT 1: Overlay Rendering Engine & Canvas Management

Your Mission

You are Agent 1 responsible for implementing the core overlay rendering engine with SVG/Canvas management, coordinate transformations, and base rendering infrastructure.

Required Reading (Read these files in order)

1. Parent Issue Context:
gh issue view 17
2. Your Specific Sub-Issue:
gh issue view 145
3. Your Detailed Instructions:
Read: /home/insulto/torematrix_labs2/AGENT_1_OVERLAY.md
4. Coordination Plan:
Read: /home/insulto/torematrix_labs2/OVERLAY_COORDINATION.md
5. Dependencies:
# PDF.js Integration (#16) for base viewer
# Coordinate Mapping Engine (#18) for positioning
# PyQt6 for graphics primitives

Your Deliverables

- Core overlay rendering engine in src/torematrix/ui/viewer/overlay.py
- Canvas/SVG renderer in src/torematrix/ui/viewer/renderer.py
- Coordinate transformation utilities in src/torematrix/ui/viewer/coordinates.py
- Layer management system in src/torematrix/ui/viewer/layers.py
- Rendering pipeline in src/torematrix/ui/viewer/pipeline.py

Start Command

git checkout -b feature/overlay-rendering-engine-agent1-issue145

# Begin development following your instruction file
```

### AGENT 2: Element Selection & State Management
```
AGENT 2: Element Selection & State Management

Your Mission

You are Agent 2 responsible for implementing element selection system, state management, and multi-element selection capabilities with persistent state.

Required Reading (Read these files in order)

1. Parent Issue Context:
gh issue view 17
2. Your Specific Sub-Issue:
gh issue view 146
3. Your Detailed Instructions:
Read: /home/insulto/torematrix_labs2/AGENT_2_OVERLAY.md
4. Coordination Plan:
Read: /home/insulto/torematrix_labs2/OVERLAY_COORDINATION.md
5. Dependencies (Wait for Agent 1's Day 3 completion):
# Agent 1: Overlay rendering APIs needed
# Element Management (#19-23) for data
# State Management (#3) for global state

Your Deliverables

- Element selection manager in src/torematrix/ui/viewer/selection.py
- State management system in src/torematrix/ui/viewer/state.py
- Multi-element selection algorithms in src/torematrix/ui/viewer/multi_select.py
- Selection event system in src/torematrix/ui/viewer/events.py
- Selection history in src/torematrix/ui/viewer/history.py

Start Command

git checkout -b feature/overlay-selection-state-agent2-issue146

# Begin development following your instruction file
```

### AGENT 3: Spatial Indexing & Performance Optimization
```
AGENT 3: Spatial Indexing & Performance Optimization

Your Mission

You are Agent 3 responsible for implementing spatial indexing with quadtree, viewport culling, and performance optimization for handling hundreds of elements efficiently.

Required Reading (Read these files in order)

1. Parent Issue Context:
gh issue view 17
2. Your Specific Sub-Issue:
gh issue view 147
3. Your Detailed Instructions:
Read: /home/insulto/torematrix_labs2/AGENT_3_OVERLAY.md
4. Coordination Plan:
Read: /home/insulto/torematrix_labs2/OVERLAY_COORDINATION.md
5. Dependencies (Wait for Agent 1 & 2's Day 3 completion):
# Agent 1: Rendering pipeline needed
# Agent 2: Selection system needed
# NumPy for spatial calculations

Your Deliverables

- Quadtree spatial indexing in src/torematrix/ui/viewer/spatial.py
- Viewport culling system in src/torematrix/ui/viewer/culling.py
- Element clustering in src/torematrix/ui/viewer/clustering.py
- Performance optimization in src/torematrix/ui/viewer/optimization.py
- Profiling system in src/torematrix/ui/viewer/profiling.py

Start Command

git checkout -b feature/overlay-performance-agent3-issue147

# Begin development following your instruction file
```

### AGENT 4: Interactive Features & Touch Support
```
AGENT 4: Interactive Features & Touch Support

Your Mission

You are Agent 4 responsible for implementing interactive features including hover effects, tooltips, touch support, and accessibility features.

Required Reading (Read these files in order)

1. Parent Issue Context:
gh issue view 17
2. Your Specific Sub-Issue:
gh issue view 148
3. Your Detailed Instructions:
Read: /home/insulto/torematrix_labs2/AGENT_4_OVERLAY.md
4. Coordination Plan:
Read: /home/insulto/torematrix_labs2/OVERLAY_COORDINATION.md
5. Dependencies (Wait for Agents 1, 2, 3's Day 3 completion):
# Agent 1: Rendering engine needed
# Agent 2: Selection system needed
# Agent 3: Spatial indexing needed
# Qt Touch Framework for gestures

Your Deliverables

- Interactive features in src/torematrix/ui/viewer/interactions.py
- Tooltip system in src/torematrix/ui/viewer/tooltips.py
- Touch support in src/torematrix/ui/viewer/touch.py
- Accessibility features in src/torematrix/ui/viewer/accessibility.py
- Animation system in src/torematrix/ui/viewer/animations.py
- Custom shapes in src/torematrix/ui/viewer/shapes.py

Start Command

git checkout -b feature/overlay-interactions-agent4-issue148

# Begin development following your instruction file
```

## 📋 Deployment Checklist

### Pre-Deployment Verification
- [ ] All agent instruction files created and accessible
- [ ] Coordination guide complete with timeline
- [ ] GitHub sub-issues created with detailed requirements
- [ ] Dependencies clearly documented
- [ ] Success metrics defined

### Agent Dependencies
- **Agent 1**: No dependencies - can start immediately
- **Agent 2**: Wait for Agent 1's Day 3 completion
- **Agent 3**: Wait for Agent 1 & 2's Day 3 completion
- **Agent 4**: Wait for Agents 1, 2, 3's Day 3 completion

### Success Criteria
- [ ] All agents complete their deliverables within timeline
- [ ] Integration points work seamlessly
- [ ] Performance targets met (60fps with 500+ elements)
- [ ] Accessibility compliance achieved
- [ ] Test coverage >95% across all components

## 🎯 Integration Timeline

### Day 1-3: Foundation Development
- **Agent 1**: Core rendering engine and coordinate system
- **Agent 2**: Selection management and state persistence
- **Agent 3**: Spatial indexing and performance optimization
- **Agent 4**: Preparation and design

### Day 4: System Integration
- **Agent 4**: Interactive features and final integration
- **All Agents**: Integration support and testing

### Day 5-6: Validation & Deployment
- **All Agents**: Performance validation and production readiness

## 🚀 Deployment Instructions

1. **Start with Agent 1** - Core rendering foundation
2. **Deploy Agent 2** when Agent 1 reaches Day 3
3. **Deploy Agent 3** when Agent 1 & 2 reach Day 3
4. **Deploy Agent 4** when Agents 1, 2, 3 reach Day 3
5. **Coordinate integration** during Day 4
6. **Final validation** during Day 5-6

Each agent should follow their specific instruction file and coordinate through the shared timeline in `OVERLAY_COORDINATION.md`.

---
**Ready for multi-agent deployment!** All preparation complete for parallel development of the document viewer overlay system.