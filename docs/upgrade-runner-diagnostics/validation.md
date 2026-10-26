# Cloud validation — 2026-10-13

Host/workspace: `e28bc78d56d3:/workspace/CoProgrammer`, local branch
`codex/runner-failure-diagnostics`, base
`24bfe9dc1bfee431db9b95c8d4cf0b01045a3682`. Existing tools confirmed access after
a disconnection notice; the batch stayed in the same environment and checkout.

- Before implementation, five new tests reproduced the absent exit-code data
  and incorrect launch marker (expected red run: one failure, seven errors from
  cases/subcases). The original code/data was not replaced or reset.
- Runner-focused tests: 21 tests, OK, 8.522 seconds.
- Existing foreground/cancellation/watcher/lock tests: 25 tests, OK, 13.739 seconds.
- Codex harness regression: 18 tests, OK, 6.312 seconds.
- Serial full unittest discovery: 443 tests, OK, 107.137 seconds.
- Config validation: `config ok`; manifest validation: `manifest ok`.
- JSON/YAML syntax: 51 JSON and 10 YAML files passed; diff whitespace check passed.
- Independent review found no implementation blocker. The copyable preview
  command now includes the CLI prefix, and the guide clarifies that the code
  belongs to the supplied harness/wrapper rather than its deeper native client.

The new cases exercise real offline process exits, POSIX signals, missing launch,
zero-exit malformed/oversized output, timeout with partial scoped edits, retained
original claims and a later explicit successful completion. A watcher counter
proves a side-effecting failed command runs once. Native output and arbitrary
exception text are not put into diagnostics or Manager events. Existing SIGINT,
duplicate watcher/runner locks, receipt and scope tests remain unchanged.

Raw logs and resource/handoff receipts remain in `.coprogrammer/evidence/`.
Baseline had five CPUs, low load, ~17 GiB available memory and ~30 GiB free disk;
no idle self-built service or test process needed termination. Completion checks
are recorded separately after the tests. Prior receipts/bundles are preserved.

No lease, permission, approval, protocol, schema, workflow, process cleanup or
model/provider behavior changed. No paid AI, new account, WorkBuddy GUI or Windows
native CI acceptance is claimed. No service was deployed; GitHub 403 and Library
network blockers were not retried and no alternate delivery route was used.

Next suggested batch: define compatibility for a structured single-run Ctrl+C
receipt before implementing it; preserve original claim/edits and existing child
cleanup. The current batch deliberately leaves cancellation behavior intact.
