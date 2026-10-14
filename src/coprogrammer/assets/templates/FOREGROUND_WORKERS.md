# Process tasks and handoffs from one foreground command

CoProgrammer 0.3.0a7 adds two explicit shortcuts over the existing local Manager.
They work across Git worktrees sharing the same repository. They do not log in
to coding clients, select models, launch their GUI windows or merge code.

## Install guidance and register a window

Inside a committed Git checkout on a named branch:

```sh
coprogrammer start --client codex --session codex-api --apply-setup --dry-run --json
coprogrammer start --client codex --session codex-api --apply-setup
```

The first command previews both registration and the project file plan. The
second installs missing files or refreshes unchanged recorded files using a6's
setup receipt, then registers the window. Existing instructions remain intact.
Any selected setup conflict prevents registration. `start` without this option
keeps its earlier behavior of registering and previewing files only.

Use `--resume` for the same existing window. Claude Code windows backed by GLM
or DeepSeek can use `--client claude --provider glm` / `--provider deepseek`;
these are routing labels and do not configure accounts. `openclaw`, `workbuddy`,
`harness`, `generic` and `copilot` use the same supported setup profiles.

Review generated files and commit them or deliberately exclude local setup
files before starting scoped work. Configuration alone does not prove connection.
File installation and session registration are separate operations: if state
storage fails after installation, inspect the files before retrying. Use the
standalone `setup` command for edition/Skill selections.

## Continue ready tasks and explicitly received messages

For a trusted executable implementing the existing [JSON harness
contract](NATIVE_RUNTIME_WORKFLOW.md), preview first:

```sh
coprogrammer worker watch --session codex-api --handle-inbox \
  --notify glm-docs -- python /path/to/trusted-harness.py
```

Apply the reviewed invocation, optionally waiting for peer changes:

```sh
coprogrammer worker watch --session codex-api --apply --wait --handle-inbox \
  --notify glm-docs --max-cycles 20 --duration-seconds 300 --poll-seconds 5 \
  -- python /path/to/trusted-harness.py
```

The harness receives either a scoped task or an inbox packet. Task completion
can notify the specified windows; inbox handling acknowledges only unique
delivered IDs explicitly returned by the harness. A valid receipt lets the
same foreground watch continue to ready work. This is protocol delivery, not
proof that a model understood the message.

`--wait` uses the existing bounded Manager channel to notice dependency/task
changes and pending messages. Without it, the watch stops when no work is
ready. Each boundary check counts as a cycle, including idle checks and receipt
handling. Limits are 1–100 cycles, 1–600 seconds and 1–25 seconds per wait. Each
process invocation is capped by `--timeout-seconds` and the remaining duration;
no new invocation starts with less than one second remaining. Existing finite
Git/lock operations and process cleanup can add processing time beyond the
nominal duration. Only one watcher may run per worktree; command execution uses
the existing separate runner lock, leaving Manager calls available to peers.

The CLI streams compact JSON lines for changed states and a final
`coprogrammer.watch.v1` summary. Progress excludes message bodies, summaries and
claim IDs. The final result retains the existing worker report for inspection.

Unhandled inboxes, open decisions, invalid replies/receipts, failed commands,
scope checks and unavailable/occupied sessions stop the watch. There are no
automatic retries, lease takeovers, approvals, Git commits or background daemon.
Ctrl+C stops the foreground operation; inspect original claims and edits before
resuming. Prior uncommitted edits still participate in the next task's guard,
so review/checkpoint them before changing to incompatible task scopes.

The packaged `coprogrammer.example_harness` is a deterministic protocol fixture
for disposable tasks covering `docs/**`; it invokes no AI model. Real clients
can use the opt-in [Codex](CODEX_TASK_HARNESS.md) or [Claude](CLAUDE_TASK_HARNESS.md)
task adapter, a trusted custom
harness adapter or their existing MCP/Skill workflow.
WorkBuddy GUI testing remains deferred.

## Inspect process failures before another invocation

Applied runner reports include `launched` and `exit_code`; a watch retains these
in its existing `last` report. `launched` is true only after process creation
succeeds. `exit_code` is the original code observed after communication completes:
zero for a normal exit, nonzero for command failure, and a negative signal number
on POSIX when the child exits from a signal. It is null if no original exit was
observed, including a failed start or timeout. Cleanup's kill code is not reported
as the original outcome. The code belongs to the supplied harness command,
including an adapter wrapper, rather than a deeper client process or provider.
These fields diagnose the process, not model access or
task correctness.

| Report reason | What to inspect |
| --- | --- |
| `command_unavailable` | The trusted executable and local process/output I/O; `launched` shows whether a process actually started. |
| `command_failed` | The observed nonzero `exit_code` and the native client separately. |
| `timeout` | Partial edits, original claim and the selected duration; code remains null. |
| `invalid_reply` / `reply_too_large` | The harness's single JSON result shape or 128,000-byte output limit; a normal process exit can still have an invalid reply. |

These failures provide fixed `next_step` guidance without copying native output,
exception text or credentials. The claim and existing edits remain intact; the
watch stops after one failed invocation. Preview `coprogrammer worker step --session <window>`
and inspect/reconcile its original claim and changes before deliberately invoking
a trusted harness again. A later explicit success can finish that same valid
claim. Do not infer retry safety from an exit code or retry side-effecting commands
automatically. Receipt/scope failures and lock contention retain their existing
handling; these diagnostics do not release, reclaim or approve anything.

## Inspect a single-run Ctrl+C receipt

When `worker run` is interrupted inside the runner, its CLI emits one
`coprogrammer.runner.v1` report with `state=stopped`, `reason=interrupted` and
exit status 130. The Python API still raises a `KeyboardInterrupt` subtype,
`RunInterrupted`, whose `report` contains the same observations. `worker watch`
keeps its existing stopped/interrupted summary and exit behavior.

| `interruption_phase` | Meaning and inspection |
| --- | --- |
| `before_launch` / `boundary` | No harness launch observed. A step that did not return may already have committed its pulse/claim; null `claim_retained` means unknown. |
| `launching` / `running` | Launch handoff or harness execution interrupted. `launched=true` requires an acquired process reference; null means launch could not be determined. Inspect partial edits and the original claim. |
| `result` / `cleanup` / `guarding` / `receipt_check` | Native exit, result validation, owned-process cleanup or scope/receipt checking. Only an exit observed before cleanup is retained in `exit_code`. |
| `finalizing` / `acknowledging` | A finish or ACK transaction did not return. `completion_status` or `receipt_status` is `unknown`; it may have committed. Inspect durable state before deciding what to do. |
| `returning` | A result was being returned. A `confirmed` completion/receipt observation remains confirmed even though overall control flow was interrupted. |

Status observations use `not_attempted`, `unknown` or `confirmed` for completion
and receipts. A null `claim_retained` is unknown, rather than a released claim.
The interrupted report excludes claim tokens, messages, native output, summaries
and exception text. It does not query or replay state to resolve uncertainty.

The default main-thread Ctrl+C is briefly deferred during process reference
acquisition and existing process-tree cleanup, then propagated after the original
handler is restored. Cleanup confirms only that the owned cleanup routine returned;
`cleanup_status=unknown` requires inspecting owned processes. Failed/interrupted
cleanup has one bounded recovery attempt; no harness, claim, finish or ACK is
retried. Custom signal handlers and threaded callers retain their behavior.
Continuous custom exceptions and interruption of stdout itself cannot guarantee
a complete receipt or cleanup; Linux fixtures do not establish Windows acceptance.

Preview `coprogrammer worker step --session <window>` and inspect completion and inbox state
before another explicit invocation. A harness's `done` output alone cannot prove
that finish committed; an unknown outcome never authorizes automatic release,
reclaim, receipt replay or a side-effecting command retry.

Use [the inspection guide and runnable offline example](INTERRUPTED_RUN_INSPECTION.md)
to check the exact task, message receipts, limits and original Manager context
without repeating a mutation.

## Verify the intended native OpenClaw

```sh
coprogrammer integrations verify --client openclaw
coprogrammer integrations verify --client openclaw \
  --native-executable /path/to/native/openclaw
```

The second command explicitly selects a trusted native CLI; it does not repoint
the default launcher. Verification requires `config validate` to report the
generated isolated profile's exact path before probing MCP. If a service proxy
ignores local environment settings, the result is `isolated_profile_not_used`.
Keep managed-service configuration separate. No fallback changes its accounts,
settings, executable or trust policy. Model access remains unchecked.

## 中文说明

`start --apply-setup --dry-run` 可一起预览项目接入和窗口登记，去掉 `--dry-run`
后安装/更新未被改动的生成文件并登记窗口。存在冲突时不登记；已有项目说明保留。
先审阅并提交接入文件或明确排除本机配置，再开始文件范围受控的任务。

`worker watch --apply` 在前台连续处理可领取任务；`--wait` 有限等待其他窗口的
依赖任务和消息。必须提供可信的 harness 程序；`--handle-inbox` 只接受程序对已
投递消息给出的明确回执，`--notify` 把完成交接送到指定窗口。失败、人工决策和
文件范围问题会停止，不会自动重试、抢占或提交代码。

这使协作流程更少依赖重复执行命令，但没有代替客户端登录、模型接入和人工审阅。
失败报告的 `launched` 表示是否成功创建进程，`exit_code` 保留观测到的原始退出码；
超时或未成功启动时为 null，不把清理时的强制终止码当成原始结果。先按 `next_step`
检查原 claim、部分改动及客户端，再决定是否明确继续；不会自动重试有副作用的命令。
使用 OpenClaw 服务代理时，单独选择可信原生 CLI 进行本机隔离验证；不把代理
服务的配置当作当前项目的接入证明。
