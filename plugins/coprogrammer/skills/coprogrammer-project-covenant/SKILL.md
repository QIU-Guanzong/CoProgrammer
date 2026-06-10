---
name: coprogrammer-project-covenant
description: "Audit or create the before-coding CoProgrammer covenant pack for a repository, including AGENTS.md, .coprogrammer.json, CODEOWNERS, protocols, protected paths, and validation commands."
---

# CoProgrammer Project Covenant

Use this workflow when a user wants a repository prepared for AI-assisted
multi-agent development before implementation begins.

## Workflow

1. Inspect the repository root and confirm whether these files exist:
   - `AGENTS.md`
   - `.coprogrammer.json`
   - `CODEOWNERS`
   - `protocols/main-branch-constitution.md`
   - `protocols/agent-workspace-contract.md`
   - `templates/task-brief.md`
2. Read `docs/COORDINATION_LIFECYCLE.md` if it exists.
3. Run available checks from the repo root:

```bash
PYTHONPATH=src python -m coprogrammer config validate
PYTHONPATH=src python -m coprogrammer agents check
```

4. Report missing or weak covenant pieces in three groups:
   - must fix before multi-agent work;
   - useful but not blocking;
   - later automation.
5. If the user asks you to fix the repo, make narrow edits using existing
   templates and preserve local conventions.

## Output

End with a short readiness summary:

- `ready`: all required covenant artifacts exist and checks pass;
- `partial`: enough exists for careful work, but gaps remain;
- `blocked`: protected paths, ownership, or validation are unclear enough that
  multi-agent coding would be unsafe.
