---
name: coprogrammer-integration-plan
description: "Turn an approved branch digest into a minimal CoProgrammer integration plan that rebuilds useful changes from latest main and records what to preserve, drop, validate, and roll back."
---

# CoProgrammer Integration Plan

Prerequisite for validating a plan: install the CoProgrammer CLI and make
`coprogrammer` available on `PATH`. Do not assume the target repository
contains CoProgrammer's Python source tree. If the CLI is unavailable, leave
the plan as an unvalidated draft and state that the check could not run.

Use this workflow after a branch digest has been reviewed and the team needs a
safe plan for integrating useful work.

## Workflow

1. Read the branch digest and any related Manager decisions.
2. Identify:
   - source branch;
   - source head;
   - latest `main` baseline;
   - objective;
   - changes to rebuild;
   - changes to drop;
   - protected areas;
   - validation commands;
   - rollback plan.
3. Prefer `templates/integration-plan.json` as the machine-readable source of
   truth and `templates/integration-plan.md` or `.zh-CN.md` for reviewer-facing
   notes.
4. Validate the JSON plan:

```bash
coprogrammer integration-plan validate <plan.json>
```

5. Recommend deterministic patch primitives before LLM patching:
   - manual;
   - git apply;
   - structural search/replace;
   - codemod or recipe;
   - LLM patch only when the intent is clear and deterministic primitives are
     insufficient.

## Output

Produce an integration plan that states:

- what to preserve;
- what to drop;
- what to rebuild from latest `main`;
- what validation must pass;
- what human decisions remain;
- how to roll back the integration patch.

Treat the source branch as evidence. The integration branch is the merge
candidate.
