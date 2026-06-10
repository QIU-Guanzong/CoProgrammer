# CoProgrammer Plugin Quickstart

This repository includes a repo-local Codex plugin at
`plugins/coprogrammer`.

The plugin packages the CoProgrammer lifecycle into five skills:

| Skill | When to Use |
| --- | --- |
| `coprogrammer-project-covenant` | Audit or create the before-coding covenant pack. |
| `coprogrammer-task-brief` | Turn a request into a scoped task brief before editing. |
| `coprogrammer-active-sync` | Coordinate active work with Manager status, leases, heartbeats, contracts, and decisions. |
| `coprogrammer-pr-digest-review` | Review a branch digest and classify preserve/drop/rebuild/defer decisions. |
| `coprogrammer-integration-plan` | Convert an approved digest into a minimal integration plan. |

## Install

From this repository root:

```bash
codex plugin marketplace add /Users/c-gavin.yau/Downloads/Claude开发/CoProgrammer
codex plugin add coprogrammer@personal
```

Confirm installation:

```bash
codex plugin list | rg coprogrammer
```

Expected status:

```text
coprogrammer@personal  installed, enabled  0.1.0
```

Start a new Codex thread after installation so the plugin skills appear in the
available skill list.

## Example Prompts

```text
Use $coprogrammer-project-covenant to audit this repo.
```

```text
Use $coprogrammer-task-brief to scope this feature before coding.
```

```text
Use $coprogrammer-active-sync to check current Manager state and request a lease.
```

```text
Use $coprogrammer-pr-digest-review to review this PR before merge.
```

```text
Use $coprogrammer-integration-plan to draft the minimal integration plan.
```

## Validate

Plugin validation:

```bash
python3 /Users/c-gavin.yau/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  /Users/c-gavin.yau/Downloads/Claude开发/CoProgrammer/plugins/coprogrammer
```

Repository validation:

```bash
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m coprogrammer config validate
PYTHONPATH=src python -m coprogrammer agents check
```
