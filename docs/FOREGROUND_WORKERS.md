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
still need a trusted harness adapter or their existing MCP/Skill workflow.
WorkBuddy GUI testing remains deferred.

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
使用 OpenClaw 服务代理时，单独选择可信原生 CLI 进行本机隔离验证；不把代理
服务的配置当作当前项目的接入证明。
