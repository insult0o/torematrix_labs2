# Claude Agent Assignment: agent-ui-areas

## Assigned Issue
- **Issue #**: 3
- **Title**: bug_cut_areas_not_displayed
- **Assigned At**: 2025-07-11 23:23:45
- **Status**: Active

## Problem Description
Fix areas not displaying in document preview - areas that were cut/selected are not showing in the preview

## Expected Files to Modify
- `tore_matrix_labs/ui/components/manual_validation_widget.py`
- `tore_matrix_labs/ui/components/pdf_viewer.py`
- `tore_matrix_labs/core/area_storage_manager.py`
- `tore_matrix_labs/ui/highlighting/highlighting_engine.py`

## Priority Level
High - Critical UI functionality

## Instructions for Claude Agent
1. **Start Command**: 
   ```
   You are "agent-ui-areas" working on GitHub issue #3.
   
   Repository: https://github.com/insult0o/tore-matrix-labs
   Issue: https://github.com/insult0o/tore-matrix-labs/issues/3
   
   Task: Fix areas not displaying in document preview - areas that were cut/selected are not showing in the preview
   Working branch: issue-3-agent-ui-areas
   ```

2. **Setup Working Branch**:
   ```bash
   git checkout -b issue-3-agent-ui-areas
   ```

3. **Check Project Status**:
   ```bash
   ./scripts/project_operations.sh status
   ```

4. **Test Projects**: Use "4.tore" and "7.tore" for testing

5. **Progress Updates**: Comment on GitHub issue #3

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
git checkout issue-3-agent-ui-areas
gh issue view 3 --repo insult0o/tore-matrix-labs
```