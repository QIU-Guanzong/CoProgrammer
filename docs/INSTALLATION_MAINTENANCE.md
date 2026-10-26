# Update an installed project

Upgrading the Python package does not refresh a project's copied Skills,
templates or MCP configuration. CoProgrammer 0.3.0a6 adds a local setup receipt
and an explicit update preview so installed projects can follow package changes.

```sh
python -m pip install --upgrade --pre coprogrammer
cd /path/to/your/project
coprogrammer setup --client codex --upgrade --include-content
coprogrammer setup --client codex --upgrade --apply
coprogrammer integrations verify --client codex
```

Replace `codex` with `claude`, `copilot`, `openclaw`, `workbuddy`, `harness` or
`generic`. Use the same edition/Skill selection as installation, for example
`--edition mcp` or `--no-mcp --skill coprogrammer-active-sync`.
Run the update from the intended Python environment: generated MCP launchers
pin that interpreter, package location and project directory. Reload the client
and complete its normal project/MCP trust flow after reviewing updated files.
Verification reports installation, transport and native discovery separately;
it does not establish model access. WorkBuddy GUI testing remains deferred.

## Check an installed Codex harness build

The cloud upgrade containing the Codex task adapter and its diagnostics remains
unreleased. Its package metadata is still `0.3.0a7`; that version alone does not
prove these additions are installed. Use the intended Python environment and
review the exact candidate build rather than assuming the public package has it.

```sh
python -m coprogrammer.codex_harness --check
coprogrammer knowledge show templates/CODEX_TASK_HARNESS
coprogrammer knowledge show templates/INTERRUPTED_RUN_INSPECTION
```

Plain `--check` starts no native client and tests discovery only. The bundled
Codex guide explains the optional `--check --probe-native` version/help probe,
worker preview, queued-task prerequisite and explicit execution. These guides
are also readable without a source checkout. A missing module/resource means
the selected environment/build needs inspection, not a task retry. Neither
diagnostic establishes account authorization or model readiness.

The same unreleased candidate includes the Claude task-only adapter:

```sh
python -m coprogrammer.claude_harness --check
coprogrammer knowledge show templates/CLAUDE_TASK_HARNESS
```

Its check only discovers an executable. Review the trusted native CLI's version
and existing authorization separately; this adapter never installs, logs in or
configures providers. The guide covers explicit execution and message receipts.

## What is refreshed?

| Existing file | Default setup | Setup with `--upgrade` |
| --- | --- | --- |
| Missing | Preview creation | Preview creation |
| Identical to the installed package | Leave unchanged | Leave unchanged |
| Recorded generated Skill, template or MCP file still matching its recorded hash | Report conflict if the new package differs | Preview `update`; `--apply` returns `updated` |
| Customized or differing file without a matching receipt | Report conflict | Report conflict |
| Project instructions (`AGENTS.md`, `CLAUDE.md`, Copilot instructions) | Preserve differences | Preserve differences |
| Linked paths, malformed or oversized receipt | Block application | Block application |

Without `--apply`, neither project files nor the receipt are written. Proposed
content contains generated data only; existing file contents are not printed.
One selected conflict blocks the entire application. There is no force option,
automatic config merge or automatic removal of deselected/older paths.

A successful setup records only paths, kinds and SHA-256 hashes of generated
non-instruction files in `.coprogrammer/setup-manifest.json`. Already identical
files can be recorded; differing files cannot be adopted. The receipt stores
no file contents or credentials and remains local to each worktree. The
existing repository-wide Manager lock serializes cooperating installers.
Selections retain records for other installed clients and unselected Skills.

For installations made before 0.3.0a6, run setup once to record files that still
match the current package. Differing older files require manual comparison;
the installer cannot prove their provenance. For mixed or custom MCP configs,
use `--no-mcp` to update Skills/templates and merge the service entry separately.
Back up custom files before deliberate manual edits. Deleting the receipt does
not authorize overwriting them.

Keep `.coprogrammer/` out of source control. Carry its receipt with a deliberately
moved workspace if you need recorded updates there; independent Git clones do
not inherit ownership or share live leases. This command does not alter ignore
rules, global configuration, accounts, other servers or package installations.

## Interrupted updates

Each replacement is staged as a complete file and rechecked before replacing
the target. The receipt is written last. On a caught failure, setup attempts to
restore/remove completed writes only while they still match this invocation's
bytes. It preserves concurrent edits and partial writes for manual inspection.

An entire multi-file update is **not a filesystem transaction**. A process kill,
disk failure or arbitrary editor can interrupt it. Inspect the selected files
and receipt before retrying; mismatched hashes continue to conflict. A local
receipt is an advisory record, not authenticated evidence or a sandbox.

## 中文操作说明

先升级 Python 包，在项目目录运行 `setup --client <客户端> --upgrade` 查看
待更新文件，确认后加 `--apply`。项目接入后仍未改动的 Skill、模板和 MCP 配置
可以更新；已有项目说明始终保留，自定义内容继续报告冲突。

记录保存在当前工作区的 `.coprogrammer/setup-manifest.json`，只包含文件路径、
类型与摘要。旧版没有记录时，只能接管与当前版本完全一致的文件；不能据此覆盖
不同内容。多个 Git 工作区共享安装锁，各自保留独立记录和路径配置。配置混有
其他服务器时，先用 `--no-mcp` 更新指引，再手动合并 MCP 服务片段。

升级后重载客户端，完成原有信任流程，再运行 `integrations verify`。文件已更新
不等于模型已登录或已自主协作。失败后先检查文件；整组文件不提供跨文件原子性，
安装记录也不能阻止任意程序修改文件。

Codex adapter 的当前云端升级尚未发布，包版本仍为 `0.3.0a7`，不能只凭版本号
确认新增功能。用同一 Python 环境运行 `python -m coprogrammer.codex_harness --check`，
再通过 `knowledge show templates/CODEX_TASK_HARNESS` 阅读随包指引；普通检查不启动
客户端。模块或资源缺失时先核对安装的构建，不重试原任务。
