# CLAUDE Agent Factory – TORE Matrix Labs

## Purpose

This file defines the multi-agent development workflow for TORE Matrix Labs using Claude Code agents. It enforces branch isolation, structured planning, and safe PR integration.

## Roles

| Agent     | Responsibility                                     |
| --------- | -------------------------------------------------- |
| Planner   | Analyzes main issue, creates sub-issues + branches |
| Architect | Writes specs and structure for each agent task     |
| Agent N   | Implements code for one specific sub-issue         |
| Validator | Verifies work, writes final report, merges PRs     |

## Branch Rules

* Each agent must work in a separate `feature/*` branch.
* Branches are linked to specific issues/sub-issues.
* No direct work is allowed in `main`, `dev`, or shared branches.

## Workflow Summary

1. Planner reads main GitHub issue.
2. Planner creates as many sub-issues as needed with clear scope.
3. Each Agent gets 1 sub-issue + isolated branch.
4. Work proceeds independently always making sure and being aware of other agents working at the same times in the same or other branches, so always make sure working and work is safe
5. Validator confirms all PRs:

   * Merges cleanly
   * Passes CI
   * Matches specification
   * Logs final result in `VALIDATION_LOG.md`

## File Reference

* `BRANCH_MAP.md` → Branch ↔ Issue ↔ Agent reference
* `STATUS_BOARD.md` → Live agent status
* `VALIDATION_LOG.md` → Final merge and test record
