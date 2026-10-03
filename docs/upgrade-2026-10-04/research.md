# Sources and choices — 2026-10-04

- [gstack ship](https://github.com/garrytan/gstack/blob/main/ship/SKILL.md)
  binds checks to consumed content and command, and distinguishes stale or
  missing evidence from a successful run. CoProgrammer will hash supported
  working content and exact command arguments, without storing command output
  or arguments. HEAD alone cannot establish freshness. This is a local receipt,
  not an authenticated review or complete dependency capture.
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) documents
  per-worker worktree isolation and the importance of the actual working
  directory. Dispatch will use the registered session's real checkout and
  occupied worktree, with claim-time checks still authoritative.
- [MCP tools, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
  defines tool annotations and structured results. Add bounded read-only tools
  through the existing negotiated stdio server; expose no arbitrary command
  execution or new transport. Existing compatibility behavior is retained.

The practical missing link between computers is a portable, inspectable context
artifact. This increment compares it explicitly against the receiving clone;
it does not claim a globally shared lease or automatically import Manager state.

Windows CI exposed a pre-lock bootstrap write failure in the existing Manager.
[Microsoft's `_locking` reference](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170)
documents locking beyond end-of-file. Empty lock files therefore need no seed
byte; removing that write prevents a contender from touching a locked range.
The new regression uses real process contention on an initially empty file.

Concurrent Windows installers also exposed path-resolution mismatches on the
Manager lock. [Python's stat attributes](https://docs.python.org/3.10/library/os.html#os.stat_result.st_file_attributes)
and [reparse-point flag](https://docs.python.org/3.10/library/stat.html#stat.FILE_ATTRIBUTE_REPARSE_POINT)
support checking each path component with non-following metadata. Setup now
rejects symlinks and Windows reparse points without resolving a locked file.
