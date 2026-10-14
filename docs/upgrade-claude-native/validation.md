# Claude native adapter validation

Base: `19040bc10a7f8de565cf65e6110ed37ea0ece2d3`.
This record covers the task-only adapter before the later optional readiness
probe. Original environment/authorization receipts remain private.

- Claude focused suite: 13 tests passed on Linux (nine portable, four POSIX).
- Knowledge focused suite: six tests passed; canonical/bundled guides match.
- Full regression: 487 tests passed, zero failures/skips, with ResourceWarning
  promoted to error. Focused and full suites ran serially.
- Config and all 18 upgrade manifests passed; 55 JSON and 10 YAML files parsed.
  `git diff --check` and `git fsck --full` passed.
- Wheel and sdist match all 51 source package payloads. A clean installed venv
  read all 16 resources and the exact new guide through generated stdio MCP.
- Two independent Git worktrees completed synthetic dependency tasks and two
  explicit message receipts. Unread inbox stopped the recipient worker; only
  its exact-ID ACK permitted the next task. Code moved by explicit fixture copy,
  not by a message. Original config remained intact and final leases were empty.
- Actual synthetic process timeout/SIGINT cases preserved claims and partial
  edits, stopped owned descendants and did not mark a failed task complete.

All fixtures used zero model requests. Native installation/version/help probes
are distinct from model task acceptance. No successful real model collaboration
was established by this increment. Windows native CI, enterprise managed MCP
and WorkBuddy GUI remain unverified.

Existing Codex, runner, watcher, worker, setup and runtime verification modules
were byte-identical to base at this increment. Schemas, protocols, workflows,
Skills and package version configuration were untouched. Forty-six earlier
private evidence files retained their SHA-256 hashes.

[Installed Claude commands](../CLAUDE_TASK_HARNESS.md) cover discovery, explicit
execution, failure inspection and recipient ACKs. Native task invocation remains
opt-in. Built-in tool selection is not an OS sandbox; native permissions apply.
No automatic ACK, coordinator retry, lease takeover, account/provider setup,
approval, merge or package release was added.
