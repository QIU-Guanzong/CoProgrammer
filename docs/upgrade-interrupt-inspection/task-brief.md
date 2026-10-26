# Inspect unknown interruption outcomes

Base: `f1f74c12df9d9fa36d7f80645cb0af71a27c42c8`. Use only the existing cloud
workface `/workspace/CoProgrammer`, branch `codex/interrupt-inspection-guide`.
Preserve the full private handoff chain, previous receipts/bundles and original
untracked materials. No public or Library delivery retry.

Problem: an interrupted runner can correctly report unknown durable outcomes,
but users need precise read-only commands and limits to decide what happened
without repeating a command, finish or ACK. Independent review also found the
normal inbox failure report always says claim_retained=true even with no claim.

Scope before implementation: add one inspection guide, a source-checkout offline
example using temporary synthetic Git fixtures and actual CLI subprocesses, and
a link from the foreground guide. Verify commands against --help. Correct only
the advisory inbox failure boolean using the runner's existing boundary
observation; add focused tests for a queued and an already-owned task. No new
CLI query, event, schema, permission, Manager mutation rule or recovery action.

Acceptance:

- Instructions retain original worktree/session/state-dir, correlate the exact
  task and owner, and distinguish completion/ACK state from correctness and
  process liveness. Empty active leases or default inbox do not prove an outcome.
- Status limits and message cursors are explained correctly. No --apply,
  automatic retry, repeated ACK or silently selected replacement claim.
- Executable example uses an isolated temporary Git project with no remotes,
  paid models, accounts or global config changes. A fixture injects one
  KeyboardInterrupt after actual finish/ACK commits; real CLI emits 130/unknown.
  Existing read-only queries expose done/acknowledged state while event-log bytes
  stay unchanged. Each fixture command runs once, and nothing is replayed.
- Normal inbox failures report false with no owned task and true with an
  existing owned claim; task/message/lease state is preserved.
- Independent review of the two recent diagnostic batches covers stage/exit
  observations and transaction limits. Run meaningful focused regression and
  one serial full suite, config/manifests, JSON/YAML and Git integrity checks.
- Commit locally, release only this agent's leases, verify the full handoff
  chain and preserve prior artifacts. No self-built service remains.

Known limit from review: wrapping runner.run in an external transaction on the
same Manager log can leave writes pending rather than durably committed. This
is not the validated CLI/watch invocation path; document it without changing
Manager or expanding this batch. Windows/native-model acceptance remains unrun.
