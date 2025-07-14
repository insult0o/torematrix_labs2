# Issue #7 - Document Ingestion System - Memory Reference

## Overview
Issue #7 (Document Ingestion System) has been broken down into 4 parallelizable sub-issues for the TORE Matrix V3 project. This system handles multi-file uploads, processing through Unstructured.io, and batch operations with real-time progress tracking.

## Created Issues
- **Parent Issue #7**: Document Ingestion System
- **Issue #83**: Core Upload Manager & File Validation (Agent 1)
- **Issue #85**: Queue Management & Batch Processing (Agent 2)
- **Issue #86**: API Endpoints & WebSocket Progress (Agent 3)
- **Issue #87**: Integration & Testing (Agent 4)

## File References

### Agent Instructions
All agent instruction files are stored in `/home/insulto/torematrix_labs2/torematrix_storage/`:
- `AGENT_1_INGESTION.md` - Core Upload Manager instructions
- `AGENT_2_INGESTION.md` - Queue Management instructions
- `AGENT_3_INGESTION.md` - API & WebSocket instructions
- `AGENT_4_INGESTION.md` - Integration & Testing instructions

### Coordination & Documentation
- `INGESTION_COORDINATION.md` - Agent coordination guide
- `ISSUE_7_BREAKDOWN_SUMMARY.md` - Breakdown summary
- `ISSUE_7_AGENT_PROMPTS_AND_FILES.md` - All prompts and references

## Key Architecture Decisions

### Component Breakdown
1. **Upload Layer** (Agent 1): Handles file validation, storage, metadata
2. **Processing Layer** (Agent 2): Queue management, workers, progress tracking
3. **API Layer** (Agent 3): REST endpoints, WebSocket, client SDK
4. **Integration Layer** (Agent 4): System integration, testing, deployment

### Technology Stack
- **API**: FastAPI with WebSocket support
- **Queue**: Redis + RQ (Redis Queue)
- **Storage**: Local filesystem + S3 abstraction
- **Processing**: Unstructured.io integration (from Issue #6)
- **Database**: PostgreSQL for metadata
- **Testing**: Pytest + Docker Compose

### Key Interfaces
```python
# Shared models (Agent 1 → All)
FileMetadata, FileStatus, UploadSession, UploadResult

# Event system (Agent 2 → Agent 3)
EventBus, ProcessingEvent

# Upload flow
API (Agent 3) → UploadManager (Agent 1) → Queue (Agent 2) → Processing

# Progress flow
Worker (Agent 2) → EventBus → WebSocket (Agent 3) → Client
```

## Success Metrics
- Handle 100+ concurrent file uploads
- Process documents in < 30 seconds average
- Support 15+ file formats
- Real-time progress updates < 1s latency
- 99.9% reliability with retries
- 90%+ test coverage

## Development Status
- ✅ All sub-issues created
- ✅ Agent instructions written
- ✅ Coordination guide complete
- ✅ Parent issue updated
- 🔄 Ready for parallel development

## Quick Commands
```bash
# View parent issue
gh issue view 7

# View sub-issues
gh issue view 83  # Agent 1
gh issue view 85  # Agent 2
gh issue view 86  # Agent 3
gh issue view 87  # Agent 4

# Read instructions
cat /home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_INGESTION.md
cat /home/insulto/torematrix_labs2/torematrix_storage/INGESTION_COORDINATION.md
```

## Notes
- Builds on Issue #6 (Unstructured.io Integration) which is complete
- Part of TORE Matrix V3 greenfield rewrite
- Uses event-driven architecture
- All components async-compatible
- Production deployment on Kubernetes

Last Updated: 2025-07-13