# PROMPT FOR CLAUDE CODE INSTANCE 1

Copy and paste this entire prompt into a new Claude Code instance:

---

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