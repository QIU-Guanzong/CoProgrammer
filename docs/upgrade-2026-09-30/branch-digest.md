# Branch Digest

Generated: `2026-09-30T05:35:22+00:00`

Base: `dc49277900cfcb80a9670a0e62ec44e8bdd9dd75`
Head: `WORKING_TREE`

## Branch Intent

Make the existing source preview easier to try, resume and discover, while reducing repeated Manager state reconstruction.

## Core Contribution

- Real isolated offline demo, with verified expected refusals and cleanup.
- Bounded CLI/MCP briefing with fixed observation time and explicit next actions.
- Shared single-snapshot collaboration replay, preserving historical validation.
- Reproducible benchmark, six-project research, bilingual entrypoints and GitHub discovery metadata.

## Changed Files

- `M` `README.md`
- `M` `src/coprogrammer/cli.py`
- `M` `src/coprogrammer/collaboration.py`
- `M` `src/coprogrammer/mcp_server.py`
- `M` `src/coprogrammer/scheduler.py`
- `A` `README.zh-CN.md`
- `A` `docs/BRIEFING.md`
- `A` `docs/DEMO.md`
- `A` `docs/research/ecosystem-2026-09-30.md`
- `A` `docs/upgrade-2026-09-30/change-manifest.json`
- `A` `docs/upgrade-2026-09-30/performance.md`
- `A` `docs/upgrade-2026-09-30/task-brief.md`
- `A` `eval/benchmark_manager.py`
- `A` `src/coprogrammer/briefing.py`
- `A` `src/coprogrammer/demo.py`
- `A` `tests/test_briefing.py`
- `A` `tests/test_demo.py`
- `A` `tests/test_manager_performance.py`

## Commit Summary

- No commits detected.

## Contract and Architecture Signals

- No high-signal risk paths detected by the first-pass rules.

## Risk Level

`medium`

## Protected Path Matches

- `src/coprogrammer/cli.py` matches `src/coprogrammer/cli.py` [medium] (CLI behavior affects PR digest generation)

## Noise / Non-Essential Changes

No dependency updates, global configuration changes or unrelated formatting. Benchmark fixtures and demo repositories are temporary and excluded from commits.

## Integration Plan

This increment depends on the reviewed source-preview base above, not directly on main. Preserve existing session/task/lease contracts; add the snapshot helper before the briefing consumer, then demo and CLI/MCP registration. Review the existing full PR separately for its protected contracts and packaging. Do not automatically merge the broad branch. Roll back this increment by reverting its commit; no event-log migration is required.

## Validation Needed

- [x] 282 source tests and 282 independent installed-wheel tests.
- [x] Real Git worktrees, independent stdio MCP, failure/rollback and expiry regressions.
- [x] Config/manifest, JSON/YAML syntax, documentation links and diff whitespace.
- [ ] Remote CI on the pushed head (read back after push).
- [ ] Maintainer review of the full PR.

No formatter, static type checker or linter is configured in the existing CI; none was added for this increment.

## Human Decisions

Maintainer acceptance of the full protected PR, release/version policy, live client acceptance and any package-registry publication remain separate decisions. No approval or merge is inferred from tests or the benchmark.
