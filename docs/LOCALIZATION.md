# Localization

CoProgrammer supports English and Simplified Chinese for user-facing digest
output.

## Supported Languages

- `en`
- `zh-CN`

Aliases such as `zh`, `zh_CN`, and `cn` resolve to `zh-CN`.

## CLI Usage

```bash
coprogrammer digest --base origin/main --head HEAD --language zh-CN
coprogrammer digest --base origin/main --working-tree --language en
coprogrammer github-comment --file branch-digest.md --language zh-CN
```

You can also set an environment variable:

```bash
export COPROGRAMMER_LANGUAGE=zh-CN
coprogrammer digest --base origin/main --head HEAD
```

If no CLI flag or environment variable is set, `coprogrammer digest` uses the
`language` value from `.coprogrammer.json`.

## GitHub Actions

The PR digest workflow reads the repository variable
`COPROGRAMMER_LANGUAGE`.

If the variable is not set, the workflow defaults to `zh-CN` so Chinese teams
can read PR digest comments directly.

To switch a repository back to English, set:

```text
COPROGRAMMER_LANGUAGE=en
```

## Human Templates

English templates remain the default filenames. Chinese versions use the
`.zh-CN` suffix:

- `templates/task-brief.zh-CN.md`
- `templates/branch-digest.zh-CN.md`
- `templates/integration-plan.zh-CN.md`
