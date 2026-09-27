# Skills, MCP and Markdown integration notes

Primary documentation reviewed on 2026-09-27:

| Source | Finding and implementation choice |
| --- | --- |
| [Codex customization](https://learn.chatgpt.com/docs/customization/overview) and [MCP](https://learn.chatgpt.com/docs/extend/mcp) | Use project `.agents/skills`, `AGENTS.md` and `.codex/config.toml`; setup does not bypass project trust. |
| [Claude skills](https://code.claude.com/docs/en/skills), [memory](https://code.claude.com/docs/en/memory) and [MCP](https://code.claude.com/docs/en/mcp) | Use `.claude/skills`, root `.mcp.json` and a new `CLAUDE.md` importing `@AGENTS.md`. Existing instructions remain intact. |
| [Copilot skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [repository instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions) and [VS Code MCP](https://code.visualstudio.com/docs/agent-customization/mcp-servers) | Copilot recognizes `.agents/skills`, so share that layout with Codex; also generate `.github/copilot-instructions.md` and `.vscode/mcp.json`. Report potential duplicate skills in other discovery directories. |
| [MCP resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources) and [prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts) | Add explicit read-only document resources and parameterized draft prompts. Advertise only implemented methods; no subscription or dynamic file access. |

Setup refuses to rewrite differing MCP configurations: JSONC comments and TOML
tables need deliberate integration, and values may contain credentials. Preview
returns generated content only. Client trust/reload flows and machine-specific
paths remain visible limitations.

The package now carries its curated Markdown resources. The source repository
is not a runtime dependency, and equivalence tests catch drift between plugin
Skill originals and wheel copies. Dynamic Manager state stays in the event log,
separate from stable instructions and reusable document templates.
