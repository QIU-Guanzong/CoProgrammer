# Cloud inspection validation

Workface: `e28bc78d56d3:/workspace/CoProgrammer`, Linux, local branch
`codex/interrupt-inspection-guide`; base
`f1f74c12df9d9fa36d7f80645cb0af71a27c42c8`.

- Six documented Manager/worker/status query help interfaces checked. The board
  has no invented JSON/session/pagination flag. Example help is runnable too.
- Final executable fixture passed with empty stderr. Actual CLI finish and ACK
  calls each returned 130/unknown after real atomic commits. The exact task was
  done, the exact message acknowledged, and read-only inspections preserved
  event-log bytes. Incrementing counters proved one invocation of each harness;
  claim, finish, release, send and ACK event counts were each one. Temporary
  fixtures were removed; no service, remote or real model was used.
- Focused runner regression: 39 tests passed, 12.981s; ResourceWarning treated
  as errors. The two added cases are runner API tests with real failed executable
  starts, covering unclaimed versus already-owned inbox handling. They do not
  claim native AI/GUI acceptance.
- Serial full unittest: 461 passed, 0 failed, 0 skipped, 67.461s. No heavy checks
  overlapped in this round; existing watch/adapter cases are included in this
  single full run rather than repeatedly counted as new coverage.
- Config and all five implemented upgrade manifests passed. JSON/YAML syntax:
  53 JSON and 10 YAML passed, including the preserved scope manifest.
- `git diff --check` and `git fsck --full` passed. Eleven prior bundle/patch/receipt
  artifacts match their recorded SHA256 values; original untracked materials
  remain untouched. Protected schemas/protocols/workflows remain unchanged.

Two agents independently reviewed the recent failure/interruption diagnostic
batches and the new inspection flow, without editing or running regression
tests. Findings addressed in this bounded batch:

- Normal inbox failure incorrectly invented claim retention when no task was
  owned. It now uses the same observed boundary fact as interruption reports;
  no Manager mutation, claim, guard or receipt behavior changed.
- A fixed invocation marker could not prove no side-effect replay. The fixture
  now increments and checks counters. Temporary Git initialization uses an empty
  template/hooks directory and disables signing per command, matching the
  existing offline demo; no global configuration changes.
- An external same-log transaction around runner calls can defer persistence.
  The guide explicitly excludes this unvalidated nesting from confirmed-result
  interpretation. No transaction policy or protocol was changed to address it.

Inspection limits are explicit: task identity must be correlated; status JSON
can truncate; message cursors follow sends and do not redisplay later ACKs on
old pages; active lease absence does not prove release. A done/ACK record does
not prove correctness, understanding or process liveness. Unknown outcomes never
trigger automatic command, finish, receipt, release or reclaim replay.

Windows native signal/cleanup and real client/model/account acceptance remain
not run. WorkBuddy GUI remains deferred. No push, PR, merge, release, deployment,
GitHub 403 retry, Library retry, Air action or other project data access occurred.
Only local commits and private artifacts carry the new change.

Next suggestions, ordered by user benefit:

1. Add safe task/window correlation to interruption diagnostics and a focused
   read-only task-detail view, so users can identify the original outcome without
   searching a large board. Do not expose claim tokens or add recovery actions.
2. Extend Codex first-use diagnostics to trusted executable/version/flag
   compatibility, keeping account/model access clearly unverified and avoiding
   model calls. This would make installed-but-incompatible clients easier to fix.
3. Run existing interruption/process fixtures in an authorized cloud Windows
   environment to validate native cleanup and exit behavior. Keep real models
   and GUI testing out of that acceptance; no workflow/public write is implied.
