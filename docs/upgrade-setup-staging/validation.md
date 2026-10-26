# Staging ownership validation — 2026-10-26

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Baseline: `f3055293b79dc9e2fb1f972c4873f4c06821837f`.

The final five new test methods were run before the runtime fix: five scenario
failures, zero errors (six scenarios including the two content variants).
After the fix, all five methods passed, including a real CLI subprocess SIGINT
and reacquisition of its Manager lock. This uses synthetic files, not a model.

- Focused: 5 passed, 0.159s.
- All setup tests: 71 passed, 1.659s.
- Serial full suite with ResourceWarning treated as error: 577 passed, 64.132s.
- Offline wheel build and isolated target install: passed, without dependencies
  or index access. Installed setup bytes matched source; 5 tests passed, 0.160s.
- Config and change manifest: valid. `git diff --check`: passed.

The maintained publication probe reproduced a same-inode foreign publication:
current bookkeeping retained the file, while an in-memory optimistic
preregistration variant destructively rolled it back. A separate probe reproduced
external replacement after the final rollback check being overwritten. These
are observed limits, not successful conflict protection tests. No production
source is modified by the probe, and its disposable fixtures are removed.

The fix only protects cleanup when the observed staging inode differs, or no
identity was obtained. Normal owned staging cleanup remains. Identity lookup and
unlink are not atomic; same-inode mutations and changes after the final check
remain possible. Manual recovery instructions require preserving uncertain
files and receipts before an explicit reviewed retry. No receipt schema changed;
existing legacy receipt and upgrade coverage passed in the setup suite.

Windows native behavior was not tested. No model invocation, service, public
write, merge retry or CI run occurred. Independent review is recorded separately
against the frozen candidate commit in the handoff evidence; this file does not
claim that a review, remote merge or release has occurred.
