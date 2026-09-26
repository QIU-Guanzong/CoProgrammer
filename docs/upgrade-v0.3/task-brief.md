# Upgrade v0.3 Task Brief

## Problem

The five CoProgrammer workflows are currently distributed through a Codex-specific
manifest. Claude Code has no repository marketplace entry, and the skills call
`PYTHONPATH=src`, which assumes the consumer is running inside this repository.
Recent client support for the open Agent Plugins package format creates a way to
share the same skills without maintaining a separate copy per client.

## Expected outcome

- Publish the existing skills as an Agent Plugins 1.0 package.
- Add native Claude Code and Codex marketplace entries for the same package.
- Make skill command examples use the installed `coprogrammer` CLI and state
  that prerequisite clearly.
- Update installation and distribution guidance, including a source-backed
  research note on gstack-style content-bound evidence.
- Keep MCP, model-provider calls, GitHub permissions, and external publishing
  outside this packaging change.

## Allowed paths

- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`
- `plugins/coprogrammer/**`
- `docs/PLUGIN_QUICKSTART.md`
- `docs/DISTRIBUTION_STRATEGY.md`
- `docs/RESEARCH_UPDATE_2026-09-27.md`
- `docs/upgrade-v0.3/**`
- `README.md` documentation index
- `tests/test_plugin_package.py`

## Forbidden paths

- `schemas/**`, `protocols/**`, `.github/workflows/**`, `pyproject.toml`, and
  runtime source code
- Global Codex/Claude settings, API credentials, and provider endpoints
- PyPI/MCP Registry/Anthropic directory submissions, GitHub releases, merges,
  and production publication

## Shared contracts

- Agent Plugins 1.0.0 manifest and MCP configuration schemas; this package is
  skills-only, so no MCP configuration is added.
- Claude Code plugin and marketplace manifests, with matching marketplace and
  plugin identifiers.
- Codex repo marketplace catalog with a local, repository-contained source.
- Existing Codex compatibility manifest remains available.
- No runtime API, event, or protocol contract changes.

## Validation

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m coprogrammer config validate
PYTHONPATH=src python3 -m coprogrammer manifest validate docs/upgrade-v0.3/change-manifest.json
claude plugin validate .
claude plugin validate ./plugins/coprogrammer
```

Run the Claude validator only when its CLI is available. Validate JSON syntax
and repository-local marketplace paths in all environments.

## Handoff

This increment improves installability and documents the next trust milestone.
It does not publish a release, bundle the CoProgrammer CLI/MCP server, or verify
live provider calls. Content-fingerprint evidence remains a follow-up design
because it would affect protected evidence contracts and needs maintainer review.
