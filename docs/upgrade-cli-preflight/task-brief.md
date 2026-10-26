# Audit CLI rejection and preview boundaries

Base: 9ae45d110874e2569428b3f34c11a98a07abc0b3.

Contract: worker run/watch without --apply previews, never claims or launches the
trusted command. Start --dry-run previews registration/setup. Status is read-only.
Invalid static requests should reject before a claim or harness invocation.
Git inspection subprocesses and existing runtime locking are allowed; no blanket
promise of zero filesystem activity is introduced. An unavailable executable
detected on an applied launch may legitimately leave a claim for inspection.

Audit missing command/target, invalid timeout/recipient, status/setup dry-run and
resume rejection with synthetic project bytes and event-log snapshots. Do not
repeat finish/ACK recovery tests. Suspected gap: a closed notification target is
known to be invalid before execution, but runner only checks registry membership;
co.send rejects it after harness completion. If reproduced, reuse the same session
validator in preflight without rejecting blocked/idle/stale peers unnecessarily.

Allowed files: runner.py, test_cli_preflight.py, foreground guide and bundled copy,
this brief/manifest/validation. Protected paths, schemas/protocols, public writes,
model/accounts/services, and earlier immutable artifacts are excluded.
Acceptance: red/green closed-target cases, coverage of valid read-only/explicit
failure semantics, related and full serial tests, installed and independent review.
