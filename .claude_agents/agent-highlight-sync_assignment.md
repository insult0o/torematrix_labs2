# Claude Agent Assignment: agent-highlight-sync

## Assigned Issue
- **Issue #**: 1
- **Title**: bug_text_highlight
- **Assigned At**: 2025-07-11 23:23:45
- **Status**: Active

## Problem Description
Fix text highlighting synchronization between extracted content and PDF coordinates

## Expected Files to Modify
- `tore_matrix_labs/ui/highlighting/highlighting_engine.py`
- `tore_matrix_labs/ui/highlighting/coordinate_mapper.py`
- `tore_matrix_labs/ui/components/pdf_viewer.py`
- `tore_matrix_labs/ui/components/page_validation_widget.py`

## Priority Level
High - Core functionality broken

## Instructions for Claude Agent
1. **Start Command**: 
   ```
   You are "agent-highlight-sync" working on GitHub issue #1.
   
   Repository: https://github.com/insult0o/tore-matrix-labs
   Issue: https://github.com/insult0o/tore-matrix-labs/issues/1
   
   Task: Fix text highlighting synchronization between extracted content and PDF coordinates
   Working branch: issue-1-agent-highlight-sync
   ```

2. **Setup Working Branch**:
   ```bash
   git checkout -b issue-1-agent-highlight-sync
   ```

3. **Check Project Status**:
   ```bash
   ./scripts/project_operations.sh status
   ```

4. **Test Projects**: Use "4.tore" and "7.tore" for testing

5. **Progress Updates**: Comment on GitHub issue #1

## Completion Checklist
- [ ] Problem identified and understood
- [ ] Solution implemented
- [ ] Code tested with test projects
- [ ] No regressions introduced
- [ ] Pull request created
- [ ] Issue updated with solution

## Session Recovery
If session is interrupted, restart with:
```bash
git checkout issue-1-agent-highlight-sync
gh issue view 1 --repo insult0o/tore-matrix-labs
```