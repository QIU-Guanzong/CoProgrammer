# MVP Design

## MVP Name

Branch Digest Bot

## Primary User

A reviewer who receives a large AI-generated feature branch and needs to decide
what is worth integrating into main.

## User Story

As a reviewer, I want an AI-assisted branch digest so that I can evaluate
intent, risk, and integration strategy without reading every noisy generated
change first.

## Scope

The MVP should:

- read changed files and commits;
- detect contract-sensitive paths;
- load project policy from `.coprogrammer.json`;
- score branch risk;
- generate a digest draft;
- publish the digest as a PR artifact and stable PR comment;
- require humans to fill in branch intent and integration decisions;
- run as a local CLI and later as GitHub Actions.

The MVP should not:

- auto-merge;
- rewrite code autonomously;
- replace CI;
- approve protected file changes without owners.

## CLI Commands

```bash
coprogrammer digest --base origin/main --head HEAD
coprogrammer digest --base origin/main --head HEAD --language zh-CN
coprogrammer digest --base origin/main --working-tree
coprogrammer config validate
coprogrammer manifest validate path/to/change-manifest.json
coprogrammer heartbeat new --agent agent-a --task "Implement backend API"
```

## Future Bot Flow

1. On PR open, run digest.
2. Comment digest on PR.
3. Fail soft if protected paths are touched without manifest.
4. Fail hard when schema or migration changes lack owner review.
5. After approval, optionally create an integration branch.
