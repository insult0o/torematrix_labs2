# PROMPT FOR CLAUDE CODE INSTANCE 3

Copy and paste this entire prompt into a new Claude Code instance:

---

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