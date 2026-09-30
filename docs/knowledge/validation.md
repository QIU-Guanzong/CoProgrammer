# Knowledge and setup verification

Verified locally on 2026-09-27 for the existing `0.2.0a1` preview. The full source
suite and a fresh wheel installed outside the checkout each passed **256 tests**.
Configuration/manifests, repository JSON/YAML, MCP parameter/tool schemas, all
six Skill metadata files, documentation links and diff whitespace checks passed.
JSON Schema/YAML validation dependencies were installed only in a temporary
environment; no new package runtime dependency was introduced.

| Behavior | Evidence |
| --- | --- |
| Packaged resources | Twelve exact catalog IDs; six Skill copies equal their plugin originals byte-for-byte |
| Native MCP capabilities | Real stdio resources/prompts across all four supported protocol versions; existing tools remain available |
| Bounded read-only context | URI whitelist rejects arbitrary project files, URLs and traversal; prompt arguments are validated data; notifications do not execute |
| Project onboarding | All three native layouts, no-write preview, selected Skills, repeated apply without changing existing timestamps |
| Preservation | Existing instructions remain unchanged; differing MCP/Skill/docs stop application; JSONC and test secret markers are preserved and never echoed |
| Filesystem handling | Target/parent and Manager log/lock links rejected; nonregular files rejected; concurrent installers serialized; late write failure retracts unchanged completed files |
| Independent forward-test | Existing Codex Git project kept its AGENTS and MCP configuration while six Skills and three guides were installed with `--no-mcp` |
| Installed launch | Isolated wheel used outside the source tree; generated Claude config launched MCP with twelve resources and two prompts |

Tests live in `tests/test_knowledge.py`, `tests/test_knowledge_mcp.py`,
`tests/test_setup.py`, and the existing plugin/MCP suites. The independent test
used temporary repositories and an installed wheel, without changing real
client settings or contacting model providers.

GitHub Checks on draft PR #1 provide current-head Ubuntu/Windows Python
3.10/3.13 verification. Symlink tests can skip where creation is unavailable;
normal path, conflict and content-preservation behavior is tested everywhere.

No native GUI trust/reload, authenticated model call, package publication or
merge was performed. Resources are curated bundled content, not a general
project-file reader. Setup is a cooperating local process, not protection
against a hostile process replacing directories while files are being written.
Shared MCP and package changes remain subject to maintainer review.
