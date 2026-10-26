# Cumulative integration validation — 2026-10-26

PR11 merged normally at `1d71ee1f0271378d54f6a166f7099ef5593ad63c`.
PR12 was retargeted to main and merged normally at
`95239fee0137a997faa1cfbb6aed5306f331090c`. All 19 PR12 increment paths and
blob SHAs matched the previously reviewed candidate after retargeting. Its merge
tree is `02855b6a1e03562585d6a992aaab751f0c754960`, exactly the local cumulative
base `edb13745db5496df7402bb94d7408489312c9567` tree. No override or protection
change was used. PR12's original skipped CI is not claimed as passing CI.

The cumulative runtime/tests are frozen at
`c2a6248c710d049aa3f06c47cfe013cb8c9f69cc`, tree
`492cbb7ac87eaa07cea56d659bcc64e0f8fd8817`. Publication preparation adds only
this integration record/manifest/brief and notices on historical validation
documents. Old test counts and remote states remain historical checkpoints.

Existing acceptance on the complete c2a6248 runtime/test bytes:

- Serial full suite with ResourceWarning treated as an error: 595 passed, 78.588s.
- Latest focused preflight suite: 6 passed, 1.493s; related suites: 60 passed,
  11.568s; isolated installed preflight suite: 6 passed, 1.184s.
- Earlier batches record their own validation scope and results; later setup and
  watch batches also include isolated installed verification and independent
  reviews. This cumulative review reuses those records without attributing
  missing checks to every batch.
- These counts are not added together or described as new integration test runs.

The integration review records exact code/test identity, independent cumulative
review, config/manifest and data syntax validation in its handoff receipt. Remote
Draft publication and remote blob verification are separate operations; this
document does not claim they have already occurred. No package release, real
model acceptance or production deployment is claimed.

Limits remain: retry protection does not lock external editors; ignored inputs
and writes after the final observation can remain outside protection. Setup uses
same-directory hard-link publication for new files and fails closed where it is
unsupported. It retains ambiguous publication results, changed/unreadable receipts
and foreign or shared inodes for inspection. Syscall-to-record and final-check
races cannot be excluded. No portable filesystem CAS or security sandbox is
claimed. Watch interruption preserves the existing exit code and exposes its
reason/report; consumers must inspect state instead of treating exit zero as task
completion. Receipt/finish recovery stays explicit, with no automatic retry/ACK.
Native Windows signals/filesystem semantics, external consumers and real model
collaboration remain unverified by these Linux fixture tests.
