# 🚨 CRITICAL SESSION HANDOFF - USAGE LIMIT APPROACHING

## 📋 Immediate Actions for Next Claude Instance

### 1. FIRST PRIORITY: Fix Dialog System Import Issues (30min total)
These are **critical blocking issues** that prevent usage of 3000+ lines of sophisticated dialog implementation:

#### Issue #138: PyQt6/PySide6 Mismatch
```bash
# File: tests/unit/ui/dialogs/test_dialogs.py:1
# Change: from PySide6.QtWidgets import → from PyQt6.QtWidgets import
gh issue view 138
```

#### Issue #139: Missing EventType Import  
```bash
# File: src/torematrix/ui/dialogs/base.py:27
# Add: from ...core.events.types import EventType
gh issue view 139
```

#### Issue #140: DialogManager Not Exported
```bash
# File: src/torematrix/ui/dialogs/__init__.py
# Add: from .base import DialogManager
gh issue view 140
```

### 2. SECOND PRIORITY: Deploy PDF.js Integration (Multi-Agent Ready)
```bash
# Command to deploy all 4 agents immediately:
"let's work on issue 16"

# All files prepared and ready:
# - AGENT_1_PDFJS.md (Core Viewer Foundation)
# - AGENT_2_PDFJS.md (Qt-JavaScript Bridge)  
# - AGENT_3_PDFJS.md (Performance Optimization)
# - AGENT_4_PDFJS.md (Advanced Features)
# - PDFJS_COORDINATION.md (Timeline & Integration)
# - ISSUE_16_AGENT_PROMPTS.md (Copy-paste prompts)
```

## 🎯 Resumption Commands

### Immediate Continuation
```bash
"continue from where we left off"
```

### Fix Critical Issues First (Recommended)
```bash
"fix dialog import issues"
```

### Deploy PDF.js Multi-Agent Workflow
```bash
"let's work on issue 16"
```

### Get Current Status
```bash
"status report"
```

## 📁 Critical Memory Files (READ THESE FIRST)

### Global Context
- `/home/insulto/.claude/CLAUDE.md` - Global instructions with session state
- `/home/insulto/torematrix_labs2/CLAUDE.md` - Project context and workflow
- `/home/insulto/torematrix_labs2/CLAUDE.local.md` - Session work logs

### PDF.js Integration Files (All Ready)
- `/home/insulto/torematrix_labs2/AGENT_1_PDFJS.md` - Agent 1 instructions
- `/home/insulto/torematrix_labs2/AGENT_2_PDFJS.md` - Agent 2 instructions  
- `/home/insulto/torematrix_labs2/AGENT_3_PDFJS.md` - Agent 3 instructions
- `/home/insulto/torematrix_labs2/AGENT_4_PDFJS.md` - Agent 4 instructions
- `/home/insulto/torematrix_labs2/PDFJS_COORDINATION.md` - Coordination guide
- `/home/insulto/torematrix_labs2/ISSUE_16_AGENT_PROMPTS.md` - Deployment prompts

## 🚨 Current State Summary

### Completed This Session
- ✅ **PDF.js Integration Workflow** - Complete 4-agent system prepared
- ✅ **Agent Instructions** - All detailed implementation guides created
- ✅ **GitHub Sub-Issues** - #124-127 ready for parallel development
- ✅ **Critical Issues Created** - #138-141 for dialog system fixes
- ✅ **Coordination Documentation** - Timeline and integration points defined

### Ready for Immediate Action
1. **Dialog Import Fixes** - 3 simple fixes to unblock sophisticated dialog system
2. **PDF.js Multi-Agent Deployment** - Everything prepared, just need to execute
3. **Continued Development** - Multiple active workstreams ready

### Repository Status
- **Current Branch**: `feature/unified-model-base-types`
- **GitHub Issues**: #138-141 (critical fixes), #124-127 (PDF.js agents)
- **Status**: All work committed and synced
- **Next**: Choose between dialog fixes or PDF.js deployment

## 🎯 Recommended Approach for Next Session

1. **Start with Dialog Fixes** - Quick wins to unblock major system
2. **Then Deploy PDF.js Agents** - Comprehensive multi-agent workflow
3. **Continue with other priorities** as time allows

## 🤖 Session Persistence Complete

All Claude instances now have:
- ✅ Complete context preservation
- ✅ Clear next action priorities  
- ✅ Ready-to-execute workflows
- ✅ Detailed implementation guides
- ✅ GitHub issue tracking
- ✅ File location references

**Ready for seamless continuation across usage limits and sessions.**