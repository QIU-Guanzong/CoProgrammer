# Localization

CoProgrammer supports English and Simplified Chinese for user-facing digest
output.

## Supported Languages

- `en`
- `zh-CN`

Aliases such as `zh`, `zh_CN`, and `cn` resolve to `zh-CN`.

## CLI Usage

```bash
coprogrammer digest --base origin/main --head HEAD --language zh-CN
coprogrammer digest --base origin/main --working-tree --language en
coprogrammer github-comment --file branch-digest.md --language zh-CN
```

You can also set an environment variable:

```bash
export COPROGRAMMER_LANGUAGE=zh-CN
coprogrammer digest --base origin/main --head HEAD
```

If no CLI flag or environment variable is set, `coprogrammer digest` uses the
`language` value from `.coprogrammer.json`.

## GitHub Actions

The PR digest workflow reads the repository variable
`COPROGRAMMER_LANGUAGE`.

If the variable is not set, the workflow defaults to `zh-CN` so Chinese teams
can read PR digest comments directly.

To switch a repository back to English, set:

```text
COPROGRAMMER_LANGUAGE=en
```

## Human Templates

English templates remain the default filenames. Chinese versions use the
`.zh-CN` suffix:

- `templates/task-brief.zh-CN.md`
- `templates/branch-digest.zh-CN.md`
- `templates/integration-plan.zh-CN.md`

## Product wording and model-generated text

For the current surfaces and acceptance criteria, see
[MVP design: current requirements](MVP_DESIGN.md#current-product-requirements-and-cli-design).
These are editorial rules for this project's CLI/guides, not a new localization
API or a guarantee about a connected model's replies.

### CLI labels and installation guidance

Lead with what happened: registered, preview only, blocked, installed or failed.
Distinguish a proposed file plan from completed writes. Show the relevant path or
operation and one appropriate next action; add more steps only when the flow
requires them. Avoid a repeated product slogan before every operation result.
Never suggest querying an unregistered session as the way to finish registration.

| Avoid | Prefer when supported by the result |
| --- | --- |
| `12 missing files` after those files were installed | `Client setup: applied` |
| A generic success claim after dry-run | `Preview: would register this window` |
| A conflict count with no location | `Conflicts: .mcp.json` and an inspection command |
| “已连接模型” after generating configuration | “配置已生成；重载客户端并完成信任流程。模型连接尚未验证。” |
| “很高兴为您提供全面、智能的一站式协作体验” before an error | “安装未完成：目标文件已更改。先检查冲突文件。” |

Keep necessary distinctions: partial writes, unknown completion/ACK outcomes,
stale state and connectivity not checked are useful information. State each at
the decision point; do not append generic disclaimers or repeat data timestamps
unless freshness changes the user's next action. Do not expose message bodies,
tokens or native diagnostics just to make an error sound more specific.

### Model replies and user-provided content

A coding client's response is separate from CLI labels. Prompts/guides should ask
for the task result, evidence, remaining uncertainty and necessary next action in
ordinary language. Avoid repeated AI introductions, forced three-part summaries,
empty praise and claims of completion unsupported by execution. Do not silently
rewrite stored user messages or task summaries to enforce a house style. Preserve
identifiers, source attribution and distinctions between proposed and executed work.

English documentation remains English; Simplified Chinese pages keep their current
language. Traditional Chinese is not a declared CLI locale; do not promise it or
mechanically convert user content. Localize human prose when supported, while
preserving machine JSON fields/reason codes and literal command arguments.


### Public references and review

Reviewed on 2026-10-27; these references inform wording, not CoProgrammer's
execution policy or machine contracts:

- [Fluent 2 content engineering](https://fluent2.microsoft.design/content-engineering):
  express tone through concrete rules and example outputs that can be reviewed.
  Here this means result-first CLI examples and separate guidance for generated
  replies; it does not introduce a new system prompt or model dependency.
- [Ant Design 文案](https://ant.design/docs/spec/copywriting-cn/):
  focus on the user's action, use familiar concise wording and consistent terms.
  Here `preview`, `applied`, `registered` and `connected` retain distinct meanings.
- [GOV.UK error messages](https://design-system.service.gov.uk/components/error-message/):
  explain the known problem and how the user can address it. Applied here to
  conflicting project files and inspection commands, not to web form components.

A fixed success label (for example “已保存”) requires a confirmed success state.
Known failures need a supported reason and recovery step; unknown causes must
remain unknown. Model replies should answer the question first, without default
praise, a forced three-item structure or a closing follow-up question. Distinguish
facts, inference and advice; do not invent a failure cause to fill a template.

Locale and register are separate choices. Future Hong Kong Traditional Chinese
copy needs regional vocabulary review; it must not simply reuse Taiwan wording.
Cantonese requires contextual language review rather than character replacement.
These are future editorial requirements, not newly supported CLI locales.

Style checks are advisory. They must not delete uncertainty markers such as
“可能” or “未核实”, rewrite stored messages, or override a project's explicit
language, legal or safety requirements. For each change, review the before/after
example against the actual success/preview/failure state and keep the source file
and regression evidence. Current checks use synthetic local fixtures only;
real-model style quality remains unverified. No style-filter dependency is added.
