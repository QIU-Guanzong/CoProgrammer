# Recovery consumers and request preflight — 2026-10-26

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Baseline: `7735ac3c7a84f496ed7ca8dd5a73e70290df0190`.

Consumer trace: worker_cli emits the watch summary; onboarding.overview and
briefing.build_briefing rebuild counts from Manager events; workflow.dispatch
excludes tasks not queued; worker.step resumes owned claims or chooses eligible
work; co.inbox excludes acknowledged messages by default. None of these paths
uses watch exit status or unknown observations as durable completion. The existing
docs/examples/interrupt_inspection.py also queries durable state before any replay.
This trace makes no claim about external scripts consuming CLI output.

Four new deterministic CLI scenarios interrupt finish and ACK before/after the
real Manager commit. Status and step queries preserve event-log bytes. Explicit
session resume does not invoke a harness. Three subsequent explicit watch startups
never rerun committed work/receipts; uncommitted work is executed once more by the
first new explicit invocation, preserving the original task claim. Each scenario
ends with exactly one durable finish/ACK. No consumer correction was needed.

Adjacent defect: self-notification passed preview; an applied run executed the
synthetic counter command before worker.finish rejected its recipient. Final
baseline: six methods, four failing subcases across the two request tests, zero
errors, 3.195s. The four recovery-consumer methods already passed on the baseline.
Two production lines now reject the same invalid recipient at runner preflight.

- Focused: 6 methods passed, 2.827s (four recovery scenarios and four request cases).
- Related runner/worker/foreground/interruption suites: 77 passed, 22.105s.
- Serial full suite with ResourceWarning as error: 589 passed, 72.161s.
- Config and change manifest validate; diff whitespace check passes.
- Installed verification and independent immutable review are recorded separately
  in the handoff; this document does not claim a remote merge or release.

Valid peer notification, watch exit status 0, claim ownership, interrupted unknown
states and explicit-retry semantics remain unchanged. No schemas/protocols,
automatic retry/ACK, model calls, accounts, services, permissions or public writes
changed. Windows native execution is unverified. Prior concurrency boundaries and
all frozen packages remain unchanged.
