# Cloud validation

Cloud Linux only, `e28bc78d56d3:/workspace/CoProgrammer`. Base
`6b3e64c9344a3ef8c60011c2d5e84d62e708d791`, branch
`codex/worker-run-interrupt-receipt`. Previous imported and local commits,
seven immutable handoff artifacts and original untracked scope materials remain
preserved. No paid model/native client call, account/profile change or service.

- New interruption suite: 16 tests passed, including actual CLI JSON/130,
  child/grandchild shutdown, partial edit/claim preservation, cleanup entry,
  default/custom SIGINT, cleanup errors and six pre/post-commit atomic boundaries.
- Final focused runner suite: 37 passed, 11.426s, with ResourceWarning promoted
  to errors. Existing foreground suite: 25 passed, 20.168s, including watch
  SIGINT retaining its existing summary and exit 0.
- Independent focused adapter/check repeat: 18 passed, 7.489s.
- Independent full unittest: 459 passed, 0 failed, 0 skipped, 69.303s.
- Config validation and all four implemented upgrade manifests: passed.
- JSON/YAML syntax: 52 JSON and 10 YAML files passed, including preserved scope
  manifests. `git diff --check`, baseline ancestor and `git fsck --full`: passed.
- Two agents reviewed read-only without editing or running tests. Cleanup
  reference/entry and exception-path findings were fixed before final regression.

Scheduling correction: the first adapter check was mistakenly still running
when an initial full suite started. Both finished successfully, but that full
log is explicitly retained as `run-interrupt-full-overlap-not-acceptance.log`.
The full suite was then repeated alone (69.303s); adapter checks were also repeated
alone (7.489s). No code or acceptance result relies on the overlapping run.

The CLI report includes only observed advisory facts and fixed guidance. Manager
step/finish/ACK interrupted before return stays unknown even when the test proves
the transaction committed. No mutation is queried, replayed or automatically
released. A normal owned cleanup routine returns confirmed; persistent synthetic
cleanup errors stay unknown with one bounded recovery attempt and no exception
text. Temporary signal handlers are restored; stdin resources are closed.

Limits: native Windows signal/process behavior, real native CLI compatibility,
account/model access and AI correctness are not tested. Continuous custom
interrupts or failed process cleanup may require inspection; stdout interruption
cannot guarantee complete delivery. No protected schema/protocol/workflow paths
or Manager transaction semantics changed. No self-built idle service was started.

GitHub 403 and Library network blockers remain unchanged, with no retry, upload,
push, PR, main merge or release. A local commit, incremental/cumulative patches,
verified private bundle and machine-readable receipt carry this bounded batch.

Suggested next bounded task: improve the read-only inspection guidance for an
unknown interruption outcome, using existing task/completion/inbox queries.
Do not introduce automatic recovery, receipt replay or provider/account setup.
