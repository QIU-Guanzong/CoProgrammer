# GitHub Actions Integration

CoProgrammer includes a first-pass Branch Digest workflow for pull requests.

## What It Does

On every PR open, synchronize, reopen, or ready-for-review event, the workflow:

1. checks out the PR head;
2. fetches the base branch;
3. installs the local CoProgrammer CLI;
4. generates `branch-digest.md`;
5. uploads it as a workflow artifact;
6. updates one stable PR comment for same-repository PRs.

The workflow intentionally avoids autonomous code changes. It only creates a
review artifact.

## Why Same-Repository PR Comments Only

Fork PRs often run with restricted token permissions. The digest artifact is
still generated for those PRs, but the comment step is skipped unless the PR
head repository matches the base repository.

## Local Equivalent

```bash
coprogrammer digest --base origin/main --head HEAD --output branch-digest.md
```

For uncommitted local work:

```bash
coprogrammer digest --base origin/main --working-tree --output branch-digest.md
```

## Next Improvements

- Add a risk threshold that can fail PR checks for protected contract changes.
- Read `CODEOWNERS` and protocol files directly.
- Use commit messages and manifests to prefill branch intent.
- Link digest sections back to changed files and commits.
