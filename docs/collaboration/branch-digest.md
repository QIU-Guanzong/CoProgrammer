# Branch Digest

Generated: `2026-09-26T23:16:18+00:00`

Base: `3afd4a9`
Head: `WORKING_TREE`

## Branch Intent

TODO: Describe the problem this branch is trying to solve.

## Core Contribution

TODO: List the useful ideas, experiments, and implementation decisions worth preserving.

## Changed Files

- `M` `README.md`
- `M` `plugins/coprogrammer/skills/coprogrammer-active-sync/SKILL.md`
- `M` `schemas/manager-event.schema.json`
- `M` `src/coprogrammer/cli.py`
- `M` `src/coprogrammer/manager_store.py`
- `M` `src/coprogrammer/mcp_server.py`
- `A` `docs/collaboration/README.md`
- `A` `docs/collaboration/change-manifest.json`
- `A` `docs/collaboration/research.md`
- `A` `docs/collaboration/task-brief.md`
- `A` `docs/collaboration/validation.md`
- `A` `src/coprogrammer/collaboration.py`
- `A` `src/coprogrammer/collaboration_cli.py`
- `A` `src/coprogrammer/collaboration_mcp.py`
- `A` `tests/test_collaboration.py`
- `A` `tests/test_collaboration_processes.py`

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

TODO: Identify formatting churn, broad rewrites, temporary debugging, generated artifacts, or unrelated refactors.

## Integration Plan

TODO: Explain how to rebuild the smallest safe patch from latest main.

## Validation Needed

- [ ] Formatter
- [ ] Linter
- [ ] Type check
- [ ] Unit tests
- [ ] Integration tests
- [ ] Contract tests
- [ ] Owner review for protected areas

## Human Decisions

TODO: List decisions that should not be delegated to an autonomous agent.
