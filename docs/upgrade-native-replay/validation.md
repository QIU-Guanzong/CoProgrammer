# Native replay and fixed execution evidence

Base: `fe07655f67a30803aa50394a685016572e2e0a05`, the private source
tree matching the unmerged PR #11 review candidate. This increment is separate
from that prior 496-test acceptance and does not merge or release it.

## This round

The restored cloud workface was checked against main and PR #11. The original
non-sensitive Markdown fixture, claim history and earlier immutable receipts
were retained. After confirming the old worker stopped, clean files and an
expired lease, the original creator explicitly reclaimed its task under the
new replay authorization. Old events remain an unchanged byte prefix.

Exactly one bounded replay was submitted through the installed candidate and
existing worker. Transparent instrumentation observed the real native process
start and exit code 1, with unchanged native argv and process-group behavior.
No valid completion was accepted. Model startup remains unknown; the failure
was not attributed to network, permissions or account state without evidence.
The replacement failed claim and edits are retained. No automatic retry or ACK
occurred. Claude/GLM/DeepSeek model readiness remains blocked without available
project authorization; no login, OAuth/API key or provider route was created.

## Confirmed independent fixes

Temporary result-storage setup/cleanup I/O could escape as raw OSError, while
a missing final result was conflated with executable unavailability. These now
produce separate fixed diagnostics. An optional new private execution receipt
records stages and observed exits without altering task/result transport.
The existing file is never overwritten, and check mode cannot create one.
An OSError around subprocess.run leaves native startup unknown; only a returned
native exit establishes startup. No model-start assertion follows from either.

- Codex focused: 21 passed, including seven new regression cases, 6.541s.
- Check-mode focused: four passed, 0.024s.
- Serial full regression after runtime changes: 503 passed, zero failures/skips,
  65.523s, with ResourceWarning promoted to error.
- Actual installed candidate with three synthetic native processes: nonzero
  exit 17, missing result after exit 0, and valid completion all produced the
  expected claim/result behavior and exact correlated private metadata.
  These cases used zero model requests; preview created no diagnostic file.
- Installed resources: 16; canonical Codex guide matches its bundled bytes.
- Wheel/sdist: all 51 source package payloads match.
- Config, 20 upgrade manifests, 57 JSON and 10 YAML documents validated;
  git diff checks passed. Thirteen prior recorded deliverables retained hashes.

These checks do not establish real model collaboration. The current real-native
task failed, while the passing task cases are explicitly offline fixtures.
Detailed environment, account-status and claim receipts stay private.

At this validation checkpoint, the increment was committed only locally; no
remote branch, commit or draft PR for it had been created or verified. Publication
permission was pending at that time. A subsequent 2026-10-23 review authorized
preparing the accumulated diagnostic and retry changes as a separate draft PR
based on PR #11's branch. Publication success must be established by its actual
remote commit and PR receipt, not inferred from this historical validation.
Main, PR #11, protected schemas/protocols/workflows, native permissions, accounts,
provider configuration, package version and repository visibility are preserved.
