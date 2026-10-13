# Validation scope

Run focused integration/setup/provider tests, then the full source suite and
independently installed-wheel suite. Check config/JSON/YAML, matching Skills,
native plugin metadata and changed Markdown links. Require four Ubuntu/Windows
Python 3.10/3.13 CI jobs. After release, read back the exact PyPI version,
verify artifact hashes/content, install into a fresh environment, and exercise
the demo, all new setup profiles, real MCP discovery and Grok offline preview.

Fixtures and local processes establish adapter behavior. They do not establish
OpenClaw node pairing, WorkBuddy GUI connector discovery, native harness hooks,
live model connectivity, provider authorization or distributed coordination.
