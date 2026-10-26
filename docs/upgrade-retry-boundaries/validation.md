# Ignored-file and observation timing audit

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

2026-10-24, cloud Linux; base
`edb13745db5496df7402bb94d7408489312c9567`. This increment adds five
offline tests and audit documents. Production code, published PRs and existing
private failure evidence are unchanged.

| New test | Observed behavior |
| --- | --- |
| Ignored untracked file modification/deletion/addition | The digest remains unchanged. A real synthetic child executes and overwrites/recreates the ignored file. This is excluded coverage, not a successful content guard. |
| Tracked file matching an ignore rule | The tracked content remains in the digest. A newer edit stops the retry before launch and leaves the old run record intact. |
| CLI preview followed by a newer edit | Preview writes no retry record; real CLI apply recomputes the digest, stops with `retry_content_changed`, preserves the edit and does not launch a second child. |
| Change between the two snapshot passes | The existing stable-observation check rejects it before recording a new start or launching a child; the newer edit and previous record survive. |
| External edit after checking, just before Popen | A deterministic test hook writes before calling the actual Popen. The child overwrites that edit. The runner lock does not lock out arbitrary external writers. |

The last test uses an injected interleaving rather than relying on sleep timing.
It characterizes the observation-to-launch window; it does not claim to prevent
it. The tested race and ignored-file behavior are the explicit exclusions in the
existing foreground guide. No new violation of the documented contract was
found. Making all writes atomic with checking would require a different execution
or editor-coordination design. Rechecking one more time merely moves the race.
Including arbitrary ignored caches/runtime state would change coverage, cost and
compatibility. Neither change is part of this bounded audit.

## Hash cost and compatibility

The fixture counts four calls to the existing content scanner for one normally
returning protected invocation: two observation passes before launch and two
after return. A retry with unstable content between passes stops after its two
initial passes. There is no new runtime scan or dependency in this increment.
Each pass reads the tracked/nonignored content subject to the existing 10,000
file, 8 MiB per-file and 64 MiB total limits. Cost scales with covered bytes and
file enumeration; this is a call-count observation, not a performance benchmark.

Default execution, opt-in retry semantics, hashes and persisted records remain
unchanged. Rollback is a revert of this test/document commit; no runtime migration
or claim reset is necessary. Existing receipts must still be inspected manually
before explicitly retrying failed work. Do not use ignored files for outputs that
need this content protection, or edit concurrently with a running harness.

## Validation boundary

The focused suite now contains 22 tests, including five added here, and passed in
6.491 seconds. Tests use synthetic temporary Git fixtures and Python subprocesses;
they make no real AI/client/account calls. Configuration and the new manifest
validated; 60 JSON and 10 YAML documents parsed. Six original private evidence
files retain their recorded hashes. Earlier 527-test results are historical and
are not counted as newly added tests.

Serial `PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s
tests` passed all 532 tests in 52.834 seconds on this candidate. The increase is
exactly the five boundary tests above. `git diff --check` also passed.

No remote write, PR change, merge, CI trigger, package publication or persistent
service was performed. The prior platform merge rejection was not retried.
