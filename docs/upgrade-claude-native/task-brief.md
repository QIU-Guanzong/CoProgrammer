# Claude native task harness and installed collaboration

Base: `19040bc10a7f8de565cf65e6110ed37ea0ece2d3`, existing cloud workface; branch `codex/claude-native-collaboration`.
Preserve the eight reviewed commits, private transfer cache, old untracked
scope and all immutable receipts. No public write or forbidden Git transport.

Deliver one task-only Claude CLI adapter, independent of model provider
configuration. Reuse the existing worker/run/watch and JSON task/result contract;
validate claimed task/worktree before launch. Require explicit execute, default
to read-only built-in tool availability, and allow edit tools only with an
explicit per-invocation choice. Preserve native approval settings. Do not add
allowedTools, permission-mode, bypass, automatic ACK, retry, account selection,
login, model routing, new billing or a universal provider gateway.

Claude print/json/schema emits a result envelope. Bound the accepted stdout read,
discard stderr and native metadata, require successful non-error result and
strict structured_output {status,summary}; never treat plain result text as the
contract. Task-only invocation must not expose Manager/MCP tools. Tool selection
is not an OS sandbox; existing native hooks/settings remain a trust boundary.
The temporary output file has no hard write cap. Invoke through the existing
worker, which supplies timeout and process cleanup; standalone execute has no
independent timeout. Accepted JSON is limited to 128000 bytes.

Add focused offline portable/process tests and a bundled canonical guide through
existing package-data/catalog paths. Update only relevant installed entry
guidance and obsolete claims about Claude. Do not modify schemas, protocols,
workflows, pyproject/version, existing Codex execution, runner policy or setup
file selections. Skill edits are unnecessary and outside this increment.

Inventory only nonsecret existence/version/capability and auth/provider status.
One official fixed-version project-local Claude installation attempt is allowed;
no global profile/service change. Real-model acceptance uses only already
authorized available native configurations: at most one small task per usable
combination, serial, bounded at120seconds, no retry, in sensitive-data-free
Markdown Git fixtures. Read-only native discovery/auth checks precede tasks.
Use two windows/dependencies and explicit completion message receipts; record
which peer operation is a real native model, current assistant action or offline
fixture. Missing accounts/network failures remain concrete gaps, never success.

Acceptance: installed baseline check first; focused new adapter/knowledge and
installed candidate CLI/MCP resources; exact task/session/worktree/claim/message
correlation; failure preserves original claim/edits; no raw model/session output
or credentials retained. Serial full unittest and config/manifests/JSON/YAML
after final code changes. Keep all temporary data under the new work directory,
stop owned processes/services, remove disposable fixtures/install-test envs after
sanitized evidence, retain the project-local native install/cache for reuse.
