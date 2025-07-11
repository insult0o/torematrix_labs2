# Claude Agent Instructions: agent-ui-areas-list

## Session Setup
This agent session is configured for: **agent-ui-areas-list**
**Assigned Issue**: #4

## Getting Started
1. Run: `./startup.sh` to initialize your working environment
2. Check your assigned issue (if any): `gh issue view 4`
3. Start working on your assigned tasks
4. Update progress regularly: `./update_progress.sh`
5. When done: `./complete_session.sh`

## Working Guidelines
- **Focus**: Work only on tasks assigned to this agent
- **Branch**: Use the designated working branch
- **Testing**: Test your changes before completion
- **Communication**: Update progress through GitHub issues
- **Coordination**: Avoid conflicts with other agents

## Essential Commands
```bash
# Check session status
cat session_config.json | jq

# View assigned issue
gh issue view 4 --repo insult0o/tore-matrix-labs

# Update progress  
./update_progress.sh

# Complete session
./complete_session.sh

# Quick status check
../../../scripts/project_operations.sh status
```

## Session Files
- `session_config.json` - Configuration and progress
- `startup.sh` - Initialize session environment
- `update_progress.sh` - Update progress and communicate
- `complete_session.sh` - Finalize work and create PR
- `AGENT_INSTRUCTIONS.md` - This file

## Coordination
This agent is part of a parallel development workflow. Other agents may be working simultaneously on different issues. Coordinate through GitHub Issues and avoid editing the same files when possible.

---
**Session Created**: Fri Jul 11 22:47:18 +00 2025
**Agent**: agent-ui-areas-list
**Ready for parallel development!** 🚀
