# Runner failure diagnostics

Base: `24bfe9dc1bfee431db9b95c8d4cf0b01045a3682`, preserving the full private
handoff chain. Use only `e28bc78d56d3:/workspace/CoProgrammer` and the new local
branch `codex/runner-failure-diagnostics`. Existing untracked scope materials,
transfer packets, immutable receipts and prior bundle remain intact.

Observed defects: the runner sets `launched=true` before `Popen` succeeds, and
discards the actual child return code. A caller cannot inspect a reported failed
start versus a launched command's nonzero exit or a zero exit with bad output.

Scope: correct the launch marker, add an advisory `exit_code` to applied runner
reports and fixed next-step guidance for existing process/reply failures. Capture
the code only after `communicate` completes, before cleanup changes the process.
Do not forward stdout/stderr, exception text or command argv into diagnostics.
Watcher uses its existing `last` report; do not alter watcher/CLI cancellation.

Acceptance, before implementation:

- Missing executables report `command_unavailable`, `launched=false`, null code,
  and retain the original claim. Preview still starts nothing and claims nothing.
- Actual nonzero exits preserve their integer code; POSIX negative signal values
  remain negative. A zero exit with malformed/oversized output reports code 0.
- Timeout reports null code rather than the cleanup kill's return code; partial
  scoped edits and the original claim remain available for explicit inspection.
- A failing watcher retains the diagnostic in `last`, executes once, stops on
  the first failure, and does not release or complete the claim.
- A later explicit successful invocation can complete that same original claim;
  no automatic retry, takeover, ACK, approval or rollback is introduced.
- Focused runner/watcher/adapter tests precede serial full unittest, config,
  manifests and JSON/YAML checks. Keep deterministic processes only.

Allowed: runner module, focused tests, foreground-worker usage guide and this
artifact directory. Forbidden: lease/ownership/receipt/permission behavior,
protocols, schemas, workflows, package metadata, dependencies, account/model
calls, global services, WorkBuddy GUI, unrelated refactors and another workspace.
GitHub 403 and Library networking remain blocked; do not retry either service.

Resource baseline: no task processes or self-built service; ~17 GiB available
memory, ~30 GiB free disk, low load. No idle service needed shutting down.
