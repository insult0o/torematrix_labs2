# Claude Memory - TORE Matrix Labs V3

## Project Overview
TORE Matrix Labs V3 is a greenfield rewrite focusing on enterprise-grade document processing pipeline with AI integration.

## Completed Issues

### Issue #6 - Unstructured.io Integration ✅
- **Status**: COMPLETED
- **Sub-issues**: #76, #77, #79, #80 (all completed)
- **Key deliverables**: Async client wrapper, configuration system, exception hierarchy
- **Files**: `/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/`

### Issue #7 - Document Ingestion System ✅
- **Status**: COMPLETED (breakdown and Agent 1 implementation)
- **Sub-issues**: #83, #85, #86, #87
- **Agent 1 work**: Core upload manager, file validation, storage abstraction
- **Files**: `/home/insulto/torematrix_labs2/src/torematrix/ingestion/`
- **Docs**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_*_INGESTION.md`

### Issue #8 - Processing Pipeline Architecture 🔄
- **Status**: BREAKDOWN COMPLETE (ready for implementation)
- **Sub-issues**: #88, #90, #91, #92
- **Architecture**: DAG-based pipeline, plugin processors, worker pool, monitoring
- **Docs**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_*_PIPELINE.md`

## Agent Instruction Files

### Issue #7 (Ingestion)
- `AGENT_1_INGESTION.md` - Core Upload Manager
- `AGENT_2_INGESTION.md` - Queue Management
- `AGENT_3_INGESTION.md` - API & WebSocket
- `AGENT_4_INGESTION.md` - Integration & Testing
- `INGESTION_COORDINATION.md` - Coordination guide

### Issue #8 (Pipeline)
- `AGENT_1_PIPELINE.md` - Core Pipeline Manager
- `AGENT_2_PIPELINE.md` - Processor Plugin System
- `AGENT_3_PIPELINE.md` - Worker Pool & Progress
- `AGENT_4_PIPELINE.md` - Integration & Testing
- `PIPELINE_COORDINATION.md` - Coordination guide

## Key Workflows

### Standard Issue Breakdown
1. Read parent issue from GitHub
2. Create 4 sub-issues for parallel development
3. Create agent instruction files with code examples
4. Create coordination guide
5. Update parent issue with breakdown
6. Create memory reference

### Agent Implementation
1. Agent reads instruction files
2. Implements according to specifications
3. Creates comprehensive tests
4. Documents integration points
5. Completes "end work" routine

### End Work Routine
1. Update issue body with completed checkboxes
2. Add implementation summary
3. Close issue with proper labels
4. Update memory references

## Quick Commands

### View Issues
```bash
gh issue view [number]
gh issue list --state open
```

### Read Instructions
```bash
cat /home/insulto/torematrix_labs2/torematrix_storage/AGENT_*.md
cat /home/insulto/torematrix_labs2/torematrix_storage/*_COORDINATION.md
```

### Run Tests
```bash
cd /home/insulto/torematrix_labs2
python -m pytest tests/ -v
```

## Architecture Decisions

### Technology Stack
- **Language**: Python 3.8+
- **Async**: asyncio throughout
- **API**: FastAPI
- **Queue**: Redis + RQ
- **Storage**: S3/Local abstraction
- **Monitoring**: Prometheus + Grafana
- **Testing**: Pytest

### Design Patterns
- Event-driven architecture (EventBus)
- Plugin system for extensibility
- DAG-based pipeline execution
- Resource pool management
- Circuit breaker for resilience

## GitHub Repository
- **URL**: https://github.com/insult0o/torematrix_labs2
- **Main branch**: main
- **Issues**: Using GitHub Issues for tracking

## Session Context
- Working directory: `/home/insulto/torematrix_labs2`
- Python environment: System Python 3
- Git configured: User insult0o, email miguel.borges.cta@gmail.com

Last Updated: 2025-07-13