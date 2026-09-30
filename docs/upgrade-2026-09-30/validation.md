# Upgrade verification — 2026-09-30

Baseline: `dc49277900cfcb80a9670a0e62ec44e8bdd9dd75` on
`codex/multi-platform-upgrade`. Checks below cover the completed working tree
immediately before the upgrade commit; this record is not merge approval.

- Full source suite: **282 tests passed**, Python 3.14.7, macOS arm64.
- Fresh wheel installed in a new virtual environment outside the checkout,
  with `PYTHONPATH` removed: **282 tests passed**. Import location was the new
  environment's `site-packages`, not `src`.
- Wheel: `coprogrammer-0.2.0a1-py3-none-any.whl`; SHA-256
  `b36058c84cb4a315e9bd2dfb357af96d92a553ad7a433dca8198213486203c9d`.
  Built with `python3 -m pip wheel . --no-deps --wheel-dir dist`.
- Separate installed-wheel stdio process successfully initialized MCP and
  called `manager_briefing`; returned the expected format and empty-state guidance.
- Text and JSON demo commands passed all **11 steps**: two real linked
  worktrees, 3 completed tasks, 24 events, 0 active leases, 0 pending messages,
  and verified temporary-directory cleanup.
- New regressions cover malformed histories, complete counts with truncated
  rows, scoped inbox counts without bodies, claim-token omission, one instant
  for lease/window expiry, expected-refusal integrity and caller Git isolation.
- Existing concurrency regressions retain multiprocess lease competition,
  atomic task claims, nested transaction visibility and rollback checks.
- Config and upgrade manifest validation passed. Parsed **37 JSON / 10 YAML**
  files and resolved **58 local Markdown links** in the new/changed entrypoints
  and guides. `git diff --check` passed.
- Independent review found two briefing issues (expiry-boundary inconsistency
  and text-view omissions); both were fixed with regressions. A second review
  corrected the documented minimum to Git 2.36+.
- [Benchmark](performance.md): checked-in reproduction script, 10,002 events,
  11 alternating rounds, equal return values. Sync wall median decreased
  **26.68%**, directory wall median **48.68%** on this message-heavy fixture.

Initial local wheel attempts lacked setuptools and then hit an SSL dependency
fetch error. The isolated build succeeded after a permitted network retry;
no runtime dependencies, global packages or repository build requirements changed.

## Publication and limits

The code remains a source preview under draft PR #1. Remote checks and final
GitHub metadata are read back after pushing; their status is not inferred from
local tests. No package release, registry submission, live provider call,
native-client GUI connection, protected-branch change or merge occurred.
Topics and an accurate About/homepage can improve discovery entrypoints
([GitHub documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics));
this work does not measure or promise increased traffic.
