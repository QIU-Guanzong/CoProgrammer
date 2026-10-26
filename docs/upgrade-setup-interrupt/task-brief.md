# Interrupted setup recovery

Base: `b80b52efb4056e69939937dce4414c5d08e133b8`.

Problem to reproduce: Ctrl+C after a generated file update but before receipt
publication bypasses setup's ordinary failure rollback. The next upgrade can
then conflict because the receipt still describes the previous file bytes.

Scope: setup.py, a focused synthetic interruption test module, installation
maintenance guidance, and this task's brief/manifest/validation. Use existing
staged writes, content checks and created-file ownership; no new persisted state.

Acceptance: a catchable interruption before receipt publication attempts the
existing conditional rollback and re-raises KeyboardInterrupt; explicit later
preview/apply can proceed after clean recovery. User edits and independent
replacements survive. If receipt publication occurred or its state cannot be
established, preserve files for inspection instead of rolling them back under a
potentially new receipt. A second interrupt is not swallowed. Verify a real
SIGINT in an offline subprocess as well as deterministic failure fixtures.

No automatic retry, force overwrite, model/credential calls, global signal
handler, schema/contract/workflow changes, GitHub writes or CI. Existing PRs,
untracked materials and historical evidence remain intact. SIGKILL, crashes,
arbitrary external races and Windows native signal acceptance remain outside
the guarantee. Run focused tests, then serial full unittest and config/manifest
validation; record actual results and a local immutable patch.
