# CLI preview and rejection audit — 2026-10-26

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Base: `9ae45d110874e2569428b3f34c11a98a07abc0b3`.

The contract follows worker run/watch preview help, start --dry-run and status
documentation. Snapshots compare Manager event bytes and project files, while
allowing Git inspection and runtime locking. They do not impose an absolute
no-filesystem-activity requirement on applied failure paths.

Six new methods cover: closed recipients on run/watch preview and apply; 24 static
invalid-input combinations (missing command, invalid timeout, duplicate/invalid/
unknown recipient and unknown session); six read-only/setup-preview/invalid-resume
cases; legitimate completion to a blocked peer; and explicit unavailable-command
retry retaining one original claim. No finish/ACK restart scenarios were added.

Baseline: 6 methods, 4 failing closed-target subcases, zero errors, 2.830s.
Both applied closed-target cases actually launched the synthetic marker command
before completion rejected the recipient. The other methods already passed.
The one-line fix reuses co._session, which co.send already uses: it rejects a
closed target but permits blocked/idle/stale sessions. Existing unknown-recipient
and self-recipient diagnostics are retained.

- Focused: 6 passed, 1.493s.
- Related runner/worker/onboarding suites: 60 passed, 11.568s.
- Serial full suite, ResourceWarning as error: 595 passed, 78.588s.
- Config, manifest and whitespace validation: passed.
- Installed and independent immutable verification are recorded in the handoff.

This is preflight against the observed state, not a reservation of recipient
availability. A target can close during command execution; completion still
validates it and an already executed side effect cannot be undone. No automatic
retry, implicit ACK, stricter freshness policy or watch exit-code change.
No GitHub action or model invocation occurred in this batch. Historical remote
evidence retains its original timestamp. Windows native behavior, external
consumers and earlier filesystem race limits remain unverified or unchanged.
