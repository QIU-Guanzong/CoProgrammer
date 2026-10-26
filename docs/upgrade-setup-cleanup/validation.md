# Cleanup failure after cancellation

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Base: `c67b580842a7d38d6538ee7fc6233f9b82316b1b`. Cloud Linux, 2026-10-25.
The base commit and its Library package remain unchanged.

Three regressions were executed before modifying runtime code: direct creation
and upgrade calls produced RuntimeError instead of the original KeyboardInterrupt
(two test errors), and a real synthetic CLI subprocess receiving SIGINT exited
with code 2 instead of interruption semantics (one test failure). Duration 0.164s.
The old error chain retained the interrupt internally, but CLI handling reduced
the user-facing failure to its generic setup-write diagnostic. A staging file
remained after the injected cleanup error; it was not silently removed.

The two staged-write helpers now retain the original KeyboardInterrupt object
and re-raise it with the cleanup OSError as explicit cause. Cleanup is attempted
once; failed cleanup artifacts remain inspectable. The application interruption
recovery branch is reached, preserves user edits, checks the receipt as before,
and re-raises the interruption. Ordinary cleanup errors and another Ctrl+C
retain their existing failure semantics. No global signal handler was added.

Six focused tests passed in 0.140s, including the three formerly failing cases,
ordinary cleanup failure, a second interrupt, and concurrent user edits.
All 52 setup tests passed in 0.826s. Serial full unittest with ResourceWarning
treated as an error passed 558 tests in 58.003s: six new beyond the frozen
552-test candidate. Configuration and manifest validate; 64 JSON and 10 YAML
files parse. Eleven prior evidence hashes and the exact c67 Library ZIP hash
remain unchanged. Protected paths are unchanged.

An offline wheel was built and installed into the task work directory without
index/dependency access or global installation. From outside the checkout, its
setup bytes matched source and the six focused tests passed. This is an unreleased
local candidate, not a new published package/version. Exact timing and wheel hash
are retained with the local verification receipt.

## Publication bookkeeping assessment

The publication-to-recording window remains. Two in-memory counterexperiments
tested moving recording before publication, without changing production source:

- Pre-appending an update completion let rollback overwrite an independent
  same-content replacement made before our publication. Current ordering kept it.
- Pre-registering a new file's identity let rollback remove a competing hard
  link created before our link failed. Current ordering kept it.

Thus optimistic ownership is not a safe local fix. Recording inside a helper
could shorten the caller-return interval but still leaves the interval between
the filesystem operation and Python bookkeeping. No timing-based guarantee is
claimed and no ownership or rollback rule was broadened. Unconfirmed publication
must still be inspected. A stronger recovery mechanism would require a separate
design and acceptance scope; it is not included here.

Known limits: Windows native SIGINT untested; SIGKILL/crash/second interrupt and
arbitrary external races are not guaranteed recoverable. Cleanup failure leaves
artifacts deliberately, with no deletion retry. Existing hard-link requirement
and multi-file non-atomicity remain. No models/accounts, GitHub write, CI, merge,
global process management or old evidence modification occurred.

## Follow-up: retain the earlier visible exception chain

Independent review of immutable `59aba3f775b217bc872aa1e4e2469f22e385f0fa`
passed 17 checks and found that attaching the cleanup error could hide an earlier
custom cause of the interruption. A new regression failed in four creation/update
subcases before the follow-up fix. Cleanup now links to the interruption's earlier
visible cause or context before becoming its explicit cause. The same original
KeyboardInterrupt remains primary. Explicit `raise ... from None` is respected:
two further baseline failures demonstrated why suppressed context must remain
suppressed. This does not promise preservation of arbitrary manually constructed
exception graphs.

Final source passed all 53 setup tests in 0.906s and serial full unittest with
ResourceWarning treated as an error: 559 tests in 57.970s. An offline wheel built
from this source was installed into a separate task directory; its setup module
bytes matched source and seven focused tests passed in 0.189s from outside the
checkout. Config and manifest validation and diff whitespace checks passed.
The earlier candidate, review and wheel evidence are preserved separately;
the follow-up receives its own immutable commit and independent review receipt.
