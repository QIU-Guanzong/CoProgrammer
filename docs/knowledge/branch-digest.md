# Branch Digest

Generated: `2026-09-27T00:02:30+00:00`

Base: `3f42bf1`
Head: `WORKING_TREE`

## Branch Intent

Connect reusable Skills, native MCP document context and Markdown project
guidance to a preview-first, missing-file project onboarding workflow.

## Core Contribution

- Six packaged Skills and six Markdown templates available without a checkout.
- Exact-ID CLI knowledge catalog and native MCP resources/prompts.
- Native Codex, Claude and Copilot project layouts with preserved instructions.
- Conflict detection, no-secret previews, repeated-install stability and link checks.
- Real stdio, project setup and installed-wheel regression coverage.

## Changed Files

- `M` `README.md`
- `M` `docs/PLUGIN_QUICKSTART.md`
- `M` `plugins/coprogrammer/.codex-plugin/plugin.json`
- `M` `plugins/coprogrammer/plugin.json`
- `M` `pyproject.toml`
- `M` `src/coprogrammer/cli.py`
- `M` `src/coprogrammer/mcp_server.py`
- `M` `tests/test_mcp_robustness.py`
- `M` `tests/test_plugin_package.py`
- `A` `docs/knowledge/README.md`
- `A` `docs/knowledge/change-manifest.json`
- `A` `docs/knowledge/research.md`
- `A` `docs/knowledge/task-brief.md`
- `A` `docs/knowledge/validation.md`
- `A` `plugins/coprogrammer/skills/coprogrammer-project-setup/SKILL.md`
- `A` `src/coprogrammer/assets/skills/coprogrammer-active-sync/SKILL.md`
- `A` `src/coprogrammer/assets/skills/coprogrammer-integration-plan/SKILL.md`
- `A` `src/coprogrammer/assets/skills/coprogrammer-pr-digest-review/SKILL.md`
- `A` `src/coprogrammer/assets/skills/coprogrammer-project-covenant/SKILL.md`
- `A` `src/coprogrammer/assets/skills/coprogrammer-project-setup/SKILL.md`
- `A` `src/coprogrammer/assets/skills/coprogrammer-task-brief/SKILL.md`
- `A` `src/coprogrammer/assets/templates/AGENTS.md`
- `A` `src/coprogrammer/assets/templates/CLAUDE.md`
- `A` `src/coprogrammer/assets/templates/COORDINATION.md`
- `A` `src/coprogrammer/assets/templates/copilot-instructions.md`
- `A` `src/coprogrammer/assets/templates/handoff.md`
- `A` `src/coprogrammer/assets/templates/task-brief.md`
- `A` `src/coprogrammer/knowledge.py`
- `A` `src/coprogrammer/knowledge_mcp.py`
- `A` `src/coprogrammer/setup.py`
- `A` `tests/test_knowledge.py`
- `A` `tests/test_knowledge_mcp.py`
- `A` `tests/test_setup.py`

## Commit Summary

- No commits detected.

## Contract and Architecture Signals

- **build**
  - `pyproject.toml`

## Risk Level

`medium`

## Protected Path Matches

- `pyproject.toml` matches `pyproject.toml` [medium] (package and entrypoint configuration; owner review required)
- `src/coprogrammer/cli.py` matches `src/coprogrammer/cli.py` [medium] (CLI behavior affects PR digest generation)

## Noise / Non-Essential Changes

No dependency updates or unrelated refactors. Skill copies are deliberate wheel
resources with byte-equivalence tests against the canonical plugin originals.

## Integration Plan

Review the catalog, package data and consumer interfaces together on top of the
existing preview. Preserve the read-only resource allowlist and missing-only
setup semantics. Configuration trust and connection verification stay with the
client. Do not apply arbitrary generated instructions or auto-merge the branch.

## Validation Needed

- [x] Source suite: 256 tests
- [x] Installed-wheel suite: 256 tests
- [x] Independent existing-project and isolated-wheel forward-tests
- [x] Config, manifest, JSON/YAML/MCP schema, Skill and link validation
- Remote CI: inspect draft PR #1 Checks for the pushed head
- [ ] Owner review for protected areas

## Human Decisions

Maintainers review packaged resources and the additive MCP capabilities before
integration. Existing project rules and conflicting configuration require
deliberate local integration; no setup operation grants model or merge authority.
