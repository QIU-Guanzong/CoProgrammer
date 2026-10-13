---
name: coprogrammer-project-setup
description: "Install project-local CoProgrammer Skills, Markdown and MCP configuration or import kits for coding agents and agent harnesses while preserving existing files."
---

# CoProgrammer Project Setup

Use this workflow when the user wants CoProgrammer available in a repository.
It installs reusable guidance and local connection configuration; it does not
start agents, run models or approve their work.

Prerequisite: a matching CoProgrammer CLI is installed and `coprogrammer` is on
`PATH`. Do not assume the target contains CoProgrammer's Python source tree.
If the CLI is unavailable, report that setup could not be verified; do not
install packages or change global client settings without the user's scope.

Read existing repository instructions and determine the requested client.
Preview its local file plan from the target repository:

```bash
coprogrammer setup --client codex --include-content
```

Choose `claude` for Claude Code or `copilot` for GitHub Copilot. With CLI
0.3.0a4+, choose `openclaw`, `workbuddy`, `harness` (generic agent harness) or
`generic` for other hosts. Read `coprogrammer integrations list` for activation
paths. OpenClaw loads workspace `skills/`; its exported node MCP entry needs
manual integration. With CLI 0.3.0a5+, WorkBuddy uses documented project
`.codebuddy/skills/` and `.workbuddy/mcp.json`; older versions use import kits.
OpenClaw also receives an isolated embedded profile; generic hosts receive import
kits. `coprogrammer integrations verify --client CLIENT` reports installation
conflicts, stdio transport and native OpenClaw discovery separately from model
connection. Do not modify global profiles or install a remote bridge
as part of project setup.

Use `--edition skills`, `--edition mcp` or `--edition full` (CLI 0.3.0a3+)
for the requested variant. Add `--no-mcp` when only Skills and Markdown are needed.
Inspect the proposed
paths and contents, including every existing-file conflict. Preserve existing
instructions and MCP servers. Differing custom files require manual integration.

For an authorized setup request, apply the reviewed plan with the same flags:

```bash
coprogrammer setup --client codex --apply
```

With CLI 0.3.0a6+, `setup --upgrade` previews updates to generated files still
matching the local hash receipt; add `--apply` after review. Instructions are
always preserved, and differing unrecorded/custom files remain conflicts.
With CLI 0.3.0a7+, `start --client CLIENT --session WINDOW --apply-setup --dry-run`
previews installation and registration together. Remove `--dry-run` within the
authorized scope to apply; conflicts prevent registration. Use `--resume` for
the same existing window. Review/checkpoint setup files before scoped work.

Read the result, check the generated files and
report conflicts that still need narrow manual integration. Do not infer that
a generated MCP configuration proves the client connected or trusted it.
Follow that client's available reload/trust flow when connection verification
is in scope. No setup step grants authority to contact other agents or services.
For OpenClaw, a managed launcher may ignore local profile variables; verification
must bind the generated profile before discovery. Select a trusted native CLI
explicitly with `--native-executable` when needed; keep service settings intact.

For an authorized foreground execution workflow, CLI 0.3.0a7+ `worker watch`
reuses the trusted JSON harness contract with finite cycle/duration limits.
Preview first; add `--apply` to launch. `--wait` is a bounded foreground wait,
and `--handle-inbox` accepts only the harness's explicit delivered-ID receipts.
Stop on failed scope checks, decisions or invalid replies; do not retry or
take over leases automatically. It does not launch GUI clients or choose models.

Inspect the bundled guidance without changing the project:

```bash
coprogrammer knowledge list
coprogrammer knowledge show templates/COORDINATION
```

Use `docs/coprogrammer/COORDINATION.md` for the session, task claim, edit guard
and message workflow. Keep live state in Manager events, not instruction files.
Summarize created files, preserved conflicts and the actual checks performed.
