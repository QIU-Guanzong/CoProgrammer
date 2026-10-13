# Task brief

After a6 repair, validation, merge and publication, the user explicitly requested
more automated multi-window task scheduling and internal message synchronization
with easier first use. Reuse the current checkout and verified package environment.

Add an explicit project-install option to `start`, preserving preview/default
behavior and blocking session registration on setup conflicts. Add a bounded
foreground `worker watch` over existing run/step/finish/receipt boundaries, with
optional idle waiting, compact progress, one watcher per worktree and no retries
after failures, unhandled messages or decisions. Retain original claims/edits.

The public a6 smoke discovered that the default OpenClaw executable now routes
to a managed service and ignores local profile environment variables. Keep that
service untouched. Add explicit native executable selection and verify profile
binding before discovery; local native 2026.6.8 and the managed 2026.10.2 launcher
must be reported separately. No account/model/production configuration changes.

Allowed: onboarding, watcher/worker CLI, native verification/CLI, bundled project
setup Skill and equivalent package asset, tests, docs/README and version metadata.
Excluded: schemas, protocols, workflows, dependencies, silent model/provider calls,
global settings, daemons, automatic ACKs/lease takeover, Git commits/merges by the
product, WorkBuddy GUI and unrelated cleanup. This development task may follow
the existing authorized release flow after checks.

Validate real worktree dependency/message flows, no-launch preview, explicit
receipt handling, scope/failure/cancellation/timeout/duplicate-watcher behavior,
conflict-safe startup, native isolation, source/wheel/platform CI and published
readback. Retain receipts and current/rollback packages; retire only precisely
identified, reconstructible task artifacts after process/reference checks.
