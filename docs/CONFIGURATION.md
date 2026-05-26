# Configuration

CoProgrammer reads project policy from `.coprogrammer.json`.

The config turns team protocol into machine-readable rules for digest
generation. It is intentionally JSON so the first version can stay dependency
free.

## Example

```json
{
  "$schema": "./schemas/coprogrammer-config.schema.json",
  "language": "zh-CN",
  "risk_level_by_category": {
    "contract": "medium",
    "database": "high",
    "security": "high",
    "build": "medium",
    "architecture": "medium"
  },
  "model_routing": {
    "simple_work_model": "codex-5.3",
    "default_model": "codex-default",
    "high_risk_model": "maintainer-approved",
    "simple_work_allowed": [
      "documentation polish",
      "research lead triage"
    ],
    "requires_human_review": [
      "schemas/**",
      "protocols/**",
      "integration patch application"
    ]
  },
  "protected_paths": [
    {
      "pattern": "schemas/**",
      "risk": "high",
      "reason": "machine-readable artifact contract changes",
      "owner_review": true
    }
  ]
}
```

## Validate Config

```bash
coprogrammer config validate
coprogrammer config validate path/to/config.json
```

## Protected Paths

Each protected path rule has:

- `pattern`: a glob-style path pattern;
- `risk`: `low`, `medium`, `high`, or `critical`;
- `reason`: why the path is protected;
- `owner_review`: whether reviewer ownership should be called out.

## Risk Scoring

Digest risk is the highest level detected from:

- first-pass risk categories such as `security`, `database`, and `contract`;
- matched protected paths.

Risk scoring does not block merges yet. It makes review pressure visible. Later
versions can turn high-risk findings into required checks.

## Model Routing

`model_routing` documents which model tier can handle each class of work.

- `simple_work_model`: low-risk work model label, configured here as
  `codex-5.3`;
- `default_model`: normal work label;
- `high_risk_model`: high-risk routing label, usually meaning maintainer
  approval or stronger review;
- `simple_work_allowed`: examples safe for simple-work routing;
- `requires_human_review`: patterns or work classes that must not be delegated
  to simple-work routing.

See `docs/MODEL_ROUTING_POLICY.md`.
