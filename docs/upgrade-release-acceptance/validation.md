# Installed candidate validation

Cloud Linux, Python 3.12.14, `/workspace/CoProgrammer`; candidate base
`5b3f7aa154745038da4cf15c5fd1dfac1a8042a5`. The final local commit and artifact
hashes are recorded separately in the private release-acceptance receipt.

Two independent read-only reviews compared CLI help, package selection, canonical
documentation and configuration. No runtime/configuration compatibility defect
was found. The actual initial wheel omitted the three new diagnostic guides.
The candidate adds these through the existing explicit knowledge catalog and
Markdown package-data path; setup selection and resource request shapes remain
unchanged. README, maintenance, knowledge and task workflow guides now agree;
the Codex example states that registration alone does not queue a task.

| Check | Actual result |
| --- | --- |
| Focused knowledge/stdio resources | 16 tests passed, 0.474s |
| Focused setup/upgrade | 30 tests passed, 0.707s |
| Serial full unittest | 474 passed, 0 failed, 0 skipped, 65.254s |
| Clean wheel and sdist | Built offline with existing setuptools/wheel; no dependency download |
| Packaged resource contents | 6 Skills and 9 Markdown resources; three guides match canonical bytes |
| sdist rebuild | All 49 runtime/asset payloads equal the first wheel and current source |
| Installed entry points | External temporary cwd, no source PYTHONPATH; site-packages imports |
| Installed resources/setup | All 15 resources readable; full/skills/mcp editions and generated stdio MCP pass |
| Codex-specific generated TOML | Parsed, installed MCP starts, explicit setup upgrade preserves identical bytes |
| Installed offline demo | Passed and removed its disposable worktrees |
| Old configuration | Exact baseline config validates and remains unchanged in all three task fixtures |

The installed adapter workflow uses three independent disposable Git projects,
each with one scoped synthetic task and no remote. Every case performs plain
discovery with zero client launches, then exactly one synthetic version and
help query, a nonmutating worker preview and one explicit adapter invocation.
The success case finishes once; a native exit 7 becomes adapter/runner exit 1
with command_failed, an original claim and partial edits retained. Actual Linux
SIGINT returns a structured interruption receipt/130, preserves its claim/edit,
and stops the owned synthetic native process and child. No failed/interrupted
command is retried. Status, board, leases, inbox, thread, worker preview and Git
queries preserve the exact Manager event-log hash. Temporary projects disappear
only after those retained states and edits are verified.

The supplied harness exit is intentionally distinguished from the deeper native
exit. Native output is discarded. These are transport/coordination tests with
synthetic data, not real model quality, account authorization, Windows native
acceptance or proof against detached descendants.

Byte checks confirm codex_harness, runner, worker_cli, worker, watcher, setup,
integrations, cli and knowledge_mcp are unchanged from the base. Protected
schemas/protocols/workflows and pyproject/version are untouched. Private work,
transfer packets and Manager state do not enter the wheel or sdist. Prior
evidence hashes, configuration/manifests, JSON/YAML and final Git/bundle integrity
are recorded in the private machine receipt.

The 403 described in prior results is **historical**, from the earlier repository
handoff attempt. Neither the preceding native-probe round nor this round made a
GitHub write retry. This round makes no GitHub, Library, native-account or model
request, public push/PR/merge/release, Air call, download or global config change.
The final cleanup receipt records removed temporary build/install environments,
zero services and released own development leases. Archives/logs remain private.
