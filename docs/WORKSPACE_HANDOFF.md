# Dispatch and handoff across coding windows and computers

Requires CoProgrammer 0.3+. The existing task claim, messages and local Manager
remain compatible; no configuration or event migration is required.

## Choose work for the current window

After registering/pulsing a window in its own Git worktree:

```sh
coprogrammer manager dispatch --session codex-api
coprogrammer manager task claim --session codex-api --id api-v2
```

Dispatch reads client eligibility, dependency blockers, overlapping leases,
session freshness and occupied worktrees. It returns bounded candidates and
excluded tasks with complete counts and reasons. An expired task in a worktree
still needs explicit reconciliation before another task can occupy it.
Recommendations are sorted by task ID. They do not claim, pulse, renew, launch
a worker, or implement a priority/fairness policy. Claim rechecks atomically;
another window can take the work between preview and claim.

## Prepare a portable handoff

Finish or release a source claim after reconciling its actual work. Commit and
push the intended changes through the project's normal review process. Then
inspect the local version and cached Git baseline:

```sh
coprogrammer --version
coprogrammer workspace snapshot --base origin/main
coprogrammer manager handoff --session codex-api --task api-v2 --base origin/main \
  --check .coprogrammer/checks/unit.json > .coprogrammer/handoff.json
coprogrammer manager handoff --session codex-api --task api-v2 --format markdown
```

Use an ignored output path, or a path outside the project. JSON is the portable
input; Markdown is a readable summary. Export is available to the task's
creator or recorded owner, including closed/stale sessions for recovery.
Claimed and completed tasks must use the recorded owner's worktree and branch;
the creator cannot substitute another checkout's content.
For unfinished work owned by a different window, export before releasing the
claim, then release it and confirm that the source worker stopped. Release clears
the recorded owner, so only the creator can export a subsequently queued task.
Session identity is self-reported. Source check failures and missing checks
are retained, not upgraded to successful evidence.

The bundle includes task scope, client constraints, self-reported result,
CoProgrammer version, exact HEAD/base, sanitized repository identity and content
fingerprint. It omits machine paths, claim/lease tokens and message bodies.
Titles and summaries are untrusted source text. Its consistency hash does not
authenticate the sender.

## Inspect on the receiving computer

Transfer the bundle through an explicitly authorized channel. Fetch commits
and select the intended branch using your existing Git workflow, then compare:

```sh
coprogrammer workspace compare /path/to/handoff.json
```

The comparison checks repository lineage (or available identity for shallow
clones), exact HEAD, cached base, package version, content and uncommitted
changes. The source base ref is used unless `--base` is supplied. Missing refs,
version/content differences and dirty checkouts are explicit blockers. It does
not fetch, checkout, copy files or import Manager state. Exit 0 means context
alignment; exit 1 means differences; invalid bundles exit 2.

An aligned bundle still requires receiving-machine tests and a local task claim.
`ownership_reconciliation_required` highlights an exported active source claim.
Even a queued/done bundle can be stale relative to later source activity: confirm
the source worker stopped before taking over. Independent clones have independent
Managers; this release does not provide a cross-computer lock or global queue.
Git worktrees on one computer continue sharing local tasks and message receipts.

MCP read tools: `workspace_snapshot`, `task_dispatch`, `manager_handoff`,
`handoff_check` and `check_verify`. They use the same core as these commands.
The existing CLI/MCP `message_send`, inbox, thread and bounded wait operations
remain the communication path within a shared local Manager. Provider calls
(Claude, GLM, DeepSeek) remain explicit; no transfer or comparison contacts one.
