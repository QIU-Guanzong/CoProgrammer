# v0.3.0a2 integration review

Baseline: latest main 9ce280073ab01d9c5233f028364aa77faf9a8cdc. Preserve current
claims, leases, messages, event formats, provider reviews and preview-first setup.
Rebuild only additive start/status entry points and read-only MCP status.

- Startup serializes existing registration/pulse operations. Dry-run and status
  create no initial runtime directory. Resume is explicit and refuses mismatched,
  blocked/closed sessions or a branch differing from an active claim.
- Client files remain a preview. No agent process, token/message export or global
  settings are added. Status uses actual client/worktree eligibility and never ACKs.
- Decode Git metadata as UTF-8; real non-ASCII worktree/branch regressions cover
  the new entry points along with legacy-encoding terminal output.
- Display positioning: CoProgrammer — Teamwork for coding agents. README starts
  with a concrete problem, actual demo excerpt, install/use steps and help routes.
- GitHub About/topics and the disabled Discussions entry were aligned with the
  user's discoverability request. No outreach, fabricated usage or star claim.
- Protected changes: CLI and package metadata. No event/schema/auth/migration
  change, new runtime dependency or Manager transport. Existing upgrade/merge
  authorization applies after the final source/wheel and CI checks pass.
- Rollback: revert the PR and pin 0.3.0a1. No migration is needed.

The generated inventory below is a review drafting aid; its TODOs are not approvals.

# Branch Digest

Generated: `2026-10-12T07:01:52+00:00`

Base: `origin/main`
Head: `HEAD`

## Branch Intent

TODO: Describe the problem this branch is trying to solve.

## Core Contribution

TODO: List the useful ideas, experiments, and implementation decisions worth preserving.

## Changed Files

- `M` `CONTRIBUTING.md`
- `M` `README.md`
- `M` `README.zh-CN.md`
- `A` `docs/GETTING_STARTED.md`
- `M` `docs/PLUGIN_QUICKSTART.md`
- `A` `docs/research/onboarding-2026-10-12.md`
- `M` `plugins/coprogrammer/.claude-plugin/plugin.json`
- `M` `plugins/coprogrammer/.codex-plugin/plugin.json`
- `M` `plugins/coprogrammer/plugin.json`
- `M` `plugins/coprogrammer/skills/coprogrammer-active-sync/SKILL.md`
- `M` `pyproject.toml`
- `M` `src/coprogrammer/__init__.py`
- `M` `src/coprogrammer/assets/skills/coprogrammer-active-sync/SKILL.md`
- `M` `src/coprogrammer/cli.py`
- `M` `src/coprogrammer/mcp_server.py`
- `A` `src/coprogrammer/onboarding.py`
- `M` `src/coprogrammer/workflow_mcp.py`
- `A` `tests/test_onboarding.py`

## Commit Summary

- 6228c48 docs: explain agent teamwork with a reproducible first-use workflow
- 2b0200c feat: add guided window startup and session-aware status for v0.3.0a2

## Contract and Architecture Signals

- **build**
  - `pyproject.toml`

## Risk Level

`medium`

## Protected Path Matches

- `pyproject.toml` matches `pyproject.toml` [medium] (package and entrypoint configuration; owner review required)
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
