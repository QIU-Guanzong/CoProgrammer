---
name: coprogrammer-task-brief
description: "Convert a human request into a scoped CoProgrammer task brief with intent, allowed paths, forbidden paths, shared contracts, validation, and handoff notes before an agent edits code."
---

# CoProgrammer Task Brief

Use this workflow before assigning coding work to a human or AI agent.

## Workflow

1. Read the user's request and identify:
   - goal;
   - likely files or modules;
   - forbidden/protected paths;
   - shared contracts that may change;
   - validation commands.
2. Read `.coprogrammer.json` for protected paths and model routing.
3. Prefer `templates/task-brief.md` or `templates/task-brief.zh-CN.md` when
   the repository provides them.
4. If scope is uncertain, inspect the codebase with `rg --files` and focused
   reads before drafting.
5. If implementation should begin immediately, request a workspace lease first:

```bash
PYTHONPATH=src python -m coprogrammer manager lease request \
  --holder <agent-or-user> \
  --pattern "<path-or-glob>"
```

## Output

Produce a concise task brief with:

- problem;
- expected outcome;
- allowed paths;
- forbidden paths;
- shared contracts;
- validation commands;
- handoff notes.

Do not make the task brief broad enough to authorize unrelated refactors,
format-only churn, dependency upgrades, or architecture rewrites.
