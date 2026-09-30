# Task brief: Skills, MCP and Markdown

Requested outcome: make collaboration capabilities usable through Skills, MCP
and Markdown, with a practical project onboarding path.

Scope: package the existing five Skills plus a setup workflow; expose a curated
knowledge catalog; generate native per-client previews and create missing
project files; add MCP resources/prompts; document and verify source and wheel
behavior. Preserve current scheduling and message semantics.

Allowed areas: knowledge/setup modules, CLI/MCP integration, package data,
plugin metadata and the new Skill, focused tests, README and this documentation.
No global installation/configuration, arbitrary external skill execution,
provider calls, unrelated refactor, auto-merge or package release.

Validation: source and isolated-wheel suites; curated resource whitelist;
existing-file preservation and no-secret preview; concurrent setup and write
failure handling; real stdio tools/resources/prompts; supported protocol
versions; generated-client configuration launch; artifact checks; documentation
links and GitHub Ubuntu/Windows matrix.

Packaging and MCP capability changes remain in draft PR #1 for maintainer
review. Setup writes only when explicitly applied; successful file creation
does not prove client connection or model invocation.
