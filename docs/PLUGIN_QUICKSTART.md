# CoProgrammer Plugins

The five collaboration workflows are packaged under `plugins/coprogrammer/`.
That directory now has an Agent Plugins 1.0 manifest for portable clients, a
Codex compatibility manifest, and a Claude Code plugin manifest. The repository
root contains the Claude marketplace catalog.

## What is included

| Skill | Use it to |
| --- | --- |
| `coprogrammer-project-covenant` | Check project instructions and safeguards before parallel work. |
| `coprogrammer-task-brief` | Scope a request, protected paths and validation before editing. |
| `coprogrammer-active-sync` | Read Manager state and coordinate leases, heartbeats, decisions and contracts. |
| `coprogrammer-pr-digest-review` | Review a branch digest and classify what to keep, rebuild or defer. |
| `coprogrammer-integration-plan` | Turn an approved review into a minimal, still-reviewable integration plan. |

## Install in Claude Code

From a checkout that contains this marketplace (such as the upgrade branch):

```bash
claude plugin marketplace add /path/to/CoProgrammer
claude plugin install coprogrammer@coprogrammer-claude
claude plugin list
```

After the marketplace entry is merged to the default branch, it can also be
added with `claude plugin marketplace add QIU-Guanzong/CoProgrammer`.

Start a new session or reload plugins. A skill can then be invoked as, for
example, `/coprogrammer:coprogrammer-active-sync`.

## Install in Codex

From a local CoProgrammer checkout, register the repository marketplace:

```bash
codex plugin marketplace add /path/to/CoProgrammer
codex plugin marketplace list
```

Open Codex's Plugins Directory, choose `CoProgrammer for Codex`, and install
`coprogrammer`. Start a new Codex thread so the skills appear in its skill
list. For a GitHub-hosted source after this marketplace is available on the
default branch, the CLI can also register `QIU-Guanzong/CoProgrammer` directly.
The portable `plugin.json` gives Agent Plugins-compatible clients a standard
package entry point; their installation flows can differ.

## Install the CLI for Manager operations

The plugin package contains workflow instructions, not the CLI or MCP server.
PyPI currently publishes `coprogrammer 0.1.0`; it predates commands added in
this branch's `0.2.0a1` development version. To use every command referenced by
these skills, install the CLI from a matching CoProgrammer checkout in the
Python environment used by your terminal:

```bash
python -m pip install -e .
coprogrammer --help
```

The published package is listed at
[PyPI](https://pypi.org/project/coprogrammer/0.1.0/). Use the matching checkout
until a release containing the current Manager and review-summary commands is
available.

Without the CLI, skills can still guide file-based planning and review. They
must report Manager reads, lease changes, digest generation and plan validation
as unavailable when those commands could not run.

To connect a client to local Manager tools after installing the CLI, generate
its native MCP configuration and merge it into that client or repository's
configuration:

```bash
coprogrammer integrations config --client codex --output coprogrammer-client.json
```

Replace `codex` with `claude` or `copilot` for those clients. This step is
separate from plugin installation; the plugin does not start an MCP process.

## Inspect and validate

The Claude Code validator checks both the repository marketplace and its
contained plugin:

```bash
claude plugin validate .
claude plugin validate ./plugins/coprogrammer
```

Review the plugin contents before installation. This release bundles skills
only: it has no hooks, background monitors, MCP server, model credentials or
provider network calls. The instructions may ask the client to run the
CoProgrammer CLI when you invoke a relevant workflow.
