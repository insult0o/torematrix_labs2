# ISSUE #20 AGENT DEPLOYMENT PROMPTS

## 🎯 Ready-to-Use Agent Deployment Commands

Copy and paste these exact prompts to deploy each agent for **Issue #20: Document Viewer Zoom/Pan Controls**.

---

## 🚀 AGENT 1 DEPLOYMENT - Core Zoom Engine

**Use this exact prompt to start Agent 1:**

```
I am Agent 1 working on Issue #20 Document Viewer Zoom/Pan Controls. My specific assignment is Sub-Issue #20.1: Core Zoom Engine & Animation Framework.

Please read the file AGENT_1_ZOOM.md for my complete instructions and implement the Core Zoom Engine & Animation Framework as specified.

My key responsibilities:
- Core zoom engine with exponential scaling algorithms  
- GPU-accelerated animation framework with easing
- Zoom level constraints and validation system
- Zoom around specific point calculations
- Performance optimization for large documents
- Thread-safe zoom state management

My branch: feature/zoom-engine-agent1-issue201

Please start by reading my instruction file and implementing the zoom engine as specified.
```

---

## 🚀 AGENT 2 DEPLOYMENT - Pan Controls & User Interaction

**Use this exact prompt to start Agent 2:**

```
I am Agent 2 working on Issue #20 Document Viewer Zoom/Pan Controls. My specific assignment is Sub-Issue #20.2: Pan Controls & User Interaction.

Please read the file AGENT_2_ZOOM.md for my complete instructions and implement the Pan Controls & User Interaction system as specified.

My key responsibilities:
- Mouse drag panning with smooth movement
- Pan boundary detection and limits  
- Pan inertia and momentum physics
- Touch gesture recognition for mobile
- Multi-touch pinch/zoom integration
- Keyboard navigation controls
- Cross-platform input handling

My branch: feature/pan-controls-agent2-issue202

I depend on Agent 1's zoom engine completion. Please start by reading my instruction file and implementing the pan controls as specified.
```

---

## 🚀 AGENT 3 DEPLOYMENT - Navigation UI & Minimap System

**Use this exact prompt to start Agent 3:**

```
I am Agent 3 working on Issue #20 Document Viewer Zoom/Pan Controls. My specific assignment is Sub-Issue #20.3: Navigation UI & Minimap System.

Please read the file AGENT_3_ZOOM.md for my complete instructions and implement the Navigation UI & Minimap System as specified.

My key responsibilities:
- Minimap component with document overview
- Zoom preset buttons (50%, 100%, 200%, Fit)
- Zoom level indicator and slider
- Zoom-to-selection functionality  
- Navigation toolbar integration
- Visual zoom/pan feedback systems
- Zoom history tracking and navigation

My branch: feature/navigation-ui-agent3-issue203

I depend on both Agent 1 (zoom engine) and Agent 2 (pan controls) completion. Please start by reading my instruction file and implementing the navigation UI as specified.
```

---

## 🚀 AGENT 4 DEPLOYMENT - Integration, Testing & Performance

**Use this exact prompt to start Agent 4:**

```
I am Agent 4 working on Issue #20 Document Viewer Zoom/Pan Controls. My specific assignment is Sub-Issue #20.4: Integration, Testing & Performance.

Please read the file AGENT_4_ZOOM.md for my complete instructions and implement the Integration, Testing & Performance system as specified.

My key responsibilities:
- Full system integration testing
- Performance profiling and optimization
- Cross-browser compatibility verification
- Mobile device testing and optimization
- Accessibility compliance (WCAG 2.1)
- Error handling and edge case management
- Production deployment preparation
- Documentation and API reference completion

My branch: feature/zoom-integration-agent4-issue204

I depend on all previous agents (1, 2, and 3) completion for final integration. Please start by reading my instruction file and implementing the integration system as specified.
```

---

## 📋 Deployment Sequence

### Phase 1: Foundation (Days 1-2)
1. **Deploy Agent 1 FIRST** - Core zoom engine (no dependencies)
2. Wait for Agent 1 completion before proceeding

### Phase 2: Interaction (Days 2-3)  
1. **Deploy Agent 2** after Agent 1 completes (depends on zoom engine)
2. Agent 2 can work in parallel with Agent 1 testing/polish

### Phase 3: User Interface (Days 3-4)
1. **Deploy Agent 3** after Agents 1&2 complete (depends on both)
2. Agent 3 needs the core functionality from previous agents

### Phase 4: Integration (Days 4-6)
1. **Deploy Agent 4** after all previous agents complete
2. Agent 4 integrates everything into production-ready system

---

## 📁 Required Files for Each Agent

### All Agents Need Access To:
- `AGENT_X_ZOOM.md` - Their specific instruction file
- `ZOOM_COORDINATION.md` - Coordination guide with interfaces
- `ISSUE_20_AGENT_PROMPTS.md` - This file with deployment prompts

### Agent-Specific Instruction Files:
- **Agent 1**: `AGENT_1_ZOOM.md` - Core Zoom Engine instructions
- **Agent 2**: `AGENT_2_ZOOM.md` - Pan Controls instructions  
- **Agent 3**: `AGENT_3_ZOOM.md` - Navigation UI instructions
- **Agent 4**: `AGENT_4_ZOOM.md` - Integration instructions

---

## ✅ Verification Commands

### Check Agent Readiness:
```bash
# Verify all instruction files exist
ls -la AGENT_*_ZOOM.md ZOOM_COORDINATION.md

# Check GitHub issues were created
gh issue list --label zoom

# Verify branch naming convention
git branch -a | grep -E "(zoom|pan)"
```

### Monitor Agent Progress:
```bash
# Check current branch and commits
git log --oneline -10

# View current agent's instruction file
cat AGENT_X_ZOOM.md  # Replace X with agent number

# Check test coverage
pytest --cov=src/torematrix/ui/viewer/controls/
```

---

## 🚨 Important Notes

### For Agent Deployment:
1. **Always read the instruction file first** before starting implementation
2. **Create the correct branch** as specified in instructions
3. **Follow the exact file structure** provided in instruction files
4. **Implement >95% test coverage** as required
5. **Meet all performance benchmarks** specified for your agent

### For Coordination:
1. **Agent 1 is independent** - can start immediately
2. **Agent 2 needs Agent 1's zoom engine** - wait for completion
3. **Agent 3 needs Agents 1&2** - wait for both completions
4. **Agent 4 needs all previous agents** - final integration role

### For Quality Assurance:
1. **Run tests before PR creation** - ensure >95% coverage
2. **Follow the "end work" routine** - create PR and close sub-issue
3. **Update parent issue #20** - report completion progress
4. **Cross-reference sub-issue numbers** - maintain traceability

---

## 🎯 Success Criteria

### Individual Agent Success:
- [ ] All assigned files implemented with comprehensive functionality
- [ ] >95% test coverage achieved and verified
- [ ] Performance benchmarks met for agent's components
- [ ] Integration APIs provided for other agents
- [ ] Pull request created and ready for review
- [ ] Sub-issue closed with completion summary

### Overall System Success:
- [ ] Smooth zoom operations (10% to 800% range)
- [ ] Responsive pan controls with momentum physics
- [ ] Intuitive navigation UI with minimap and presets
- [ ] Complete system integration with error handling
- [ ] Cross-platform compatibility verified
- [ ] Accessibility compliance (WCAG 2.1) achieved
- [ ] Production-ready deployment configuration

---

**Ready for immediate deployment! Start with Agent 1 using the prompt above.** 🚀