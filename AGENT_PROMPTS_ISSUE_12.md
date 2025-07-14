# AGENT PROMPTS - ISSUE #12: REACTIVE COMPONENTS

## 🤖 AGENT 1: Core Reactive Base Classes

### Your Mission
You are Agent 1 responsible for implementing the core reactive base classes and fundamental mechanisms for reactive UI components.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 12
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 108
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_1_REACTIVE_COMPONENTS.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/REACTIVE_COMPONENTS_COORDINATION.md
   ```

5. **Project Context**:
   ```
   Read: /home/insulto/torematrix_labs2/CLAUDE.md
   Read: /home/insulto/.claude/CLAUDE.md
   ```

### Your Deliverables
- ReactiveWidget base class in `src/torematrix/ui/components/reactive.py`
- Reactive metaclass implementation
- Property binding decorators in `src/torematrix/ui/components/decorators.py`
- Lifecycle management in `src/torematrix/ui/components/lifecycle.py`
- Comprehensive unit tests

### Start Command
```bash
# Create your feature branch
git checkout -b feature/reactive-components-core

# Begin development following your instruction file
```

---

## 🤖 AGENT 2: State Subscription & Memory Management

### Your Mission
You are Agent 2 responsible for implementing robust state subscription mechanisms and comprehensive memory management for reactive components.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 12
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 111
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_2_REACTIVE_COMPONENTS.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/REACTIVE_COMPONENTS_COORDINATION.md
   ```

5. **Dependencies** (Wait for Agent 1's Day 3 completion):
   ```
   # Agent 1 must complete ReactiveWidget base class first
   # Check: src/torematrix/ui/components/reactive.py exists
   ```

### Your Deliverables
- State subscription manager in `src/torematrix/ui/components/subscriptions.py`
- Memory management utilities in `src/torematrix/ui/components/memory.py`
- Cleanup strategies in `src/torematrix/ui/components/cleanup.py`
- Comprehensive memory tests

### Start Command
```bash
# Wait for Agent 1's base classes, then:
git checkout -b feature/reactive-components-state

# Begin development following your instruction file
```

---

## 🤖 AGENT 3: Performance Optimization & Diffing

### Your Mission
You are Agent 3 responsible for implementing efficient re-rendering with virtual DOM-like diffing, render batching, and performance monitoring.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 12
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 112
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_3_REACTIVE_COMPONENTS.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/REACTIVE_COMPONENTS_COORDINATION.md
   ```

5. **Dependencies** (Wait for Agent 1 & 2's Day 3 completion):
   ```
   # Agent 1: ReactiveWidget render system needed
   # Agent 2: State change notifications needed
   ```

### Your Deliverables
- Widget diffing engine in `src/torematrix/ui/components/diffing.py`
- Render batching system in `src/torematrix/ui/components/batching.py`
- Performance monitoring in `src/torematrix/ui/components/monitoring.py`
- Debug utilities in `src/torematrix/ui/components/debug.py`

### Start Command
```bash
# Wait for Agent 1 & 2's foundations, then:
git checkout -b feature/reactive-components-performance

# Begin development following your instruction file
```

---

## 🤖 AGENT 4: Integration & Error Handling

### Your Mission
You are Agent 4 responsible for implementing error boundaries, async operation support, and seamless integration with existing UI framework components.

### Required Reading (Read these files in order)
1. **Parent Issue Context**: 
   ```
   gh issue view 12
   ```

2. **Your Specific Sub-Issue**:
   ```
   gh issue view 114
   ```

3. **Your Detailed Instructions**:
   ```
   Read: /home/insulto/torematrix_labs2/AGENT_4_REACTIVE_COMPONENTS.md
   ```

4. **Coordination Plan**:
   ```
   Read: /home/insulto/torematrix_labs2/REACTIVE_COMPONENTS_COORDINATION.md
   ```

5. **Dependencies** (Wait for Agents 1, 2, 3's Day 3 completion):
   ```
   # Agent 1: Component base classes needed
   # Agent 2: Memory management patterns needed  
   # Agent 3: Performance infrastructure needed
   ```

### Your Deliverables
- Error boundary components in `src/torematrix/ui/components/boundaries.py`
- Async operation mixins in `src/torematrix/ui/components/mixins.py`
- UI integration utilities in `src/torematrix/ui/components/integration.py`
- Testing framework in `src/torematrix/ui/components/testing.py`

### Start Command
```bash
# Wait for Agents 1, 2, 3's completion, then:
git checkout -b feature/reactive-components-integration

# Begin development following your instruction file
```

---

## 📋 Coordination Notes for All Agents

### Shared Resources
- **Event Bus**: Already complete (Issue #1)
- **State Management**: Already complete (Issue #3)
- **Main Window**: Dependency for final integration (Issue #11)

### Communication Protocol
- Daily sync at coordination checkpoints
- Clear handoff documentation on Day 3
- Agent 4 coordinates final integration on Day 4

### Success Criteria
- >95% test coverage for each agent's components
- All agents ready for integration by Day 3
- Complete system integration by Day 4
- Production readiness by Day 6