# AGENTS.md

This file gives coding agents stable instructions for this repository. Keep it
short. Put live work state in CoProgrammer Manager events, not here.

## Project Purpose

TODO: Describe what this repository does and what kind of changes are expected.

## Before Editing

- Read `.coprogrammer.json` for protected paths, owners, language, and risk
  policy.
- Prefer narrow changes that preserve existing architecture and contracts.
- Keep feature work, refactors, formatting, and dependency updates separate.
- Request or check workspace leases before touching shared areas:

```bash
coprogrammer manager lease request --holder <agent> --pattern "path/**"
```

## Expected Artifacts

- `templates/change-manifest.json` for meaningful feature work.
- `coprogrammer manager heartbeat` for active agent status.
- Branch digest for risky or broad PRs.
- Decision records for human-approved architecture, security, migration, auth,
  payment, or contract decisions.

## Validation

TODO: List the fastest reliable checks for this repository.

Example:

```bash
python -m unittest discover -s tests
coprogrammer config validate
```

## Boundaries

- Do not merge large generated branches directly.
- Do not silently rewrite shared contracts or architectural invariants.
- Do not store backlog, live status, or decisions in this file.
