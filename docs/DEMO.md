# Try the coordination workflow offline

Run a complete, checked example without API keys or a project to configure:

```bash
coprogrammer demo
coprogrammer demo --json
```

From a source checkout, use `PYTHONPATH=src python -m coprogrammer demo`.
Python 3.10+ and Git 2.36+ are required. Git 2.36 introduced the NUL-delimited
worktree listing used by shared-state discovery ([release notes](https://github.com/git/git/blob/master/Documentation/RelNotes/2.36.0.adoc)). The command works
outside a Git repository and does not need an internet connection.

The demo creates a temporary Git repository and two linked worktrees. It runs
the same collaboration and scheduler APIs exposed by the CLI and MCP server,
and verifies every reported outcome against real Manager events.

| Step | What you can observe |
| --- | --- |
| Worktrees | Separate `demo/codex` and `demo/claude` branches discover one shared Manager log. |
| Sessions | Two local session records identify the participating worktrees. |
| Dependencies | The documentation task cannot be claimed before its API dependency finishes. |
| Claim | The API task receives an active path lease and a claim token bound to its worktree and branch. |
| Guard | `src/api.py` passes the scope check; `docs/api.md` is rejected for this claim. |
| Conflict | An independent review task cannot claim an overlapping path from the other worktree. |
| Handoff | A message persists in the recipient inbox; reading it does not acknowledge it, and retrying it creates no duplicate. |
| Acknowledgement | An explicit recipient ACK clears the pending message. |
| Completion | Finishing the API task releases its lease. Claude can then claim, guard and finish the documentation and review tasks. |

Each expected refusal is also checked for unintended event-log writes. If a
check fails or Git or a Manager API returns an unexpected error, the command
fails instead of presenting a successful tour. The JSON output includes the
observed branch names, claim and lease IDs, rejection reasons, message ID,
final task counts and cleanup result. IDs, commit hashes and timestamps vary
between runs; the verified workflow is repeatable.

All repositories, worktrees and events are deleted before the command returns,
including after a failure. Git configuration and environment overrides are
isolated in a child process. The command does not edit the current project,
modify global Git configuration, connect to a remote or install a client.

The Codex and Claude names are local routing labels in this example. No Codex
or Claude session is connected and no model is called. Leases and guards are
cooperative checks, not filesystem permissions. A task marked done and a
message marked acknowledged do not approve, merge or validate application code.

After the tour, follow the [quick start](MULTI_PLATFORM_QUICKSTART.md) to use the same workflow
in your project, or inspect [client setup](knowledge/README.md) before applying
any generated configuration.
