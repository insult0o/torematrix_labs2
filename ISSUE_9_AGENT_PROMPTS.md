# ISSUE #9 - READY-TO-USE AGENT PROMPTS

## 🚀 Quick Start Agent Prompts

Use these exact prompts to start each agent on their sub-issue implementation:

### Agent 1 - Core Parser Framework
```
Let's work on issue 96. I need to implement the core parser framework with abstract base classes and factory pattern that all specialized parsers will inherit from. Please read the AGENT_1_PARSERS.md file for detailed instructions and implement the complete foundation system with >95% test coverage.
```

### Agent 2 - Table & List Parsers  
```
Let's work on issue 97. I need to implement specialized parsers for tables and lists with structure preservation and hierarchy detection. Please read the AGENT_2_PARSERS.md file for detailed instructions and wait for Agent 1's base framework completion before starting.
```

### Agent 3 - Image & Formula Parsers
```
Let's work on issue 99. I need to implement advanced parsers for images and mathematical formulas with OCR integration and LaTeX conversion. Please read the AGENT_3_PARSERS.md file for detailed instructions and wait for Agent 1's base framework completion before starting.
```

### Agent 4 - Code Parser & Integration
```
Let's work on issue 101. I need to implement the code snippet parser and complete integration system with caching and monitoring. Please read the AGENT_4_PARSERS.md file for detailed instructions and wait for all other agents to complete before starting the final integration phase.
```

## 📋 Agent File Reference Guide

### Core Documentation Files
- `AGENT_1_PARSERS.md` - Complete implementation guide for Agent 1
- `AGENT_2_PARSERS.md` - Complete implementation guide for Agent 2  
- `AGENT_3_PARSERS.md` - Complete implementation guide for Agent 3
- `AGENT_4_PARSERS.md` - Complete implementation guide for Agent 4
- `PARSERS_COORDINATION.md` - Inter-agent coordination and timeline

### GitHub Sub-Issues
- **Issue #96** - Agent 1: Core Parser Framework & Base Classes
- **Issue #97** - Agent 2: Table & List Parsers Implementation
- **Issue #99** - Agent 3: Image & Formula Parsers with OCR
- **Issue #101** - Agent 4: Code Parser & Integration System

### Expected Timeline
- **Days 1-2**: Agent 1 builds foundation framework
- **Days 2-4**: Agents 2 & 3 work in parallel on specialized parsers
- **Days 4-6**: Agent 4 integrates everything into production system

## 🎯 Success Validation

After each agent completes, validate with:
```bash
# Run agent's specific tests
pytest tests/unit/core/processing/parsers/test_[agent_component].py -v

# Verify integration points work
python -c "from src.torematrix.core.processing.parsers import ParserFactory; print('✅ Integration ready')"
```

## 📊 Progress Tracking

Monitor progress via GitHub issues:
- Main Issue #9: Overall parser system progress
- Sub-issues #96, #97, #99, #101: Individual agent progress
- Check test coverage and performance benchmarks in each PR

This provides everything needed for efficient multi-agent coordination!