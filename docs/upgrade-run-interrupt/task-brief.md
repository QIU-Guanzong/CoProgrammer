# Single worker run interruption receipt

Base: `6b3e64c9344a3ef8c60011c2d5e84d62e708d791`. Work only on
`e28bc78d56d3:/workspace/CoProgrammer`, local branch
`codex/worker-run-interrupt-receipt`. Preserve the previous private commit chain,
bundles, receipts and untracked scope/transfer materials. No delivery retries.

Problem: a single `worker run` currently propagates Ctrl+C without a structured
receipt. The caller cannot distinguish interrupted claiming, a running child,
cleanup or a finish/ACK whose durable transaction may already have committed.

Scope, before implementation: add advisory cancellation diagnostics and a
KeyboardInterrupt subtype to the runner. Only single-run CLI catches that subtype,
emits one interrupted JSON report and exits 130; watch and Python API retain their
existing interrupt control flow. Observe launch and original exit only. Mark
claim/completion/receipt state unknown when a mutating boundary did not return.
Do not read/replay Manager state to resolve uncertainty. Briefly defer the default
main-thread SIGINT handler during Popen reference acquisition and owned-process
cleanup, restore it, then propagate interruption. Preserve custom handlers and
threaded callers; never block a signal mask inherited by children.

Acceptance:

- Pre-launch interruption launches no harness and does not invent claim facts.
  Interrupted step/finish/ACK before or after durable commit reports uncertainty;
  transactions remain atomic, and no action is replayed or release duplicated.
- Real running child and grandchild stop before the CLI emits JSON/130. Partial
  edits remain, with no finish/ACK/retry; a later explicit call can inspect the
  same claim and released runner lock.
- Launch handoff and cleanup SIGINT are deferred until the owned process can be
  cleaned; preserve the first interruption phase and restore the original handler.
- An observed exit code survives interruption in finalization. No code from a
  cleanup kill is misreported as the original outcome. No claim token, native
  output, packet body or exception text appears in the interruption receipt.
- Python callers can still catch KeyboardInterrupt, and bounded watch keeps its
  prior stopped/interrupted summary and exit behavior.
- Focused offline subprocess/transaction tests, serial full unittest, config,
  manifests, JSON/YAML, diff and Git integrity checks pass before local commit.

Allowed paths: runner, worker CLI, new focused tests, foreground guide and this
artifact directory. No schema, protocol, workflow, dependency, architecture,
security, ownership, permission or lease-policy change; no paid model calls,
account/profile changes, global service changes, Air or another checkout.

Limits: diagnostics describe observations, not code correctness. Interrupted
stdout delivery itself cannot guarantee a complete JSON document. Real Windows
signal/process acceptance and native AI calls remain untested. Only owned default
SIGINT handling gets deferred; custom handlers or directly injected exceptions
in Popen may leave launch state unknown and require inspection.
