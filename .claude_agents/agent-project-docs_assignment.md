# Claude Agent Assignment: agent-project-docs

## Assigned Issue
- **Issue #**: 2
- **Title**: bug_multiple_docs_loaded
- **Assigned At**: 2025-07-11 23:23:45
- **Status**: Active

## Problem Description
Fix duplicate documents appearing when reprocessing and reloading projects

## Expected Files to Modify
- `tore_matrix_labs/ui/main_window.py`
- `tore_matrix_labs/ui/components/project_manager_widget.py`
- `tore_matrix_labs/core/document_processor.py`
- `tore_matrix_labs/models/project_models.py`

## Priority Level
Medium - Project state integrity issue

## Instructions for Claude Agent
1. **Start Command**: 
   ```
   You are "agent-project-docs" working on GitHub issue #2.
   
   Repository: https://github.com/insult0o/tore-matrix-labs
   Issue: https://github.com/insult0o/tore-matrix-labs/issues/2
   
   Task: Fix duplicate documents appearing when reprocessing and reloading projects
   Working branch: issue-2-agent-project-docs
   ```

2. **Setup Working Branch**:
   ```bash
   git checkout -b issue-2-agent-project-docs
   ```

3. **Check Project Status**:
   ```bash
   ./scripts/project_operations.sh status
   ```

4. **Test Projects**: Use "4.tore" and "7.tore" for testing

5. **Progress Updates**: Comment on GitHub issue #2

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
git checkout issue-2-agent-project-docs
gh issue view 2 --repo insult0o/tore-matrix-labs
```