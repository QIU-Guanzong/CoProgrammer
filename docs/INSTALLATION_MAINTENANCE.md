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

New files, including a new setup receipt, are fully written and synced in a
same-directory temporary file before publication. Publication uses a hard link
that refuses an existing destination: a file created while setup is preparing
its output is preserved, even when its bytes match the generated content.
Filesystems without hard-link support fail without an overwriting fallback.
Normal creation permissions still follow the process umask; setup does not
change the umask or global permissions.

On a later failure, removal of a newly created file requires both its observed
file identity and its contents to match this invocation. Independently replaced
or edited files are retained for inspection. Existing-file updates continue to
use their expected-content check and staged replacement. These checks do not
lock external editors, make rollback an atomic conditional unlink, or make the
whole multi-file installation atomic. A crash or uncertain publication may
leave complete output or staging files; inspect them before explicitly retrying.

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

A catchable Ctrl+C also attempts that conditional recovery when the setup
receipt still matches its pre-run bytes (or is still absent for a new install).
The interruption remains an interruption: no success report or automatic retry
is issued. If the receipt changed or cannot be read, setup retains completed
writes for inspection, since receipt publication may already have completed.
A second Ctrl+C can interrupt recovery itself. Inspect the files and receipt,
then preview the same `setup --upgrade` selection before explicitly applying it.
Clean recovery permits a later explicit upgrade; preserved user edits continue
to conflict. This does not add recovery for SIGKILL or process crashes, and the
receipt comparison does not lock arbitrary external editors.

If Ctrl+C interrupts a staged setup write and temporary-file cleanup also raises
an I/O error, setup retains the original `KeyboardInterrupt` as the primary
exception with the cleanup error as its cause. Failed staging cleanup is not
retried; inspect any remaining staging file. Ordinary cleanup errors still fail
the operation, and another Ctrl+C can interrupt cleanup/recovery. This does not
close the interval between file publication and recording a completed write;
unconfirmed output is retained rather than assigned optimistic rollback ownership.

Confirmed upgrade replacements are now recorded inside the write helper before
it returns to the installer. Recovery requires both their staged file identity
and unchanged content; a later same-content replacement is preserved. Identity
is checked again after staging a rollback, before replacing the target. These
checks narrow the recovery window, but do not lock external editors or provide
atomic compare-and-swap. An interruption inside publication before confirmation
still leaves output for inspection. Hard links to the same inode and edits after
the final observation remain outside this protection.

Recovery also retains files after an ordinary I/O/runtime failure when the receipt
has changed or cannot be read reliably; publication may have succeeded before the
primitive reported failure. The error reports retention instead of claiming rollback.
A recovery target observed with multiple hard links is retained even when content
and inode match, including an alias left by failed staging cleanup. This is more
conservative than older cleanup behavior: inspect the receipt, generated target
and staging artifacts before manually retrying. No automatic deletion/retry is
added. A transient alias removed before observation, or a link/write added after
the final check, remains indistinguishable; no global signal mask or transaction
guarantee is introduced.

An entire multi-file update is **not a filesystem transaction**. A process kill,
disk failure or arbitrary editor can interrupt it. Inspect the selected files
and receipt before retrying; mismatched hashes continue to conflict. A local
receipt is an advisory record, not authenticated evidence or a sandbox.

### Inspect an uncertain installation before retrying

1. Stop the current setup invocation and coordinate a quiet interval with other
   project editors. Do not remove leases or kill unrelated processes to obtain it.
2. Preserve a private copy of the affected targets, the setup receipt and any
   remaining staging files. Do not delete the receipt to force adoption or use a
   wildcard cleanup of `.coprogrammer-setup-*` paths; a name may now belong to
   another writer. Replacement cleanup retains staging names whose captured
   identity is unavailable or no longer matches, as creation cleanup already does.
3. Preview the same client, edition and selection without `--apply`, for example:
   `coprogrammer setup --client claude --edition mcp --upgrade`.
   A successful preview or `unchanged` content does not prove provenance or a
   live client connection. Review preserved content and the prior receipt together.
4. If the old receipt and files were restored together, an explicitly reviewed
   retry can proceed. If some files are new/custom while the receipt is old,
   retain those edits and either manually reconcile them or restore the complete
   known-good file/receipt pair from a trusted backup. Do not restore only the
   receipt over newer files. A new readable receipt matching the selected files
   may mean publication completed before the error; inspect instead of undoing it.
5. Resolve unreadable/linked receipts and conflicting files with their owner,
   preview again, then explicitly apply only the reviewed selection. There is no
   automatic force, lease takeover, rollback replay or evidence deletion step.

The existing v1 receipt format is unchanged, including legacy projects without
a receipt. Files retained for inspection are not a durable recovery journal.
For reproducible boundary observations in a source checkout, run
`PYTHONPATH=src python docs/upgrade-setup-staging/probe_publication_boundaries.py`.
It uses disposable synthetic directories and an in-memory pre-registration
counterexample. It does not exercise an AI model or modify production source.
Pre-registering uncertainty can support a future explicit retain-all policy, but
pre-registering completed ownership is unsafe. A retain-all policy would also
disable useful existing recovery on failed syscalls; it is not silently enabled
here. Neither policy makes external-editor writes atomic with filesystem checks.

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
