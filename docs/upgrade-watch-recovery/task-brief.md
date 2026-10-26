# Verify consumers after uncertain watch outcomes

Base: 7735ac3c7a84f496ed7ca8dd5a73e70290df0190.

Trace: worker_cli emits watch reports; status/briefing and dispatch reconstruct
Manager events, not process exit or watch counters. Worker step selects queued
or owned claimed tasks; inbox selection excludes acknowledged messages. Verify
these actual paths using finish/ACK interruption before and after commit, read-only
CLI inspection, explicit session resume and repeated watch startup.

Adjacent suspected request-validation gap: runner prechecks unknown recipients
but not its own session, while worker.finish forbids self notifications. An invalid
--notify may therefore fail only after a side-effecting harness executes. Prove
this with synthetic commands, then move that existing rejection before preview,
claim and launch. Do not change valid notification semantics or watch exit codes.

Allowed: runner.py, test_watch_recovery.py, foreground guide and packaged copy,
this task's documents. No protocol/schema, automatic retry/ACK, durable-state
inference, model, account, service, protected path or public write change.
Acceptance: consumer coverage, failed-before/passed-after request tests, related
runner/worker/watch regression, serial full suite, installed verification and
independent review. Keep all earlier frozen packages and integration identities.
