# Watch interruption validation — 2026-10-26

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Base: `90862a325d36acca0ab16a4b20b29c70837d3169`.

Six final focused tests against the base: five failures, zero errors, 1.060s.
The initial baseline had two failures and three missing-field KeyErrors; the
assertions were changed to compare missing values explicitly, then the same
runtime defect was reproduced before editing watcher.py.

- Focused: 6 passed, 1.365s.
- Related foreground/runner/interruption/diagnostic suites: 70 passed, 24.355s.
- Serial full unittest, ResourceWarning as error: 583 passed, 67.649s.
- Offline wheel build and isolated install: passed. Runtime and bundled guide
  bytes match source; installed focused verification is recorded in the handoff.
- Config and change manifest validate; canonical and packaged guides match.

Fault injection covers interrupted finish before and after actual commit, plus
ACK after commit. Unknown outcomes remain unknown; durable events are inspected
only by the tests, and the interrupted action is attempted once. Watch counters
remain unchanged. A separate test preserves unknown launch/cleanup values and
another preserves plain idle-wait interruption behavior. A real CLI child marker
precedes SIGINT, confirming launch before cancellation; the final summary retains
cleanup and claim observations. Historical watch exit code 0 remains intentional;
automation must inspect the summary reason.

No runner, Manager mutation, schema or protocol change. No model, account,
permission, public write, CI or service operation. Windows native SIGINT behavior
is unverified. The prior filesystem race limitations and frozen packages remain.
Independent review is recorded against the frozen commit separately; no remote
merge, maintainer approval or package release is claimed here.
