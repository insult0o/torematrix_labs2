# Parallel Development Guide for TORE Matrix Labs V3

## 🚀 Quick Start for Claude Code Instances

This guide helps coordinate 3 Claude Code instances working in parallel on TORE Matrix Labs V3.

## 📋 Instance Assignments

### Instance 1: Event Bus System
- **Issue**: #1 (Core Infrastructure)
- **Branch**: `feature/event-bus-system`
- **Priority**: Critical - All components depend on this
- **Estimated Time**: 2-3 days

### Instance 2: Multi-Library PDF Parser
- **Issue**: #41 (Document Processing Enhancement)
- **Branch**: `feature/multi-parser-system`
- **Priority**: High - Improves parsing accuracy
- **Estimated Time**: 3-4 days

### Instance 3: Caching System
- **Issue**: #48 (Performance Infrastructure)
- **Branch**: `feature/caching-system`
- **Priority**: High - Enables fast processing
- **Estimated Time**: 3-4 days

## 🔄 Coordination Protocol

### Daily Sync (via GitHub)
Each instance should:
1. **Morning**: Comment on issue with day's plan
2. **Evening**: Comment with progress summary
3. **Blockers**: Tag other issues if dependencies needed

### Branch Management
```bash
# Before starting each day
git fetch origin
git status  # Ensure on your feature branch

# If you need updates from main
git merge origin/main

# Regular pushes
git push origin feature/[your-feature]
```

### Dependency Handling
- **Instance 1** (Event Bus): No dependencies, build first
- **Instance 2** (PDF Parser): Can work independently
- **Instance 3** (Cache): May use Event Bus for cache events

## 📊 Progress Tracking

### GitHub Issue Updates
```bash
# Mark issue as in-progress
gh issue edit [number] --add-label "in-progress"

# Add progress comment
gh issue comment [number] --body "Progress: [what you completed]"

# When blocked
gh issue comment [number] --body "Blocked by: #[other-issue]"
```

### Commit Message Format
```
feat(component): Brief description

- Detailed point 1
- Detailed point 2

Refs: #[issue-number]
```

Examples:
- `feat(event-bus): Add async event handling`
- `feat(parsers): Implement pdfplumber adapter`
- `feat(cache): Add Redis backend support`

## 🔧 Shared Resources

### Test Documents
Location: `/tests/fixtures/`
- Use existing test PDFs
- Add new test cases as needed
- Document special test cases

### Configuration
- Check `/config/` for templates
- Don't commit local settings
- Use environment variables for secrets

### Documentation
- Update `/docs/` as you build
- Architecture decisions in `/docs/architecture/`
- API docs in docstrings

## 🚦 Integration Points

### Event Bus ↔ Other Components
```python
# Parser might emit events
event_bus.emit('parser.completed', {'doc_id': '123', 'parser': 'pdfplumber'})

# Cache might listen to events
event_bus.on('document.changed', cache.invalidate)
```

### Parser ↔ Cache
```python
# Parser checks cache first
cached_result = cache.get(f"parse:{doc_hash}:{parser_name}")
if not cached_result:
    result = parser.parse(document)
    cache.set(cache_key, result)
```

## 📝 Definition of Done

Each issue is complete when:
- [ ] All acceptance criteria met
- [ ] Tests written and passing (95%+ coverage)
- [ ] Documentation updated
- [ ] Code reviewed (self-review)
- [ ] PR created and linked to issue
- [ ] No linting errors
- [ ] Performance benchmarks documented

## 🆘 Getting Help

### If Blocked
1. Check related documentation in `/docs/`
2. Look at V1 code for inspiration (but don't copy)
3. Comment on GitHub issue with specific question
4. Check if other instances solved similar problems

### Common Issues
- **Import Errors**: Ensure you're in project root
- **Test Failures**: Run specific test with `-v` flag
- **Git Conflicts**: Fetch and merge main regularly

## 🎯 Week 1 Goals

By end of Week 1, we should have:
1. ✅ Event Bus core functionality
2. ✅ Basic multi-parser system
3. ✅ Memory and disk cache layers
4. ✅ All components testable
5. ✅ Initial integration possible

## 📅 Daily Checklist

### Start of Day
- [ ] Pull latest changes
- [ ] Check issue for new comments
- [ ] Plan day's work
- [ ] Update issue with plan

### During Development
- [ ] Commit every 1-2 hours
- [ ] Run tests frequently
- [ ] Update documentation
- [ ] Push to remote branch

### End of Day
- [ ] Push all changes
- [ ] Update issue with progress
- [ ] Note any blockers
- [ ] Plan tomorrow's work

## 🔗 Important Links

- **Repository**: https://github.com/insult0o/torematrix_labs2
- **Issues**: https://github.com/insult0o/torematrix_labs2/issues
- **V3 Design**: `/docs/ENHANCED_SYSTEM_DESIGN_V2.md`
- **Architecture**: `/docs/architecture/overview.md`

---

*Remember: We're building a professional, enterprise-grade system. Quality over speed!*