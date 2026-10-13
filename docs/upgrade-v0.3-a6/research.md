# Related open-source projects and implementation choices

Primary sources reviewed on 2026-10-13. These describe the upstream source
observed on that date; they do not establish compatibility with a future version.
No upstream implementation was copied or added as a dependency.

| Project and source | Observed pattern | Choice for CoProgrammer |
| --- | --- | --- |
| [gstack setup](https://github.com/garrytan/gstack/blob/main/setup) | Host-specific installation, registered install refreshes, team updates and read-only status | Add explicit refreshes for generated project files with matching local hashes. Preserve independent project/client ownership; do not introduce silent package downloads or global updates. |
| [Beads initialization](https://github.com/gastownhall/beads/blob/main/cmd/bd/init.go) | Personal/stealth setup separates local planning state from source commits, including repository-local excludes | Keep setup receipts in local runtime state rather than project instructions. Keep ignore changes explicit; no new database or cross-machine state sync. |
| [MCP Agent Mail workflow](https://github.com/Dicklesworthstone/mcp_agent_mail/blob/main/SKILL.md) | Session bootstrap macros combine identity, reservations and inbox, with explicit message receipts | Preserve existing `start`, `worker step`, `worker finish` and explicit ACK flow; improve installation maintenance instead of adding a second inbox or implicit receipt policy. |

The installed-user problem is concrete: after a generated Skill changes or a
Python/package/project path moves, missing-only setup reports old generated
files as conflicts. A package upgrade alone cannot refresh them. A local hash
receipt distinguishes unchanged generated files from customization, while
preview plus explicit application keeps the operation reviewable.

This release does not claim more stars, independent-user adoption, productivity
improvement, real autonomous model execution, universal client auto-discovery
or network-shared leases. WorkBuddy UI work remains deferred by the user.
