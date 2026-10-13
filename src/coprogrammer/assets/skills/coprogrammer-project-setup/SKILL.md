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
manual integration. WorkBuddy and generic hosts receive import kits, not claimed
native discovery paths. Do not modify global profiles or install a remote bridge
as part of project setup.

Use `--edition skills`, `--edition mcp` or `--edition full` (CLI 0.3.0a3+)
for the requested variant. Add `--no-mcp` when only Skills and Markdown are needed.
Inspect the proposed
paths and contents, including every existing-file conflict. Preserve existing
instructions and MCP servers; setup does not overwrite or merge them.

For an authorized setup request, apply the reviewed plan with the same flags:

```bash
coprogrammer setup --client codex --apply
```

Only absent files are created. Read the result, check the generated files and
report conflicts that still need narrow manual integration. Do not infer that
a generated MCP configuration proves the client connected or trusted it.
Follow that client's available reload/trust flow when connection verification
is in scope. No setup step grants authority to contact other agents or services.

Inspect the bundled guidance without changing the project:

```bash
coprogrammer knowledge list
coprogrammer knowledge show templates/COORDINATION
```

Use `docs/coprogrammer/COORDINATION.md` for the session, task claim, edit guard
and message workflow. Keep live state in Manager events, not instruction files.
Summarize created files, preserved conflicts and the actual checks performed.
