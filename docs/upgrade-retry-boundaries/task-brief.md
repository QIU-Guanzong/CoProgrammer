# Retry guard boundary audit

Base: `edb13745db5496df7402bb94d7408489312c9567`.

Audit only ignored-file changes and observation-to-execution timing in the
existing optional retry guard. Use synthetic temporary Git repositories and
offline Python subprocesses. Preserve the published PR #11/#12 candidates and
all original local material. No remote changes, CI, native models or accounts.

Acceptance: distinguish ignored untracked content from tracked content matching
an ignore rule; verify that preview cannot authorize a later stale retry; verify
that changing content during the existing double observation stops execution;
deterministically characterize external edits after the final observation but
before child startup. Count observation calls to describe hashing costs without
claiming a benchmark or protection against arbitrary concurrent editors.

Fix only a reproducible defect within the existing contract. The published guide
explicitly excludes ignored/external inputs and writes after observation. Do not
silently broaden the snapshot to caches, runtime state or credentials, or add a
new lock/sandbox architecture to turn these limits into different guarantees.
If behavior matches the contract, commit tests and evidence only. Run focused
and serial full offline regression plus config/manifest and JSON/YAML checks.

Compatibility and rollback: a test/document-only increment does not change the
runtime hash algorithm, file limits, default behavior, event records or CLI.
It can be reverted as one local commit without changing claims or saved state.
