# Branch Digest

Generated: `2026-09-26T23:39:26+00:00`

Base: `13a0de0`
Head: `WORKING_TREE`

## Branch Intent

Coordinate cross-client tasks during development: prevent competing ownership,
keep worktree changes within the claimed scope, and exchange durable task updates.

## Core Contribution

- Dependency-aware task queue with atomic path lease acquisition.
- Claim tokens bound to window, worktree and named Git branch; explicit recovery.
- Cooperative concrete-path/working-tree guard and same-worktree exclusion.
- Bounded change waits and sent/received task discussions over CLI and MCP.
- Pending-event visibility and same-holder conflict reporting fixes.

## Changed Files

- `M` `README.md`
- `M` `plugins/coprogrammer/skills/coprogrammer-active-sync/SKILL.md`
- `M` `schemas/manager-event.schema.json`
- `M` `src/coprogrammer/cli.py`
- `M` `src/coprogrammer/collaboration.py`
- `M` `src/coprogrammer/collaboration_cli.py`
- `M` `src/coprogrammer/collaboration_mcp.py`
- `M` `src/coprogrammer/manager_store.py`
- `M` `src/coprogrammer/mcp_server.py`
- `M` `tests/test_cli.py`
- `M` `tests/test_collaboration.py`
- `A` `docs/scheduling/README.md`
- `A` `docs/scheduling/change-manifest.json`
- `A` `docs/scheduling/research.md`
- `A` `docs/scheduling/task-brief.md`
- `A` `docs/scheduling/validation.md`
- `A` `src/coprogrammer/channels.py`
- `A` `src/coprogrammer/scheduler.py`
- `A` `src/coprogrammer/scheduler_cli.py`
- `A` `src/coprogrammer/scheduler_mcp.py`
- `A` `tests/test_channels.py`
- `A` `tests/test_scheduler.py`
- `A` `tests/test_scheduling_integration.py`

## Commit Summary

- No commits detected.

## Contract and Architecture Signals

- **contract**
  - `schemas/manager-event.schema.json`

## Risk Level

`high`

## Protected Path Matches

- `schemas/manager-event.schema.json` matches `schemas/**` [high] (machine-readable artifact contract changes; owner review required)
- `src/coprogrammer/cli.py` matches `src/coprogrammer/cli.py` [medium] (CLI behavior affects PR digest generation)

## Noise / Non-Essential Changes

No dependency upgrades or unrelated refactors. This generated digest was filled
with the increment's intent, review boundaries and validation evidence.

## Integration Plan

Review on top of the existing multi-platform preview. Preserve the task/channel
core, adapters, shared-log validation and their behavioral tests together. The
six new event types and MCP interfaces need maintainer review before integration.
No automatic merge, release, model launch or native client-message injection.

## Validation Needed

- [x] Source behavioral tests (228 passed)
- [x] Seven independent MCP process scheduling scenarios
- [x] Configuration and manifest checks
- [x] Installed-wheel suite (228 passed) and artifact validation (see validation.md)
- Remote CI: consult PR #1 Checks for the pushed head
- [ ] Owner review for protected areas

## Human Decisions

Maintainers review the additive event contract and cooperative enforcement
boundaries. Task completion, message receipt and test results never substitute
for code approval. Native wakeup, process control and remote scheduling remain
future scope.
