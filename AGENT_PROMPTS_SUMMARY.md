# PDF.js Integration - Agent Prompts Summary

## 🎯 Quick Reference for All Agents

Each agent has a dedicated prompt file that contains:
- Their specific mission and timeline
- Required reading files (in order)
- Detailed task breakdown
- Files they need to create
- Performance targets
- Integration requirements
- Definition of done

## 📝 Agent Prompt Files

### Agent 1: Core Viewer Foundation
**File**: `AGENT_1_PROMPT.md`
**Timeline**: Day 1-2 (Critical Path)
**Mission**: Implement foundational PDF.js viewer with PyQt6

### Agent 2: Qt-JavaScript Bridge  
**File**: `AGENT_2_PROMPT.md`
**Timeline**: Day 2-3 (Dependent on Agent 1)
**Mission**: Implement QWebChannel communication bridge

### Agent 3: Performance Optimization
**File**: `AGENT_3_PROMPT.md`  
**Timeline**: Day 3-4 (Parallel with Agent 4)
**Mission**: Optimize performance and memory management

### Agent 4: Advanced Features & UI
**File**: `AGENT_4_PROMPT.md`
**Timeline**: Day 4-6 (Final integration)
**Mission**: Implement features and UI framework integration

## 🚀 How to Use These Prompts

### For Each Agent:
1. **Read your prompt file first** - it has everything you need
2. **Follow the required reading list** - critical context files
3. **Check your GitHub issue** - run the `gh issue view` command
4. **Create your branch** - use the suggested branch name
5. **Start development** - follow the day-by-day task breakdown

### For Coordination:
- **All agents should read**: `PDFJS_COORDINATION.md`
- **Daily check-ins**: Reference the coordination timeline
- **Integration testing**: Follow the checkpoint schedule
- **Handoff coordination**: Agents must notify next dependent agent

## 📋 Required Reading for All Agents

Every agent must read these core files:
1. `/home/insulto/torematrix_labs2/CLAUDE.md` - Project context
2. `/home/insulto/torematrix_labs2/PDFJS_COORDINATION.md` - Coordination guide
3. Their specific `AGENT_X_PDFJS.md` instruction file
4. Their specific `AGENT_X_PROMPT.md` prompt file

## 🔗 Integration Dependencies

```
Agent 1 (Foundation) 
    ↓
Agent 2 (Bridge) 
    ↓ 
Agent 3 (Performance) ←→ Agent 4 (Features)
    ↓                      ↓
    Final Integration Testing
```

## ✅ Success Criteria

Each agent must:
- [ ] Complete all tasks in their instruction file
- [ ] Meet all performance targets
- [ ] Achieve >95% test coverage
- [ ] Write comprehensive documentation
- [ ] Successfully integrate with other agents
- [ ] Pass all integration checkpoints

## 📞 Communication Protocol

- **Daily Progress**: Update GitHub issues
- **Coordination**: Use PDFJS_COORDINATION.md timeline
- **Handoffs**: Explicit notification between dependent agents
- **Integration**: Continuous testing at checkpoints
- **Completion**: Mark GitHub issues complete with summary

---

**Start with your agent's prompt file - it has everything you need to succeed!**