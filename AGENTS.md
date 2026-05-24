# AGENTS.md

This file gives coding agents stable instructions for this repository. Keep it
short. Live coordination state belongs in `.coprogrammer/events.jsonl`, not in
this file.

## Project Purpose

CoProgrammer is an open protocol and toolkit for semantic integration in
multi-agent software development. It focuses on branch digestion, Manager Plane
state, workspace leases, decision records, and safe integration artifacts.

## Before Editing

- Read `.coprogrammer.json` for protected paths and default language.
- Prefer `rg` and `rg --files` for repository search.
- Keep feature changes, refactors, formatting, and dependency updates separate.
- If multiple agents may touch the same area, request a lease first:

```bash
python -m coprogrammer manager lease request --holder <agent> --pattern "path/**"
```

## Expected Artifacts

- Use `templates/change-manifest.json` for meaningful feature changes.
- Use `templates/agent-heartbeat.json` or `coprogrammer manager heartbeat` for
  active agent work.
- Use branch digests for PRs that touch protected paths, contracts, or broad
  architecture.
- Record human decisions with `coprogrammer manager decision record`.

## Validation

Run the focused check for your change. For broad changes, run:

```bash
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m coprogrammer config validate
```

For research or schema changes, also validate JSON/YAML files.

## Boundaries

- Do not directly merge noisy AI-generated branches.
- Do not auto-approve architecture, security, auth, payment, migration, or
  contract changes.
- Do not use this file as a backlog, status board, or decision log.
