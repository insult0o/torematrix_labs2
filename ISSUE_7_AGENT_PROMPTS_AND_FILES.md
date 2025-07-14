# Issue #7 - Document Ingestion System - Agent Prompts and File References

## Overview
This document contains all agent prompts and file references for Issue #7 (Document Ingestion System) broken down into 4 parallelizable sub-issues.

## File Locations

### Agent Instruction Files
- **Agent 1**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_INGESTION.md`
- **Agent 2**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_INGESTION.md`
- **Agent 3**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_3_INGESTION.md`
- **Agent 4**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_4_INGESTION.md`

### Coordination Guide
- **Location**: `/home/insulto/torematrix_labs2/torematrix_storage/INGESTION_COORDINATION.md`

### Summary Documents
- **Breakdown Summary**: `/home/insulto/torematrix_labs2/ISSUE_7_BREAKDOWN_SUMMARY.md`
- **This Reference**: `/home/insulto/torematrix_labs2/ISSUE_7_AGENT_PROMPTS_AND_FILES.md`

## GitHub Issues
- **Parent Issue #7**: https://github.com/insult0o/torematrix_labs2/issues/7
- **Sub-Issue #83** (Agent 1): https://github.com/insult0o/torematrix_labs2/issues/83
- **Sub-Issue #85** (Agent 2): https://github.com/insult0o/torematrix_labs2/issues/85
- **Sub-Issue #86** (Agent 3): https://github.com/insult0o/torematrix_labs2/issues/86
- **Sub-Issue #87** (Agent 4): https://github.com/insult0o/torematrix_labs2/issues/87

## Agent Prompts

### Agent 1 Prompt - Core Upload Manager & File Validation
```
You are Agent 1 working on Issue #83 (Core Upload Manager & File Validation) as part of the TORE Matrix V3 Document Ingestion System.

Your detailed instructions are located at:
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_INGESTION.md

Please read your instructions carefully and implement:
1. Core Upload Manager with session support
2. File validation system (type, content, security)
3. Storage abstraction layer (local + S3)
4. File metadata models
5. Comprehensive unit tests

You are building the foundation layer that other agents will depend on. Focus on:
- Async/await patterns throughout
- Production-grade error handling
- Support for 15+ file formats
- Integration with Unstructured.io for validation

Coordinate with other agents through the shared models defined in your instructions.
```

### Agent 2 Prompt - Queue Management & Batch Processing
```
You are Agent 2 working on Issue #85 (Queue Management & Batch Processing) as part of the TORE Matrix V3 Document Ingestion System.

Your detailed instructions are located at:
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_INGESTION.md

Please read your instructions carefully and implement:
1. Redis/RQ queue configuration and manager
2. Document processing workers
3. Batch processing optimization
4. Progress tracking system
5. Retry mechanisms with exponential backoff

You depend on Agent 1's FileMetadata models. Your events will be consumed by Agent 3. Focus on:
- Scalable queue architecture
- Real-time progress updates via EventBus
- Robust error handling and retries
- Performance optimization for batches

Review the coordination guide at /home/insulto/torematrix_labs2/torematrix_storage/INGESTION_COORDINATION.md for integration details.
```

### Agent 3 Prompt - API Endpoints & WebSocket Progress
```
You are Agent 3 working on Issue #86 (API Endpoints & WebSocket Progress) as part of the TORE Matrix V3 Document Ingestion System.

Your detailed instructions are located at:
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_3_INGESTION.md

Please read your instructions carefully and implement:
1. FastAPI REST endpoints for file uploads
2. WebSocket server for real-time progress
3. Session-based upload management
4. Client SDK for easy integration
5. API response models and documentation

You depend on Agent 1's UploadManager and Agent 2's progress events. Focus on:
- RESTful API design
- WebSocket connection management
- Real-time event broadcasting
- User-friendly client SDK

Review the coordination guide at /home/insulto/torematrix_labs2/torematrix_storage/INGESTION_COORDINATION.md for integration details.
```

### Agent 4 Prompt - Integration & Testing
```
You are Agent 4 working on Issue #87 (Integration & Testing) as part of the TORE Matrix V3 Document Ingestion System.

Your detailed instructions are located at:
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_4_INGESTION.md

Please read your instructions carefully and implement:
1. System integration layer connecting all components
2. End-to-end test suite
3. Performance benchmarking tests
4. Docker compose test environment
5. Production deployment guide

You depend on all other agents' work. Focus on:
- Wiring components together properly
- Comprehensive E2E test scenarios
- Performance testing and optimization
- Production-ready deployment documentation

Review the coordination guide at /home/insulto/torematrix_labs2/torematrix_storage/INGESTION_COORDINATION.md for full system architecture.

Wait for Agents 1-3 to complete their core components before starting integration work.
```

## Key Implementation Details

### Shared Dependencies
- All agents use models from Agent 1's `torematrix.ingestion.models`
- Event system from Agent 2's `torematrix.core.events`
- Unstructured.io client from Issue #6 implementation

### Directory Structure
```
src/torematrix/
├── ingestion/
│   ├── upload_manager.py     # Agent 1
│   ├── validators.py         # Agent 1
│   ├── storage.py           # Agent 1
│   ├── models.py            # Agent 1
│   ├── queue_manager.py     # Agent 2
│   ├── queue_config.py      # Agent 2
│   ├── processors.py        # Agent 2
│   ├── progress.py          # Agent 2
│   └── integration.py       # Agent 4
├── api/
│   ├── routers/
│   │   └── ingestion.py     # Agent 3
│   ├── websockets/
│   │   └── progress.py      # Agent 3
│   ├── client/
│   │   └── ingestion_client.py  # Agent 3
│   └── models.py            # Agent 3
└── core/
    └── events.py            # Agent 2

tests/
├── unit/
│   ├── ingestion/
│   │   ├── test_upload_manager.py  # Agent 1
│   │   ├── test_validators.py      # Agent 1
│   │   ├── test_queue_manager.py   # Agent 2
│   │   └── test_processors.py      # Agent 2
│   └── api/
│       └── test_ingestion_endpoints.py  # Agent 3
├── e2e/
│   └── test_document_ingestion.py   # Agent 4
└── performance/
    └── test_ingestion_performance.py # Agent 4
```

## Success Criteria
- Handle 100+ concurrent file uploads
- Process documents in < 30 seconds average
- Support 15+ file formats via Unstructured.io
- Real-time progress updates with < 1s latency
- 99.9% reliability with automatic retries
- Comprehensive test coverage (90%+)
- Production-ready with monitoring

## Development Workflow
1. Agents 1-3 work in parallel on their components
2. Agent 4 prepares test infrastructure
3. Integration phase when core components ready
4. Full E2E testing and performance optimization
5. Documentation and deployment guide finalization

## Notes
- This is part of the TORE Matrix V3 greenfield rewrite
- Builds on Issue #6 (Unstructured.io Integration) which is complete
- Uses event-driven architecture for loose coupling
- All components must be async-compatible
- Production deployment uses Kubernetes

Last Updated: 2025-07-13