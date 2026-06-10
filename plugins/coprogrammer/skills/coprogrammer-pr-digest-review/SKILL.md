---
name: coprogrammer-pr-digest-review
description: "Generate or review a CoProgrammer branch digest after coding, then classify branch content into preserve, drop, rebuild, defer, reject, validation, and human decision items."
---

# CoProgrammer PR Digest Review

Use this workflow after a branch or PR exists and a reviewer needs to understand
what should actually reach `main`.

## Workflow

1. Resolve base and head. Prefer the PR base and current branch head. If the
   user does not specify them, use `origin/main` and `HEAD` when available.
2. Generate a branch digest if one is not already supplied:

```bash
PYTHONPATH=src python -m coprogrammer digest \
  --base origin/main \
  --head HEAD \
  --language zh-CN \
  --output branch-digest.md
```

3. Read the digest, changed files, commits, protected path matches, risk level,
   and validation needs.
4. Classify content into:
   - preserve;
   - drop;
   - rebuild from latest `main`;
   - defer to later task;
   - reject;
   - human decision required.
5. Check for missing artifacts:
   - change manifest;
   - compatibility note;
   - owner review;
   - validation evidence;
   - integration plan.

## Output

Lead with the integration decision summary, not a raw diff summary. Make clear
which branch insights should survive and which code should not merge as-is.

Do not approve protected path, contract, auth, payment, migration, or
architecture changes without explicit human review.
