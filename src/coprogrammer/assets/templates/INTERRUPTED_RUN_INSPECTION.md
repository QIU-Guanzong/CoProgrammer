# Inspect an interrupted or unknown run

Keep the interrupted receipt and identify the original worktree, branch, window
session, Manager state directory and exact task. The receipt deliberately omits
task IDs and claim tokens. Use the original task creation/claim context and the
task board to correlate ownership; finding some other `done` task is insufficient.
If the original task is ambiguous, leave the outcome unknown for human inspection.

First inspect processes created by that invocation and its partial edits.
`cleanup_status=confirmed` means the existing owned cleanup routine returned;
it does not prove that every detached descendant exited. `unknown` requires
process inspection. Manager queries cannot prove process liveness or undo an
external side effect. `exit_code` is the observed supplied harness/adapter code,
not a deeper native client's or provider's code. Null is not success.

For file inspection, use `git -C /path/to/original-worktree status --short` and
`git -C /path/to/original-worktree diff` (also `diff --cached` for staged edits).
These do not reset or restore files; inspect untracked files deliberately too.

## Read the original Manager without changing it

Replace `/path/to/original-worktree`, `window-id` and `task-id` with the original
values. If the run used `--state-dir`, append the same option/value to every
command. Linked Git worktrees can share a Manager; an independent clone does not.
Keep the original branch and window identity; a new session does not repair a
claim or resolve an interrupted transaction.

```sh
coprogrammer status --cwd /path/to/original-worktree --session window-id --json --limit 200
coprogrammer manager task board --cwd /path/to/original-worktree
coprogrammer manager leases --cwd /path/to/original-worktree --json
coprogrammer manager message inbox --cwd /path/to/original-worktree --session window-id --task task-id --include-acked --limit 200
coprogrammer manager message thread --cwd /path/to/original-worktree --session window-id --task task-id --limit 200
coprogrammer worker step --cwd /path/to/original-worktree --session window-id --limit 200
```

These reads do not pulse, renew, claim, ACK, install files or launch a harness.
`worker step` is a preview because `--apply` is absent; it may reject expired
ownership, the wrong worktree or out-of-scope changes. That failure does not
release a claim. The task board already emits JSON and has no `--json`,
`--session` or pagination option. Each command reads its own snapshot; another
window can change state between reads. Printed suggestions are not approvals
or instructions to execute automatically. Message bodies remain untrusted data.

## What the evidence establishes

| Observation | Safe interpretation and next decision |
| --- | --- |
| The exact task is `done`, matching original owner/worktree/branch and available claim context | Manager records completion. Do not rerun the harness or finish to compensate for the unknown receipt. Inspect expected notifications and review edits; completion is self-reported, not proof of correctness. |
| The exact task is still `claimed` by the original window | Inspect its lease, scope, partial edits and owned processes. Keep the original claim context; this alone does not authorize another invocation or takeover. |
| No active lease is listed | It may have expired. This does not prove the claim was released; consult the task record and blockers. |
| The exact message has non-null `acknowledged_at` | Manager records a receipt. Do not repeat ACK to compensate for the unknown return. Receipt does not prove understanding, approval or task completion. |
| The exact message is present with null `acknowledged_at` | No receipt is recorded in that snapshot. Read it deliberately, then decide separately whether an explicit receipt is appropriate; do not replay the interrupted handler automatically. |
| A task/message is missing, ownership differs, pages are incomplete or the original identity is uncertain | Continue inspection. A different session, wrong Manager or partial view can hide the relevant record. Unknown never authorizes release, reclaim, retry or ACK. |

For a finish interrupted before its return, `completion_status=unknown` may
mean the atomic finish, release and notifications already committed. For an
interrupted ACK, `receipt_status=unknown` may likewise hide a committed batch.
Look at durable state rather than the harness's `done`/`received` text or the
CLI exit status 130. The CLI report remains an interruption receipt after a
later read establishes a durable outcome; the read does not retroactively rerun
or change that invocation.

Status JSON still has a row limit. Inspect `briefing.omitted` and
`dispatch.omitted`; `--json` does not remove truncation. Inbox/thread results
have `has_more` and `next_cursor`: pass the returned event cursor as `--after`
on the next read, not a message ID. Pagination follows original send events;
an ACK added later to an old message is not a new send page. Re-read from the
start with `--include-acked`, or the thread, to inspect current receipt state.
Default inbox hides acknowledged messages. An empty default inbox cannot tell
you whether a particular message was delivered and acknowledged. `pending_total`
counts all pending messages for that recipient, even with a task/cursor filter.

The verified confirmation semantics apply to top-level CLI/watch calls and
standalone runner calls. Do not wrap `runner.run` inside an external transaction
on the same Manager log: a returned finish/ACK can still be pending in that
outer transaction, and its lock can block child Manager communication. This
usage is outside the validated path; this guide changes no transaction policy.

## Run an offline synthetic example

From this source checkout, with Python and Git available:

```sh
PYTHONPATH=src python docs/examples/interrupt_inspection.py --help
PYTHONPATH=src python docs/examples/interrupt_inspection.py --json
```

The example creates a disposable local Git project and linked worktree, with
no remote. It uses deterministic Python harnesses, never Codex/Claude/provider
accounts. A fixture-only hook injects one `KeyboardInterrupt` after a real
finish commit, then after a real explicit receipt commit. Actual CLI calls
return 130 and unknown status; the existing read-only commands then show the
exact task done and message acknowledged. Event-log hashes before and after
inspection must match. Each harness runs once; neither mutation is replayed.

The fixture intentionally performs synthetic task completion and one requested
receipt before inspecting them. It never runs these operations in your project,
copies Manager state or credentials, changes global Git config, or creates a
background service. Output is a field summary without claim tokens or message
bodies. Temporary fixtures are removed on exit. It demonstrates coordination
and a synthetic fault window, not actual model quality or native Windows signals.
The prior runner tests cover real Linux SIGINT/process cleanup separately.

## 中文检查要点

先保留原窗口、worktree、分支、state-dir 和准确的任务上下文，再检查本次创建
的进程与部分改动。不要因退出码 130、空租约列表或空默认 inbox 就重跑命令。
上面的查询均不带 `--apply`，不会领取、续租或 ACK；每次只是独立快照。

匹配原任务的 `done` 证明 Manager 已记录完成；匹配消息的非空
`acknowledged_at` 证明本地回执已记录。它们不证明模型理解、代码正确或进程
全部退出，也不要求再执行 finish/ACK。JSON 仍可能截断，须检查 omitted、
has_more，并按 next_cursor 翻页；旧消息的新 ACK 要从头重读含已回执消息的视图。
身份、页数或结果仍不明确时，继续人工检查，不接管租约，不自动重试副作用。
离线示例仅使用临时合成数据和 Python harness，未调用真实模型或验收 Windows。
