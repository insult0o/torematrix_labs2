# AGENT PROMPTS - ISSUE #13: LAYOUT MANAGEMENT

## 🤖 AGENT 1: Core Layout Manager & Templates

### Your Mission
You are Agent 1 responsible for implementing the core layout management system with predefined templates and fundamental layout operations.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 13
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 116
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_1_LAYOUT_MANAGEMENT.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/LAYOUT_MANAGEMENT_COORDINATION.md
   ```

5. **Project Context**:
   ```
   Read: /home/insulto/torematrix_labs2/CLAUDE.md
   Read: /home/insulto/.claude/CLAUDE.md
   ```

### Your Deliverables
- LayoutManager core class in `src/torematrix/ui/layouts/manager.py`
- Layout templates in `src/torematrix/ui/layouts/templates.py`
- Base layout classes in `src/torematrix/ui/layouts/base.py`
- Validation rules in `src/torematrix/ui/layouts/validation.py`
- Comprehensive unit tests

### Start Command
```bash
# Create your feature branch
git checkout -b feature/ui-layout-management-core

# Begin development following your instruction file
```

---

## 🤖 AGENT 2: Layout Persistence & Configuration

### Your Mission
You are Agent 2 responsible for implementing layout persistence, serialization, and configuration management for the layout system.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 13
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 117
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_2_LAYOUT_MANAGEMENT.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/LAYOUT_MANAGEMENT_COORDINATION.md
   ```

5. **Dependencies** (Wait for Agent 1's Day 3 completion):
   ```
   # Agent 1 must complete LayoutManager class first
   # Check: src/torematrix/ui/layouts/manager.py exists
   ```

### Your Deliverables
- Layout serialization in `src/torematrix/ui/layouts/serialization.py`
- Configuration integration in `src/torematrix/ui/layouts/persistence.py`
- Custom layout management in `src/torematrix/ui/layouts/custom.py`
- Multi-monitor support in `src/torematrix/ui/layouts/multimonitor.py`
- Migration system in `src/torematrix/ui/layouts/migration.py`

### Start Command
```bash
# Wait for Agent 1's base classes, then:
git checkout -b feature/ui-layout-management-persistence

# Begin development following your instruction file
```

---

## 🤖 AGENT 3: Responsive Design & Performance

### Your Mission
You are Agent 3 responsible for implementing responsive design system with breakpoints and performance optimization for layout operations.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 13
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 118
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_3_LAYOUT_MANAGEMENT.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/LAYOUT_MANAGEMENT_COORDINATION.md
   ```

5. **Dependencies** (Wait for Agent 1 & 2's Day 3 completion):
   ```
   # Agent 1: Layout templates for responsive variants needed
   # Agent 2: Configuration integration for responsive settings needed
   ```

### Your Deliverables
- Responsive design system in `src/torematrix/ui/layouts/responsive.py`
- Breakpoint management in `src/torematrix/ui/layouts/breakpoints.py`
- Adaptive algorithms in `src/torematrix/ui/layouts/adaptive.py`
- Performance optimization in `src/torematrix/ui/layouts/performance.py`
- Monitoring tools in `src/torematrix/ui/layouts/monitoring.py`

### Start Command
```bash
# Wait for Agent 1 & 2's foundations, then:
git checkout -b feature/ui-layout-management-responsive

# Begin development following your instruction file
```

---

## 🤖 AGENT 4: Layout Transitions & Integration

### Your Mission
You are Agent 4 responsible for implementing smooth layout transitions, drag-and-drop editing, and complete integration with the UI framework.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 13
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 119
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_4_LAYOUT_MANAGEMENT.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/LAYOUT_MANAGEMENT_COORDINATION.md
   ```

5. **Dependencies** (Wait for Agents 1, 2, 3's Day 3 completion):
   ```
   # Agent 1: Complete layout system needed
   # Agent 2: Layout persistence for floating panels needed
   # Agent 3: Responsive coordination for transitions needed
   ```

### Your Deliverables
- Transition system in `src/torematrix/ui/layouts/transitions.py`
- Animation framework in `src/torematrix/ui/layouts/animations.py`
- Layout editor in `src/torematrix/ui/layouts/editor.py`
- Preview tools in `src/torematrix/ui/layouts/preview.py`
- Floating panels in `src/torematrix/ui/layouts/floating.py`

### Start Command
```bash
# Wait for Agents 1, 2, 3's completion, then:
git checkout -b feature/ui-layout-management-transitions

# Begin development following your instruction file
```

---

## 📋 Coordination Notes for All Agents

### Shared Resources
- **Main Window**: Dependency for layout container integration (Issue #11)
- **Reactive Components**: Dependency for layout items (Issue #12)
- **Configuration Management**: Already complete (Issue #5)

### Communication Protocol
- Daily sync at coordination checkpoints
- Clear handoff documentation on Day 3
- Agent 4 coordinates final integration on Day 4

### Layout Templates to Implement
```
Document Layout: Main viewer + properties + corrections panels
Split Layout: Primary and secondary content areas  
Tabbed Layout: Tab-based content organization
Multi-Panel: Complex workflow with multiple panels
```

### Responsive Breakpoints
```
XS (≤576px): Mobile portrait - stacked layout
SM (≤768px): Mobile landscape - tabbed layout
MD (≤992px): Tablet - simplified split layout  
LG (≤1200px): Desktop - full split layout
XL (≥1201px): Large desktop - extended layout
```

### Success Criteria
- >95% test coverage for each agent's components
- All agents ready for integration by Day 3
- Complete system integration by Day 4
- Responsive design working across all screen sizes
- 60fps smooth transition animations
- Production readiness by Day 6