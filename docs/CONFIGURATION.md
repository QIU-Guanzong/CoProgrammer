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
