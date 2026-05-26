# Model Routing Policy

Last updated: 2026-05-26

## Goal

CoProgrammer should route work by risk, not by habit.

Simple work can use the configured low-cost/simple-work model. In this
repository, that label is:

```json
"simple_work_model": "codex-5.3"
```

This is a team configuration label, not a claim that every deployment has the
same model name.

## Routing Table

| Work Type | Allowed Model Tier | Human Review |
| --- | --- | --- |
| Documentation polish | `simple_work_model` | Usually optional |
| Research lead triage | `simple_work_model` | Optional unless it changes roadmap |
| Low-risk template updates | `simple_work_model` | Optional |
| Format-only changes | `simple_work_model` | Optional after validation |
| Local validation and summaries | `simple_work_model` | Optional |
| Branch digest generation | default model or deterministic tooling | Required for high-risk findings |
| Schema/protocol changes | default or high-risk model | Required |
| Contract board changes | default or high-risk model | Required for breaking changes |
| Security/auth/payment behavior | high-risk model plus maintainer | Required |
| Database migrations | high-risk model plus maintainer | Required |
| Integration patch application | high-risk model plus maintainer | Required |

## Policy

Use `codex-5.3` for simple work when:

- the diff is narrow;
- no protected path is touched;
- no contract/schema/API behavior changes;
- no integration patch is being applied;
- validation is cheap and available.

Do not use simple-work routing for:

- `schemas/**`;
- `protocols/**`;
- auth, payment, permissions, secrets, or security behavior;
- database migrations;
- breaking contract changes;
- generated integration patches;
- branch deletion, history rewrite, or destructive Git actions.

## Config

The policy lives in `.coprogrammer.json`:

```json
{
  "model_routing": {
    "simple_work_model": "codex-5.3",
    "default_model": "codex-default",
    "high_risk_model": "maintainer-approved",
    "simple_work_allowed": [
      "documentation polish",
      "research lead triage",
      "low-risk template updates",
      "format-only changes",
      "local validation and summaries"
    ],
    "requires_human_review": [
      "schemas/**",
      "protocols/**",
      "security/auth/payment behavior",
      "database migrations",
      "integration patch application"
    ]
  }
}
```

## Product Implication

Model routing should become part of Manager Plane policy:

- branch digest can report suggested model tier;
- contract board can force high-risk routing for breaking changes;
- integration plan can declare the model tier used for patch attempts;
- decision records can capture human override when routing is ambiguous.

The rule is simple: cheap models are fine for cheap mistakes. Expensive mistakes
need stronger models, structured validation, and human decisions.
