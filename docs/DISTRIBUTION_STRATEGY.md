# Distribution Strategy

Last updated: 2026-09-27

CoProgrammer coordinates work products across coding runtimes. It should not
become another coding runtime or a universal model gateway. Keep the shared
protocol and artifacts small, and adapt installation to each client.

## Current channels

| Channel | Current state | What it provides | Boundary |
| --- | --- | --- | --- |
| Agent Skills | Five skills in an Agent Plugins 1.0 package at `plugins/coprogrammer/` | Portable instructions for readiness, task scoping, coordination, review and integration planning | CLI commands require the separately installed `coprogrammer` executable |
| Claude Code plugin | Native plugin manifest plus a repository marketplace entry | Install the same five skills as one named plugin | Third-party marketplace; no hooks or MCP server are bundled |
| Codex plugin | Agent Plugins package, `.codex-plugin/plugin.json` compatibility manifest and `.agents/plugins/marketplace.json` repo catalog | Install the five skills from the Codex Plugins Directory | CLI registers the catalog; the client UI performs installation |
| GitHub Copilot | The portable package can be used on Agent Plugins-compatible Copilot surfaces | Shared Skills package; GitHub remains the PR and review system | Copilot surface support and setup differ; use GitHub's current client docs |
| PyPI CLI and MCP | PyPI `0.1.0` is published; this branch uses `0.2.0a1` | Stable CLI and stdio MCP exist; the current branch adds newer Manager, integration and review-summary commands | The published version does not contain every command used by these skills; install the matching checkout for this branch. No hosted MCP endpoint is verified |
| GitHub Action | Root `action.yml` and PR digest workflow | Reviewable digest artifact and same-repository PR comment | Pin a reviewed full commit SHA when consuming it; fork jobs must retain least privilege |
| Claude API, GLM, DeepSeek | Optional provider adapters exist | Explicit second-opinion review of selected evidence | Tests use mocked HTTP; live credentials, provider availability and billing are unverified |

## Architecture decision

Keep five layers distinct:

1. **Coding runtimes** create branches and edits: Codex, Claude Code, Copilot,
   and other local or hosted coding agents.
2. **Skills** teach repeatable workflows without owning state or authority.
3. **CLI and MCP** expose local coordination state and controlled commands.
4. **Model providers** supply optional analysis; Claude API, GLM and DeepSeek are
   providers, not substitutes for the coding runtimes.
5. **GitHub** remains the canonical place for pull requests, checks, reviews
   and maintainer decisions.

The portable Agent Plugins 1.0 package carries only the Skills component. The
same package includes client metadata for Codex, while Claude Code uses its own
native manifest and marketplace catalog. This avoids duplicating the workflow
instructions while respecting client-specific installation formats. MCP is
kept separate until the current CLI feature set has a stable distributable
package and the connection can be validated in supported clients. PyPI has a
stable `0.1.0`, but it predates commands added by the current `0.2.0a1` branch.

## Design lessons from open-source projects

The current gstack project ties review receipts and test evidence to a content
fingerprint of the working tree, rather than relying only on a commit SHA. That
can keep evidence current through amend, rebase and squash operations. Its
documented review receipt still relies on a reviewer's reported completion; a
fingerprint establishes which content the receipt names, not that a reviewer
independently understood it. CoProgrammer should adopt the content-identity and
freshness idea while keeping review claims appropriately limited.

The Agent Plugins standard shows a useful open-source boundary: standardize
only the component formats with cross-client convergence (Skills and MCP), and
leave hooks and other runtime behavior in client-owned extensions. Claude's
marketplace further separates a plugin catalog from the plugin package itself.
We follow that split instead of forcing Claude's manifest into the portable
manifest.

For GitHub automation, keep permissions minimal and treat fork content as
untrusted input. A digest or review summary should be generated without a
write-capable token where possible. Do not run code from an untrusted pull
request in a privileged `pull_request_target` or `workflow_run` path.

## Prioritized roadmap

### Done in this increment

- Add a portable Agent Plugins 1.0 manifest and retain the Codex compatibility
  manifest.
- Add a Claude Code plugin manifest and repository marketplace listing.
- Make packaged skills stop assuming that the consumer repository contains
  CoProgrammer's `src/` tree.
- Document the separate CLI prerequisite and the research boundaries.

### Next: stable local distribution

- Publish and verify the current `0.2.0a1` feature set before recommending
  `uvx` or `pipx` for the new Manager and review-summary commands. The existing
  PyPI `0.1.0` remains an older stable install path.
- Add a packaged MCP configuration only after the CLI launch command is
  deterministic on supported platforms and has been exercised in each client.
- Consider MCP Registry publication only after the package and namespace are
  independently verified. Do not use a preview branch as a distribution ref.

### Then: evidence freshness

- Propose a content fingerprint over the exact files reviewed and tested.
- Record command, tool version, timestamp, content identity and result in a
  reviewable receipt.
- Report evidence as fresh, stale or unverifiable; do not turn a receipt into
  approval or merge authority.
- Keep this schema/protocol change behind maintainer review and a pilot across
  real rebases, amendments, untracked files and ignored scratch files.

### Later: GitHub and provider evaluation

- Surface review summaries in GitHub Actions job summaries and downloadable
  artifacts before adding PR writes or an App.
- Keep fork-triggered jobs free of model credentials and write tokens.
- Compare provider adapters on the same bounded input and rubric; report
  mocked, live and unavailable states separately.
- Add opt-in adoption telemetry only if users can inspect, disable and delete
  what is collected. Default behavior remains local and quiet.

## Sources

- [Agent Plugins Specification 1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md)
- [OpenAI: Package your plugin](https://developers.openai.com/plugins/build/plugins)
- [GitHub Copilot: About plugins](https://docs.github.com/en/copilot/concepts/agents/about-plugins)
- [Claude Code: Plugins overview](https://code.claude.com/docs/en/plugins)
- [Claude Code: Create a marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [GitHub Actions: Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [gstack README](https://github.com/garrytan/gstack)
- [gstack ship workflow and verification gate](https://github.com/garrytan/gstack/blob/main/ship/SKILL.md)
