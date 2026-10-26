# Ambiguous recovery validation — 2026-10-26

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Base d97d06bbf8fee5e029950426a215b38bc67221fb; original cloud checkout reused.
Tracked files were clean; existing untracked material was retained; no active
Manager lease, decision or contract change was present. After environment startup,
the first shell request briefly reported no usable executor; the same environment
then executed normally. No alternate host, identity or account was used.

Six new methods cover thirteen synthetic scenarios. Before runtime changes,
eleven scenarios failed: after receipt publication returned an error, recovery
removed/restored files under the newly published receipt; unknown receipt state
did not preserve output for ordinary errors; a relinked target with a surviving
alias could be removed or replaced during recovery. The ordinary unchanged-
receipt rollback scenarios passed already.

The receipt consistency check now applies to OSError/RuntimeError as well as
KeyboardInterrupt. Unverified/changed receipt state retains files and reports
that retention, chaining the original error; it never claims successful rollback.
Recovery additionally requires a regular file, matching staged identity and
observed link count exactly one. New-file unlink and staged update restoration
recheck this condition immediately before mutation. No success is inferred from
an unconfirmed publishing primitive, and no signal mask or journal was added.

Two prior test expectations were intentionally updated, with stronger state
assertions: a foreign receipt retains its matching generated files; a staging
unlink failure retains both observed aliases with matching bytes and inode.
These are explicit conservative compatibility changes, not skipped regressions.
The new CLI fixture's post-signal lock check initially used incompatible setup
flags; it now acquires the same Manager lock without redoing installation.
Final test bytes were rerun against the previous installed d97 package, whose
setup bytes were checked against Git: eleven failures, zero errors, 0.210s.

Final source checks, ResourceWarning treated as an error:

- Six focused methods passed in 0.218s.
- All 66 setup tests passed in 1.496s.
- Serial full unittest: 572 tests passed in 64.044s.
- Offline wheel built/installed without index/dependency/global writes; setup
  bytes matched source and six installed tests passed in 0.220s outside checkout.
- Actual CLI subprocess received SIGINT, preserved the relinked target/alias,
  retained interruption semantics and released its Manager lock. No AI call.
- Config, change manifest and diff whitespace checks passed.

Independent review, exact commit/tree hashes, sequential integration evidence
and artifact hashes are attached privately after freezing the candidate.

Fresh read-only GitHub metadata shows main d9e55083b506013f2c38380cb0d3f35a61e92a37,
open PR11 26d64273fcdac83441026ba1f06f66772d7a24ec, and stacked draft PR12
4cd839c31ab5b627c02fc254f3573698a18d14a7. PR11/12 trees match the existing local
equivalents. No merge retry, push, PR mutation, CI or package publication occurred;
the previous platform merge rejection remains distinct from repository metadata.

The syscall-to-record window for ordinary generated files remains unresolved
when publication cannot be confirmed; such files require inspection. A transient
alias removed before observation, or changes after the final check, cannot be
excluded. Link counts do not establish provenance or provide atomic CAS. Unknown
or non-one link counts conservatively retain files. Windows native signals and
filesystem behavior remain unverified; no compatibility success is claimed there.
Reverting this commit restores the earlier recovery behavior without migrating
receipts or changing permissions, providers, accounts or public schemas.
