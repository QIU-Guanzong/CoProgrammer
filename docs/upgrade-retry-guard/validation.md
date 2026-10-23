# Retry content guard validation

Validated in the existing cloud Linux checkout on 2026-10-23, based on
`cfa7ffd93a3367cf6f22bb90f9f8554943638d13`.

- Focused `test_retry_guard.py`: 17 tests passed in 5.545 seconds.
- Serial full suite with `-W error::ResourceWarning`: 527 tests passed in
  60.152 seconds. These are this candidate's results, not historical counts.
- Configuration and change-manifest validation passed.
- Syntax validation: 59 JSON and 10 YAML files passed.
- Bundled foreground guide is byte-identical to its source guide.
- AST comparison confirms that extraction of the existing invocation body into
  `_invoke` preserves that body; the guard wraps it under the existing lock.
- Six original private replay evidence files retain their recorded SHA-256
  hashes. No original model task was replayed or inspected for new causes.

The focused suite uses synthetic temporary Git repositories and actual offline
Python subprocesses. It covers unchanged retries, external content modification,
addition/deletion, content-preserving commits, missing/invalid records, failed
start/end record writes, end observation failure, expired claims, previews,
CLI wiring, default behavior, duplicate completion/notification and SIGINT
cleanup. The SIGINT process test is POSIX-only; Windows execution was not run.
No real AI client/model or account is used by these tests.

Compatibility is explicit: protection is opt-in on `worker run`, must begin with
newly claimed work, and must be requested for each attempt. The default, watcher,
inbox receipt rules and protected protocol/schema paths are unchanged. Existing
claims without a protected baseline cannot acquire one by retrying. Interrupted
attempts retain an incomplete marker rather than assuming a safe end state.

The digest observes the whole tracked/nonignored worktree, so unrelated edits
can conservatively block a retry. It cannot cover ignored/external inputs,
identify the writer of changes during a run, lock concurrent editors, or prove
the authenticity of edited local state. Successful task completion is not
rolled back if subsequent observation or record persistence fails; inspect the
existing task/report before deciding what to do next.

At this validation checkpoint no public push, PR, CI trigger, model call or
package publication had been performed. A later publication receipt is separate
from these local test results.
Test-owned subprocesses and temporary fixtures were cleaned up; no persistent
service was started. Local logs and the candidate patch are retained under
`work/retry-guard-20261023/` for private review.
