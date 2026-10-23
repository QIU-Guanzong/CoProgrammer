# Optional content protection before retry

Base: `cfa7ffd93a3367cf6f22bb90f9f8554943638d13`.

The existing explicit worker retry can execute a retained claim again and replace
newer in-scope edits. This is permitted existing behavior, not a breached
idempotency promise. Add an opt-in `worker run --protect-retry` mode without
changing the default, watcher, task/claim contracts or inbox receipt behavior.

Reuse workspace.snapshot's bounded aggregate content digest and the existing
worktree runner lock/event storage. Persist a started marker before launch and
an end digest after a normally returning invocation, including command failure.
Before continuing the same claim, compare current content to that end digest.
Missing baselines for existing claims, changed content, incomplete attempts and
invalid records stop before execution. Do not automatically rebaseline, reclaim,
ACK, release or override. Stale claims remain fenced by the existing worker.

Store only fixed metadata and aggregate hashes; no source contents, argv,
prompts or exception text. Cover all tracked and nonignored worktree files using
the existing snapshot rules. This is observation, not a sandbox or lock against
arbitrary editors; concurrent changes during a running attempt cannot be
attributed to a specific writer. Ignored/external inputs remain out of scope.

Acceptance: actual offline harnesses cover unchanged retry, external edits,
addition/deletion, old/missing/incomplete records, expired claims, cancellation,
default compatibility and completed-task/notification idempotency. Preview
writes no retry records. Validate CLI wiring and bundled guide, then serial full
unittest/config/manifest/JSON/YAML. Keep all prior evidence. No real model,
credential/session access, remote writes, CI trigger or package publication.
