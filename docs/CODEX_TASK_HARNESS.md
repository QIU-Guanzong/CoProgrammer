# Explicit Codex CLI task harness

This task-only adapter uses an already installed and authorized Codex CLI.
Use a CoProgrammer build containing this adapter in the same Python environment
as your worker command. This cloud branch is unreleased; an earlier public
package may report `No module named coprogrammer.codex_harness`. Check the
interpreter/build before retrying a claimed task.

The build bundles this guide and its worker/recovery guides. Read them without
a source checkout through the existing installed CLI:

```sh
coprogrammer knowledge show templates/CODEX_TASK_HARNESS
coprogrammer knowledge show templates/FOREGROUND_WORKERS
coprogrammer knowledge show templates/INTERRUPTED_RUN_INSPECTION
```

Check native executable discovery first, without a task packet or model call:

```sh
python -m coprogrammer.codex_harness --check
python -m coprogrammer.codex_harness --check --executable /trusted/path/to/codex
```

Plain `--check`: `available` (exit 0) reports only an executable file found through
PATH or your explicit path. `unavailable` (exit 1) gives the next step. Version,
client configuration and model access remain `not_checked`. This discovery-only
mode does not start Codex, read stdin/accounts/Manager state or change setup files.
`--check` and `--execute` are mutually exclusive. Select your intended client configuration
through its existing authorized flow before task execution.
Pass the same `--executable` selection to the later worker adapter command;
the check does not pin the executable for subsequent invocations. The examples
below use an explicit trusted path for both steps.

## Opt in to local version and help diagnostics

```sh
python -m coprogrammer.codex_harness --check --probe-native --executable /trusted/path/to/codex
```

This option runs the discovered executable's `--version`, then `exec --help`,
once each, with no task stdin. Each command has a five-second timeout and owned
process cleanup. It does not run a task, login, provider/configuration command,
automatic download or install, or retry an existing claim. Raw native stdout,
stderr and exception text are discarded; the parsed stdout sample is at most
128,000 bytes. Temporary-file output is not a hard disk quota or sandbox.

The check report gains `native_probe`. `native_version` contains only a short
recognized `codex-cli` version token or `unknown`; no version threshold is used.
`exec_help` checks actual help option rows for `--ephemeral`, `--sandbox`,
`--output-schema` and `--output-last-message`, matching the adapter's unchanged
argv and the [official CLI reference](https://developers.openai.com/codex/cli/reference/).
Mentions in help descriptions/examples do not advertise an option. Unrecognized
or colored/localized help may remain unknown rather than guessing support.

| Native probe status | Meaning |
| --- | --- |
| `advertised` (exit 0) | A version token was recognized and successful, untruncated exec help advertises all four required options. Argument values, real execution and model access remain unverified. |
| `incomplete` (exit 1) | Inspect the version/help subresults: missing advertisements, unknown formats, nonzero exit, unavailable command, timeout, invalid UTF-8, oversized output or I/O/cleanup failure. No repair or retry occurred. |
| `unavailable` (exit 1) | Discovery found no executable; neither probe command ran. |

`exit_code` records only an original exit observed before cleanup; timeout/start
failures keep it null, never the cleanup kill's code. Probe argument misuse exits
2; `--probe-native` requires `--check` and cannot accompany `--execute`.
An interrupted probe exits 130 with a fixed diagnostic; the Python API still
raises `KeyboardInterrupt`. No later help query starts after interruption.
Configuration/model remain `not_checked`. After native startup, `network_used`
is also `not_checked`: CoProgrammer makes no network/model request, but help cannot
prove what a trusted executable's startup internally reads or contacts. No global
service, account, approval or profile is modified by the checker.

An incomplete probe is an earlier diagnostic, not permission to rerun a failed
side-effecting task. Inspect its original claim, messages and edits separately
using the [interruption inspection guide](INTERRUPTED_RUN_INSPECTION.md).

## Preview and explicitly execute a task

Register the intended window using the existing `start --client codex --session
codex-api` workflow.

These worker examples assume an eligible scoped task is already queued for that
window. Registration alone supplies no task and the runner will remain idle.
Inspect `coprogrammer manager task board`; deliberately create the intended task
using the existing [task workflow](AUTOMATIC_COLLABORATION.md) before execution.
Installed users can read `coprogrammer knowledge show templates/COORDINATION`
for task creation and scope examples.

Then preview from that installed environment:

```sh
coprogrammer worker run --session codex-api -- python -m coprogrammer.codex_harness --execute --executable /trusted/path/to/codex
```

After reviewing the task, scope and account authorization, allow workspace edits:

```sh
coprogrammer worker run --session codex-api --apply -- python -m coprogrammer.codex_harness --execute --executable /trusted/path/to/codex --sandbox workspace-write
```

The same argv works with the existing bounded foreground `worker watch` loop.
The adapter requires `--execute`, defaults to read-only and accepts an optional
`--executable /trusted/path/to/codex`. It invokes one `codex exec --ephemeral`,
requests a structured final result and discards native stdout/stderr. It does
not select a model, configure a provider, log in, copy credentials, change
approval settings or retry. Parent runner timeouts stop its process group.
The parent runner guards edits and owns completion; permissions and the
post-run scope check do not prove code correctness.

Inbox packets are refused. Receive messages through the existing MCP/client
receipt workflow before resuming work; no automatic ACK is added.
If a worker report stops at `inbox`, inspect `coprogrammer manager message inbox
--session codex-api`, review the delivered messages and explicitly receipt the
ones you received through that workflow. Passing `--handle-inbox` to `worker
run/watch` with this task-only adapter still delivers a refused inbox packet.
Existing claims and edits remain intact after a launch failure; no claim is
invented for an inbox without owned work. Inspect them and the native client separately before
another explicit invocation. `--check` neither retries nor clears that state.

For a separately authorized execution, optionally add
`--diagnostics /private/execution.json` to the adapter argv after `--execute`.
The parent directory must already exist and the file must be new. The adapter
creates it with owner-only POSIX permissions and refuses to overwrite an old
receipt. Keep it outside claimed project files, in an ignored/private runtime
directory. Plain check cannot create an execution receipt.

This local operator artifact records fixed stages, task/session/claim IDs and
observed native exit status, without packet titles, summaries, account values
or native stdout/stderr. It does not change the task/result contract. A returned
native exit establishes process startup; an OSError around subprocess I/O leaves
startup unknown. Model startup remains unknown in this artifact, including after
a valid structured reply. The receipt is evidence to inspect, never authority
to complete, ACK, take over a lease or retry a task. A timeout/interruption may
leave the last checkpoint rather than a final outcome; consult the parent runner
report and original claim. Local storage, native nonzero exit, missing result
and invalid result are distinguished without weakening the existing guards.

For local Python I/O failures, `os_error` contains an allowlisted symbolic errno
such as `ENOENT`, `EACCES`, `ENOSPC` or `EPIPE`, otherwise `unknown`. It never
contains exception text or filenames. This describes the operation at the
recorded stage; it does not explain a native nonzero exit or establish that a
model request did or did not start. Native stdout/stderr remain discarded.

Before considering another explicitly authorized invocation:

| Recorded failure | Inspect first |
| --- | --- |
| `packet_read_failed`, `packet_too_large`, `packet_parse_failed` | Parent packet transport/size/encoding; native execution has not begun. Do not paste the packet into shared logs. |
| `packet_rejected`, `sandbox_rejected` | Current task, session, claim, worktree and allowed sandbox; do not fabricate a replacement claim. |
| `result_storage_io_failed` | Local temporary storage/access; use the recorded startup state because cleanup can fail after execution. |
| `native_launch_or_io_failed` | Selected executable and local process I/O; startup remains unknown even with an errno. |
| `native_exit_nonzero`, `result_missing`, `result_unavailable`, `result_invalid` | Original worker report, retained claim and edits; exit status alone does not identify account, quota or network failure. |

Use the existing `coprogrammer manager task board` and `git status --short` from
the affected worktree to inspect retained work. An expired lease does not prove
the old worker stopped. A partial checkpoint or failed diagnostic write needs
manual inspection; none of these stages authorizes release, takeover or retry.

Claude can use the separate [task-only Claude adapter](CLAUDE_TASK_HARNESS.md),
project MCP/Skills or a trusted custom harness. Each native adapter keeps the
client's existing authorized configuration; neither handles inbox receipts.

GLM/DeepSeek are provider choices for a separately configured compatible client.
`--client claude --provider glm` or `deepseek` labels a collaboration session;
it does not configure an account or prove model access. The Codex adapter uses
the selected native CLI's existing authorized configuration only.

Flags follow the official [non-interactive documentation](https://developers.openai.com/codex/noninteractive).
Offline fake-client tests validate transport and failure retention, not real AI
collaboration. Version/help probes inspect local CLI declarations only; account,
real task execution and model validation remain separate and unverified. No paid
model call is part of these diagnostics or the cloud acceptance fixtures.

## 中文首次使用

先在与 worker 相同的 Python 环境中运行 `python -m
coprogrammer.codex_harness --check`，需要时加 `--executable` 指向可信原生 CLI。
普通检查的退出码 0 只表示可执行文件可找到；版本、客户端配置、账户和模型仍未验证。
不加 `--probe-native` 时无需任务输入，不启动 Codex、不读取账户或 Manager、不写配置。
当前升级尚未发布；出现模块缺失时先核对 Python 环境与安装的构建版本。
检查时指定了 `--executable`，后续 worker 适配器命令也要传同一个路径；
诊断结果不会固定后续执行所用的程序。

需要版本/参数诊断时，明确加 `--check --probe-native`，仅运行可信程序的
`--version` 和 `exec --help`，每条最多五秒并清理自己的进程。退出码 0 仅说明
版本 token 可识别、帮助列出了适配器所需选项；不按版本猜支持，也不证明参数
语义、账户或模型可用。缺选项、异常输出、超时等返回 1；误用返回 2。
原始输出不会回显；原生程序内部配置/网络行为仍未独立验证。检查不登录、
不自动安装、不修改全局 profile，不执行或重试原任务。

确认客户端已有授权配置后，先预览 worker，再明确使用 `--apply` 和适配器的
`--execute`。此适配器只处理 task，inbox 仍须在已有客户端/MCP 流程中阅览并
明确回执。执行失败后先检查保留的原 claim 和改动；诊断不会自动重试或接管。
