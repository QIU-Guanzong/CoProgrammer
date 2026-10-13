# More AI runtimes, one coordination workflow

Available in **0.3.0a4+**, with native installation/verification updates in
**0.3.0a5**: see [the current native workflow](NATIVE_RUNTIME_WORKFLOW.md).
CoProgrammer coordinates tasks, file boundaries and
handoffs. Your chosen runtime owns the model, editing tools and execution loop.
An agent harness can call the CLI at work boundaries or expose the same workflow
through MCP; it does not need a separate scheduler implementation.

## Choose the right adapter

| Runtime | Skill installation | MCP installation | What is verified |
| --- | --- | --- | --- |
| Codex / Claude Code / Copilot | Existing project directories | Existing native project config | Generated config starts the packaged stdio server |
| OpenClaw | `skills/` in the selected agent workspace | `.coprogrammer-kit/openclaw/mcp.json`, using `nodeHost.mcp.servers` | Workspace Skill format and real stdio server startup; node pairing is not tested |
| WorkBuddy a5+ | Project `.codebuddy/skills/` | Project `.workbuddy/mcp.json` | Documented native paths and real stdio startup; desktop GUI discovery remains unverified |
| Agent harness | Import `.coprogrammer-kit/harness/skills/`, or use CLI | Import `.coprogrammer-kit/harness/mcp.json` | Generic CLI/MCP compatibility; no product-specific harness API |
| Other runtimes | Import `.coprogrammer-kit/generic/skills/`, or use CLI | Import `.coprogrammer-kit/generic/mcp.json` | Generic CLI/MCP compatibility |
| Grok / xAI | Run in a compatible host, registering `--provider grok` | The host connects to CoProgrammer; the model API is separate | Responses API request and response handling with fixtures; no live account call |

Each kit contains the same six Skills. `full` also includes Markdown project
guidance and the MCP recipe; `skills` omits MCP; `mcp` contains only the recipe.
Imported recipes have machine-specific paths. Generate them separately in each
worktree and again after moving Python, the package or the project. A remote node
needs its own local installation and paths.

## Install and preview

Use a virtual environment, then run inside the target project:

```sh
python -m pip install --pre --upgrade coprogrammer
coprogrammer integrations list
coprogrammer setup --client openclaw --edition full --include-content
coprogrammer setup --client workbuddy --edition full --include-content
coprogrammer setup --client harness --edition mcp --include-content
```

Review the plan for the chosen client, then repeat it with `--apply`. Existing
instructions are preserved. A different config, Skill or generated guide is a
conflict: no force overwrite or silent merge. The report's `activation` field
explains which files are automatically discovered and which require import.
Decide how to commit or ignore generated files before claiming a narrow task;
the edit guard includes unrelated untracked files too.

### OpenClaw

Select the project as the agent's actual workspace so its workspace `skills/`
can be discovered. For MCP on a paired local node, merge only the
`nodeHost.mcp.servers.coprogrammer` entry into that node's active `openclaw.json`,
preserving other configuration. The kit does not edit that file. Restart the
node, then check that CoProgrammer tools are published and callable. Workspace
Skills and node-hosted Skills have different discovery locations: this installer
does not modify `~/.openclaw/skills` or a global OpenClaw profile.

Follow the official [workspace Skills](https://docs.openclaw.ai/skills) and
[node MCP instructions](https://docs.openclaw.ai/nodes/mcp-and-skills) for the
installed version. If the runtime cannot access the repository and its local
Python, use a local agent/node or an explicit portable handoff. This package
serves stdio, not a remote HTTP endpoint.

### WorkBuddy

With a5+, setup writes the documented `.codebuddy/skills/` and `.workbuddy/mcp.json`
project files. Existing a4 import kits remain untouched. Preserve existing
connectors and complete WorkBuddy's normal trust/reload flow; then call
`workspace_status` and confirm it reports the intended worktree. See the
[current native steps and evidence](NATIVE_RUNTIME_WORKFLOW.md).

The official [plugin guide](https://www.codebuddy.cn/docs/workbuddy/Plugins)
documents Skill and MCP extensions. Desktop, CodeBuddy IDE and CodeBuddy Code
have different configuration surfaces; use the one offered by your installation.
The [WorkBuddy changelog](https://www.codebuddy.cn/docs/workbuddy/Changelog)
also documents Skill ecosystem compatibility. This release does not configure
WorkBuddy's cloud or sandbox bridge.

### Agent harness

`--client harness` is a generic runtime identity. Import the MCP recipe into your
runtime's documented MCP interface, or call the CLI from its work loop. No
particular Harness product, daemon or window-control API is assumed.

## Connect the work loop

Start each participating window in its own committed, named Git worktree:

```sh
coprogrammer start --client openclaw --session claw-api
# In another worktree:
coprogrammer start --client workbuddy --session buddy-docs
# In a third worktree, already configured to use Grok:
coprogrammer start --client harness --provider grok --session harness-review
```

The provider is a declared routing label. It neither changes accounts nor verifies
model access. A task's existing client filter can match `openclaw`, `workbuddy`,
`harness`, `generic`, or a declared provider such as `grok`.

Follow the [queue and work-boundary guide](AUTOMATIC_COLLABORATION.md) to create
tasks and dependencies. At each work boundary, the harness calls:

```sh
coprogrammer worker step --session claw-api
coprogrammer worker step --session claw-api --apply
```

The second call pulses activity, inspects messages/decisions, claims eligible
work or guards and renews the current claim. A participating agent edits only
after the result permits it. Pending messages pause work; read and explicitly
acknowledge them before continuing. Finish using the returned task/claim IDs:

```sh
coprogrammer worker finish --session claw-api --id TASK_ID --claim CLAIM_ID \
  --summary 'API change tested; documentation can proceed' --notify buddy-docs
```

MCP equivalents are `worker_step` and `worker_finish`. Handoffs enter the local
recipient inbox; they do not send platform chat messages or wake a window.
Choose and implement any runtime-specific boundary hook in the harness itself;
this release does not install unattended hooks, run a daemon or auto-ACK.

Same-repository worktrees on one machine share a Manager log. Independent clones
and other computers do not share live leases or messaging; use
[portable handoffs](WORKSPACE_HANDOFF.md). Leases are cooperative checks, not
filesystem permissions.

## Ask Grok to review a committed change

This is a separate, explicit model-review adapter. It uses xAI's
[Responses API](https://docs.x.ai/developers/rest-api-reference/inference/responses),
with an explicit model available to your account, a bounded output and
`store: false`. That flag disables conversation retrieval storage; it is not a
promise about provider logging or retention. No model tools are supplied or run.

```sh
coprogrammer review --provider grok --model YOUR_ACCOUNT_MODEL \
  --base origin/main --head HEAD --output .coprogrammer/grok-preview.json
```

Preview is offline and contains the actual diff/request for inspection. Only
`--send` makes a potentially billable call, reading `XAI_API_KEY` from the process
environment. After inspecting the preview and setting your existing account key,
use a new output path:

```sh
coprogrammer review --provider grok --model YOUR_ACCOUNT_MODEL \
  --base origin/main --head HEAD --send --output .coprogrammer/grok-review.json
```

The adapter does not retry, follow redirects, execute returned commands or
approve code. Incomplete, pending, failed or malformed output cannot become an
accepted review. Compare a valid advisory result with other reviews through
`review-summary`. `doctor` reports only executable/key presence and installation
profiles; these are not connection or account-authentication checks.
