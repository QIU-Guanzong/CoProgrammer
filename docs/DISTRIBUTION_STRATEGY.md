# Distribution Strategy

Last updated: 2026-06-10

Goal: a developer should be able to adopt CoProgrammer in **under five
minutes** through whichever surface their stack already uses. We ship the same
core (CLI + Manager event log + schemas) through six thin wrappers instead of
building six products.

## Channel Matrix

| Channel | Audience | Status | Install Story |
| --- | --- | --- | --- |
| **Agent Skills (SKILL.md)** | Users of Claude Code, Codex CLI, Gemini CLI, Copilot, Cursor, 35+ tools | ✅ 5 skills exist in `plugins/coprogrammer/skills/` | Copy skill folder, or install via skills.sh / openai/skills-style catalogs |
| **MCP server** | Any MCP client (Claude Code/Cowork, Codex, Cursor, custom agents) | ✅ `coprogrammer mcp serve` (zero-dep stdio); `server.json` ready | `uvx coprogrammer mcp serve` once on PyPI; publish via mcp-publisher |
| **PyPI / uvx CLI** | Terminal users, CI scripts, orchestrator hooks | ✅ entry point exists; ⏳ not yet published | `pipx install coprogrammer` / `uvx coprogrammer` |
| **GitHub Action (reusable)** | Any repo wanting PR digests without setup | ✅ `action.yml` at repo root | `uses: QIU-Guanzong/CoProgrammer@v0` |
| **Codex plugin** | Codex teams wanting shared install | ✅ `plugins/coprogrammer/.codex-plugin/` | `codex plugin marketplace add <repo>` |
| **Claude Code plugin** | Claude Code teams | ⏳ wrap same skills + MCP in plugin manifest | `/plugin install` from a marketplace repo |

Key research facts behind this matrix (2026-06):

- **SKILL.md became an open cross-vendor standard** (spec at agentskills.io,
  published 2025-12; adopted within weeks by Codex CLI, VS Code Copilot,
  Gemini CLI, Antigravity, Cursor; Vercel's skills.sh acts as a package
  manager/directory; OpenAI maintains a curated catalog at openai/skills).
  Our existing five skills are already in the right format — distribution is
  now a listing problem, not a build problem.
- **The official MCP Registry is live** (registry.modelcontextprotocol.io).
  Publishing = ship package to PyPI → `mcp-publisher init` (creates
  `server.json`) → `mcp-publisher login github` → `mcp-publisher publish`.
  Namespace `io.github.qiu-guanzong/*` is verified via the GitHub account.
- MCP clients then discover the server with a one-line config; `uvx` makes
  install-on-first-run free for users.

## What Each Wrapper Exposes

```text
                ┌────────────── SKILL.md skills ──────────────┐
                │  workflows: covenant / task brief / sync /  │
                │  digest review / integration plan           │
                └──────────────────┬──────────────────────────┘
                                   │ call CLI or MCP tools
┌──────────── CLI (PyPI) ──────────┴───────────┐
│ digest · manager (lease/heartbeat/contract/  │
│ forecast/status) · manifest · plan validate  │
└──────────────────┬───────────────────────────┘
                   │ same internals
┌────────── MCP server (stdio) ────────────────┐   ┌── GitHub Action ──┐
│ tools: digest_branch, manager_status,        │   │ PR digest comment │
│ manager_forecast, lease_request, heartbeat,  │   │ + artifact        │
│ contract_propose                             │   └───────────────────┘
└──────────────────────────────────────────────┘
```

Design rule: **skills describe workflows, tools execute state changes.**
Skills tell the agent *when and why* to request a lease or digest a branch;
the MCP tools / CLI are the only things that write Manager events. This keeps
behavior identical across Claude Code, Codex, and Cursor.

## Five-Minute Quickstarts (to put in README)

1. **MCP (any client):**

   ```json
   { "mcpServers": { "coprogrammer": {
       "command": "uvx", "args": ["coprogrammer", "mcp", "serve"] } } }
   ```

2. **Skills:** copy `plugins/coprogrammer/skills/*` into your agent's skills
   directory (`.claude/skills/`, `.codex/skills/`, etc.).
3. **CI:** `uses: QIU-Guanzong/CoProgrammer@v0` in a PR workflow.
4. **Terminal:** `pipx install coprogrammer && coprogrammer manager init`.

## Release Checklist (v0.1.0)

1. `python -m build` + publish `coprogrammer` to PyPI (enables uvx/pipx and is
   a prerequisite for the MCP registry).
2. Tag `v0` / `v0.1.0` so the GitHub Action ref is stable.
3. `mcp-publisher login github && mcp-publisher publish` (server.json is
   ready; verify the namespace matches the GitHub org).
4. Submit skills to skills.sh and the openai/skills catalog; keep
   `plugins/coprogrammer/skills/` as the source of truth.
5. Add a Claude Code plugin manifest reusing the same skills + MCP server;
   list in a public marketplace repo.
6. README "Install" section linking all channels (done).

## Maintenance Rules

- One version number across pyproject.toml, server.json, plugin.json; bump
  together (add a CI check later).
- Wrappers must stay thin: no logic in skills/action that is not in the CLI.
- Every new Manager capability ships in this order: CLI → MCP tool → skill
  mention → docs. If it cannot be expressed as a CLI command, it does not
  ship.
