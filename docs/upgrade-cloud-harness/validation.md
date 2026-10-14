# Cloud validation — 2026-10-13

- Baseline: d9e55083b506013f2c38380cb0d3f35a61e92a37.
- Initial config validate and CLI help: passed.
- Initial focused runner tests: 16 passed.
- New focused Codex adapter tests: 4 passed (fake CLI, no model calls).
- PYTHONPATH=src python -m unittest discover -s tests: 424 passed, 38.881s.
- PYTHONPATH=src python -m coprogrammer config validate: config ok.
- Manifest validation: manifest ok.
- git diff --check: passed.
- Native model validation: blocked; Codex/Claude/OpenClaw CLI absent from PATH.
- Direct Git transport: network policy blocked github.com:443. GitHub connector
  successfully read main, open PRs, source blobs and raw Git metadata.
- All 262 baseline blobs, all trees and original signed commit reconstructed
  and independently SHA-1 verified. Checkout is shallow at the stated baseline.
- GitHub CI/release for this new branch: not yet claimed or verified.
- No development services or watchers started. No local host actions performed.

## Targeted cloud review — 2026-10-13

Remote read via GitHub connector at 2026-10-13T12:13:57Z (20:13:57 Asia/Shanghai):
main remained d9e55083b506013f2c38380cb0d3f35a61e92a37; open PR list empty.
The checkout and branch were reused; no additional environment was created.

Found and fixed: empty/malformed task dictionaries could reach native execution.
The adapter now validates claimed task identifiers, title, normalized nonempty
patterns, summary and status before launch, and matches packet workspace to the
actual worktree. This reuses existing validation rules and does not establish a
new authorization boundary or authenticate arbitrary external packets.
Duplicate JSON fields and nonfinite numeric constants now fail closed for input
and final output. Native argv retains ephemeral structured output and read-only
by default; nonzero exit ignores even a plausible final result. Empty, invalid,
extra-field and oversized final output cannot complete a task.

POSIX fixtures explicitly have a platform guard: Windows lacks executable
shebang semantics. Added platform-neutral argv/result subprocess simulations
with no shell or executable permission changes. Linux execution is not Windows
CI acceptance. SIGINT and timeout tests run the actual parent runner, adapter,
fake native CLI and its sleeping child, and verify both fixture descendants
stop without task completion. The existing runner process-group cleanup is
retained; no production process policy or approval setting was changed.

Next task belongs exclusively to the designated receiving cloud workspace:
validate installed native Codex/version/account; Claude remains a later route. Codex/Claude/OpenClaw
CLI absent from PATH; real-model and Windows CI validation remain blocked/not
run. The network policy and GitHub write 403 are retained. Latest coordination forbids public push/PR/merge/release. Export only new Git
objects for private cloud-to-cloud import into /workspace/CoProgrammer on the
designated durable host e28bc78d56d3. This relay starts no subsequent feature.

Final verification after fixes (cloud Linux only):
- Focused adapter suite: 14 tests passed, 0 failed, 0 skipped, 4.716s.
- Full suite: 434 tests passed, 0 failed, 0 skipped, 41.311s.
- Config validation: config ok; manifest validation: manifest ok.
- git diff --check: passed.
- Windows native CI: not run. Platform-neutral simulations ran on Linux;
  POSIX shebang/process tests will be explicitly skipped on Windows.
- Real Codex/Claude/OpenClaw model calls: not run, native CLI absent.
- Public GitHub push/PR/merge/release: prohibited by final coordination boundary.
