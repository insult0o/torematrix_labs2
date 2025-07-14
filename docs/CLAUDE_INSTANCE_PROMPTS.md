# Claude Code Instance Prompts for Parallel Development

## 🚀 Overview

These prompts are designed for 3 separate Claude Code instances to work in parallel on TORE Matrix Labs V3. Each instance will handle a different critical component from the Priority 1 issues.

---

## 📋 Instance 1: Event Bus System (Issue #1)

### Complete Prompt:

```
You are working on TORE Matrix Labs V3, a ground-up rewrite of a document processing platform. Your specific task is to implement the Event Bus System (Issue #1).

## Project Context
- **Repository**: https://github.com/insult0o/torematrix_labs2
- **Working Directory**: /home/insulto/torematrix_labs2
- **Current Branch**: You'll create feature/event-bus-system
- **Issue Number**: #1
- **Priority**: 1 (Critical Infrastructure)

## Initial Setup Tasks
1. First, verify your environment:
   ```bash
   pwd  # Should be /home/insulto/torematrix_labs2
   git status  # Check current branch
   git pull origin main  # Get latest changes
   ```

2. Read the GitHub issue:
   ```bash
   gh issue view 1 --repo insult0o/torematrix_labs2
   ```

3. Create and checkout your feature branch:
   ```bash
   git checkout -b feature/event-bus-system
   git push -u origin feature/event-bus-system
   ```

4. Update the issue to assign yourself and mark as in-progress:
   ```bash
   gh issue edit 1 --repo insult0o/torematrix_labs2 --add-label "in-progress"
   gh issue comment 1 --repo insult0o/torematrix_labs2 --body "Starting implementation of Event Bus System. Working on feature/event-bus-system branch."
   ```

## Key Implementation Requirements
Based on the system design, the Event Bus must:
- Replace V1's complex signal chains with clean event-driven architecture
- Support async event processing
- Include middleware for logging and validation
- Be type-safe with proper event definitions
- Support performance monitoring

## Files to Create/Modify
1. `/src/torematrix/core/events/event_bus.py` - Main implementation
2. `/src/torematrix/core/events/event_types.py` - Event definitions
3. `/src/torematrix/core/events/middleware.py` - Middleware system
4. `/tests/unit/core/test_event_bus.py` - Unit tests
5. `/docs/architecture/event_bus.md` - Technical documentation

## Important Context Files to Read
- `/docs/ENHANCED_SYSTEM_DESIGN_V2.md` - Section on Event Bus
- `/docs/architecture/overview.md` - Overall architecture
- `/src/torematrix/__init__.py` - Package structure

## Development Guidelines
1. Use Python 3.11+ features (type hints, async/await)
2. Follow clean architecture principles
3. Write tests first (TDD) - aim for 95%+ coverage
4. Document all public APIs
5. Regular commits with clear messages

## Progress Tracking
After each major milestone:
```bash
# Commit your changes
git add -A
git commit -m "feat(event-bus): [specific change description]"
git push

# Update the issue
gh issue comment 1 --repo insult0o/torematrix_labs2 --body "[Progress update]"
```

## Completion Checklist
- [ ] Core EventBus class implemented
- [ ] Event types defined with proper typing
- [ ] Middleware system functional
- [ ] Async event handling working
- [ ] Performance monitoring integrated
- [ ] Unit tests with 95%+ coverage
- [ ] Integration tests written
- [ ] Documentation complete
- [ ] Code reviewed and refactored
- [ ] PR created and linked to issue

Remember: You're building the foundation for all component communication in V3. This replaces the complex signal system from V1 with a clean, maintainable solution.
```

---

## 📋 Instance 2: Multi-Library PDF Parser System (Issue #41)

### Complete Prompt:

```
You are working on TORE Matrix Labs V3, implementing the Multi-Library PDF Parser System (Issue #41) - a critical enhancement for accurate document processing.

## Project Context
- **Repository**: https://github.com/insult0o/torematrix_labs2
- **Working Directory**: /home/insulto/torematrix_labs2
- **Current Branch**: You'll create feature/multi-parser-system
- **Issue Number**: #41
- **Priority**: High (PDF Enhancement)

## Initial Setup Tasks
1. Verify your environment:
   ```bash
   pwd  # Should be /home/insulto/torematrix_labs2
   git status  # Check current branch
   git pull origin main  # Get latest changes
   ```

2. Read the GitHub issue thoroughly:
   ```bash
   gh issue view 41 --repo insult0o/torematrix_labs2
   ```

3. Create and checkout your feature branch:
   ```bash
   git checkout -b feature/multi-parser-system
   git push -u origin feature/multi-parser-system
   ```

4. Update the issue status:
   ```bash
   gh issue edit 41 --repo insult0o/torematrix_labs2 --add-label "in-progress"
   gh issue comment 41 --repo insult0o/torematrix_labs2 --body "Starting implementation of Multi-Library PDF Parser System. This will provide fallback parsing with pdfplumber, PyMuPDF, pdfminer.six, and PyPDF2."
   ```

## Key Implementation Requirements
From the PDF-to-LLM best practices analysis:
- Implement fallback system with multiple PDF parsing libraries
- Auto-select parser based on document characteristics
- Merge results from multiple parsers for best output
- Handle parser failures gracefully
- Cache parsing results for performance

## Files to Create/Modify
1. `/src/torematrix/infrastructure/parsers/pdf_parser_manager.py` - Main system
2. `/src/torematrix/infrastructure/parsers/pdfplumber_parser.py`
3. `/src/torematrix/infrastructure/parsers/pymupdf_parser.py`
4. `/src/torematrix/infrastructure/parsers/pdfminer_parser.py`
5. `/src/torematrix/infrastructure/parsers/pypdf2_parser.py`
6. `/src/torematrix/infrastructure/parsers/parser_selector.py` - Selection logic
7. `/tests/unit/infrastructure/parsers/` - Test directory
8. `/tests/fixtures/pdf_samples/` - Test PDFs

## Important Context Files to Read
- `/docs/PDF_TO_LLM_GAP_ANALYSIS.md` - Missing capabilities
- `/docs/ENHANCED_SYSTEM_DESIGN_V2.md` - Multi-parser architecture
- `/docs/CACHING_AND_INCREMENTAL_PROCESSING.md` - Caching strategies

## Dependencies to Add
Update `/pyproject.toml`:
```toml
dependencies = [
    # ... existing deps
    "pdfplumber>=0.9.0",
    "PyMuPDF>=1.23.0",
    "pdfminer.six>=20221105",
    "PyPDF2>=3.0.0",
]
```

## Implementation Strategy
1. Start with base parser interface
2. Implement each parser adapter
3. Create intelligent selector based on PDF characteristics
4. Build result merger for combining outputs
5. Add caching layer
6. Comprehensive testing with various PDF types

## Testing Requirements
- Unit tests for each parser adapter
- Integration tests with real PDFs
- Performance benchmarks
- Fallback scenario testing
- Cache hit/miss testing

## Progress Tracking
```bash
# Regular commits
git add -A
git commit -m "feat(parsers): [specific implementation detail]"
git push

# Update issue with progress
gh issue comment 41 --repo insult0o/torematrix_labs2 --body "[What you implemented today]"
```

## Completion Checklist
- [ ] Base parser interface defined
- [ ] All 4 parser adapters implemented
- [ ] Parser selector with document profiling
- [ ] Result merger algorithm
- [ ] Caching integration
- [ ] Error handling and fallback logic
- [ ] 95%+ test coverage
- [ ] Performance benchmarks documented
- [ ] Technical documentation written
- [ ] PR created with comprehensive description

Remember: This system is critical for handling diverse PDF types. Each parser has strengths - pdfplumber for layout, PyMuPDF for speed, pdfminer for detail, PyPDF2 for simplicity.
```

---

## 📋 Instance 3: Caching and Incremental Processing (Issue #48)

### Complete Prompt:

```
You are working on TORE Matrix Labs V3, implementing the Caching and Incremental Processing system (Issue #48) - essential for performance optimization.

## Project Context
- **Repository**: https://github.com/insult0o/torematrix_labs2
- **Working Directory**: /home/insulto/torematrix_labs2
- **Current Branch**: You'll create feature/caching-system
- **Issue Number**: #48
- **Priority**: High (Core Infrastructure)

## Initial Setup Tasks
1. Verify your environment:
   ```bash
   pwd  # Should be /home/insulto/torematrix_labs2
   git status  # Check current branch
   git pull origin main  # Get latest changes
   ```

2. Read the GitHub issue in detail:
   ```bash
   gh issue view 48 --repo insult0o/torematrix_labs2
   ```

3. Create and checkout your feature branch:
   ```bash
   git checkout -b feature/caching-system
   git push -u origin feature/caching-system
   ```

4. Update issue status:
   ```bash
   gh issue edit 48 --repo insult0o/torematrix_labs2 --add-label "in-progress"
   gh issue comment 48 --repo insult0o/torematrix_labs2 --body "Starting implementation of multi-level caching system. This will include memory, disk, Redis, and object storage layers with incremental processing support."
   ```

## Key Implementation Requirements
From the caching design document:
- 4-level cache hierarchy (Memory → Disk → Redis → Object Storage)
- Change detection for incremental processing
- Cache key generation and management
- TTL and eviction policies
- Performance metrics collection
- Support for large objects with compression

## Files to Create/Modify
1. `/src/torematrix/core/cache/multi_level_cache.py` - Main cache system
2. `/src/torematrix/core/cache/cache_backends.py` - Backend implementations
3. `/src/torematrix/core/cache/change_detector.py` - File change detection
4. `/src/torematrix/core/cache/incremental_processor.py` - Incremental logic
5. `/src/torematrix/core/cache/cache_metrics.py` - Performance tracking
6. `/tests/unit/core/cache/` - Test directory
7. `/config/cache_config.yaml` - Configuration template

## Important Context Files to Read
- `/docs/CACHING_AND_INCREMENTAL_PROCESSING.md` - Complete design
- `/docs/ENHANCED_SYSTEM_DESIGN_V2.md` - Cache integration points
- Issue #41 (Multi-parser) - You'll cache parser results

## Dependencies to Add
Update `/pyproject.toml`:
```toml
dependencies = [
    # ... existing deps
    "diskcache>=5.6.0",
    "redis>=5.0.0",
    "cachetools>=5.3.0",
    "boto3>=1.28.0",  # For S3 object storage
]
```

## Implementation Phases
1. **Phase 1**: Core cache interface and memory cache
2. **Phase 2**: Disk cache with TTL support
3. **Phase 3**: Redis integration (optional)
4. **Phase 4**: Object storage for large files
5. **Phase 5**: Change detection system
6. **Phase 6**: Incremental processor
7. **Phase 7**: Metrics and monitoring

## Cache Key Strategy
```python
# Example key format
"namespace:version:document_hash:operation:params_hash"
# e.g., "parse:v1:abc123:pdfplumber:def456"
```

## Testing Requirements
- Unit tests for each cache level
- Integration tests for cache hierarchy
- Performance benchmarks
- Concurrent access testing
- Cache invalidation testing
- Incremental processing scenarios

## Progress Tracking
```bash
# Commit after each phase
git add -A
git commit -m "feat(cache): [specific feature, e.g., 'Add disk cache backend']"
git push

# Update issue
gh issue comment 48 --repo insult0o/torematrix_labs2 --body "Completed Phase X: [description]"
```

## Configuration Example
Create `/config/cache_config.yaml`:
```yaml
caching:
  memory:
    size_mb: 1024
    ttl_seconds: 3600
  disk:
    path: "/var/cache/torematrix"
    size_gb: 50
  redis:
    enabled: false  # Optional
    host: "localhost"
  object_storage:
    enabled: false  # Optional
    type: "s3"
```

## Completion Checklist
- [ ] Multi-level cache interface
- [ ] Memory cache with TTL
- [ ] Disk cache implementation
- [ ] Redis backend (optional)
- [ ] Object storage backend
- [ ] Change detection system
- [ ] Incremental processor
- [ ] Cache key management
- [ ] Metrics collection
- [ ] Configuration system
- [ ] 95%+ test coverage
- [ ] Performance benchmarks
- [ ] Documentation complete
- [ ] PR created with benchmarks

Remember: This cache system is critical for performance. It should make the document processing 10x faster for repeated operations while supporting incremental updates for changed documents.
```

---

## 🎯 General Guidelines for All Instances

### Git Workflow
1. Always work on your feature branch
2. Commit frequently with descriptive messages
3. Push regularly to avoid losing work
4. Update the GitHub issue with progress

### Communication
- Comment on issues when you start/stop work
- Ask questions on the issue if blocked
- Create draft PR early for visibility
- Tag related issues in commits

### Testing
- Run tests before committing:
  ```bash
  pytest tests/unit/[your-component] -v
  pytest --cov=[your-module] --cov-report=html
  ```

### Code Quality
- Use pre-commit hooks if available
- Follow Python type hints
- Document all public APIs
- Keep functions small and focused

### When Complete
1. Create Pull Request:
   ```bash
   gh pr create --title "[Component]: Brief description" \
                --body "Closes #[issue-number]\n\n## Summary\n..." \
                --base main
   ```

2. Link PR to issue:
   ```bash
   gh issue comment [issue-number] --repo insult0o/torematrix_labs2 \
                    --body "Implementation complete. PR: #[pr-number]"
   ```

---

*Each instance should save their specific prompt section for reference during development*