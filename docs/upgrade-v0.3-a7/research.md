# Implementation references

The [a6 comparison](../upgrade-v0.3-a6/research.md) identified gstack's registered
installation refreshes, Beads' local state separation and MCP Agent Mail's
session/inbox/reservation macros. This slice applies those patterns to explicit
startup and bounded foreground processing over CoProgrammer's existing APIs,
without adding another task store, inbox, daemon or dependency.

[OpenClaw's MCP CLI source](https://github.com/openclaw/openclaw/blob/main/src/cli/mcp-cli.ts)
and [official MCP CLI documentation](https://docs.openclaw.ai/cli/mcp) distinguish
config inventory from live capability probing. Inspection of the installed
native CLI's config validator confirms its JSON output includes the validated
profile path. Require that path to match the generated isolated profile before
discovery. An explicitly selected native executable preserves a separately
managed launcher rather than silently changing it.

This choice responds to a live observation: the default executable had become
a service proxy while the original native CLI remained installed. The proxy's
validation/probe ignored local profile environment variables. Native local
verification passed with explicit CLI selection. This does not prove managed
service compatibility or model access and is not a reason to alter its accounts
or production configuration.
