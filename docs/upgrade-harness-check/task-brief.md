# Codex harness first-use check

This slice starts only after private cloud import and independent acceptance of
`ae4a9164967c3c91a7c3983c8b680f5658e03c34` (parent
`e963b72438a2e9f9fe859eb4e14b61f01460383e`, parent baseline
`d9e55083b506013f2c38380cb0d3f35a61e92a37`). All 26 received Git objects passed
SHA verification; fsck and target cloud's 14 adapter tests/config/manifest passed.
Original untracked scope materials and baseline/pause evidence remain intact.

Problem: the task adapter requires an explicitly applied worker invocation to
discover that its native executable is missing. Native diagnostics are discarded
by design, so first-use guidance should provide an earlier standalone check.

Add `python -m coprogrammer.codex_harness --check`, retaining `--executable` and
the current sandbox options. It reports executable discovery only, plus task-only
and inbox boundaries and the next action. It must not assert version, client
configuration or model readiness. Add installed-environment and message-receipt
troubleshooting to the existing adapter guide.

Acceptance, defined before implementation:

- Explicit executable paths and PATH lookup return `available`/exit 0 with an
  absolute discovered path; missing, directory or nonexecutable paths return
  `unavailable`/exit 1.
- Check mode requires no task packet and never reads stdin, launches a native
  process, calls Git/Manager, creates temporary state or reads accounts/config.
- `--check` and `--execute` are mutually exclusive. Execution still requires
  explicit `--execute`; its 14 existing tests continue to pass.
- Results state task-only support, inbox refusal and unverified native version,
  configuration and model connection. Client labels do not select providers.
- Focused checks run before serial full unittest, config/manifest and JSON/YAML
  validation. Verify the check from an independently installed local package
  if the existing offline build tools permit it.

Allowed paths: `src/coprogrammer/codex_harness.py`, a focused test file,
`docs/CODEX_TASK_HARNESS.md`, and this artifact directory. Do not modify runner,
worker, watcher, schemas, protocols, workflows, package metadata, dependencies,
OpenClaw profile validation, accounts or approval rules. Use offline fixtures
only; no paid model calls, GUI testing, global services or public writes.
