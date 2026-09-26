# 多份审核的离线交接

同一项改动可能收到多份模型建议。`review-summary` 将这些本地文件对照同一组
提交，列出缺席、过期、覆盖缺口、风险和建议分歧。它生成待人工审核的快照，
不选择“获胜模型”，也不把意见一致当成合并批准。

[查看合成数据示例](example.md)：两份有效工件、一名缺席审核者、一处建议分歧。

## 使用

先按[接入指南](../MULTI_PLATFORM_QUICKSTART.md)生成并保存审核工件。每份工件
必须使用 `coprogrammer.review.v1` 格式；普通聊天记录、Codex/Claude Code 的
文字答复不能直接作为已完成工件导入。

```sh
coprogrammer review-summary --base origin/main --head HEAD \
  --review claude=.coprogrammer/claude-review.json \
  --review glm=.coprogrammer/glm-review.json \
  --expect deepseek --format markdown \
  --output .coprogrammer/review-summary.md
```

- `--review 名称=文件` 可重复；同一个名称重复提供会报错。
- `--expect 名称` 声明预期参与者，不会启动模型或新任务。未交付工件保持 `missing`。
- 名称是本地标记，使用 1–64 位英文字母、数字、点、下划线或连字符，首位为字母或数字。
- 总共最多 16 个不同名称；每个 JSON 文件最多 2 MiB。
- 输入文件的相对路径基于 `--cwd`。`--output` 相对路径基于命令实际运行目录，
  与已有输出命令一致；已经存在的文件不会被覆盖。
- 默认输出 JSON；`--format markdown --language zh-CN` 或 `--language en` 输出可读报告。
- 默认只报告结果；加 `--fail-on-attention` 后，有待处理项会在输出报告后返回 1。
  输入参数、目标提交或输出路径错误返回 2。返回 0 不是批准合并。

## 如何读报告

| 状态 | 含义 | 参与建议对照 |
| --- | --- | --- |
| `current` | 已完成工件的证据与本次选定提交重新核对一致 | 是，但仍需查看覆盖限制 |
| `stale` | 工件记录的提交与本次目标不同 | 否 |
| `prepared` | 仅生成请求预览，没有完成审核 | 否 |
| `missing` | 声明的审核未提供文件，或文件不存在 | 否 |
| `invalid` | 文件无法读取，或格式、完成字段、证据、建议校验失败 | 否 |
| `duplicate` | 与另一个名称使用相同的 JSON 内容 | 否，显示原名称 |

`current` 只表示证据匹配。`coverage=partial`、被排除的文件、模型遗漏的决定
或 `defer` 都需要继续处理。不同审核者提出 `preserve`、`drop` 或 `rebuild`
会显示分歧；`defer` 显示为判断或覆盖缺口，不作为反对票。

概述、风险和待执行检查来自审核者原文；检查建议不等于测试已运行。报告不会执行
这些文字。非空风险、部分证据、待判断项、分歧或任何非 `current` 状态都会触发
`attention_required`。重复结果也不会增加当前审核数量。

JSON 报告记录目标提交，以及成功解析的工件原始文件 SHA-256，便于交接时追溯输入。不同格式或空白的
同一 JSON 内容仍会被识别为重复。修改 JSON 的声明字段可以改变其身份描述；
该工具不提供签名、服务商调用收据或独立审核者认证。

## 从 Codex、Claude Code 或 Copilot 调用

在已配置的本地 CoProgrammer MCP 服务中调用 `review_summary`：

```json
{
  "base": "origin/main",
  "head": "HEAD",
  "reviews": [
    {"label": "claude", "path": ".coprogrammer/claude-review.json"},
    {"label": "glm", "path": ".coprogrammer/glm-review.json"}
  ],
  "expected": ["claude", "glm", "deepseek"]
}
```

MCP 返回 JSON，不写报告或 Manager 日志。所有相对工件路径基于服务所配置的项目
目录；客户端可自行展示或由用户保存结果。它与命令行使用相同校验，不产生服务商调用。

## 验证范围

开始与结束都会解析本次选定的 base/head；汇总过程中引用移动时，整次汇总失败，
必须重新运行。固定 SHA 工件即使自身有效，也不能作为不同目标提交的当前审核。
审核者原来的分支别名可以在另一台机器不存在；比较依据是已记录的完整提交 ID。

报告只覆盖已提交内容，不包含工作区未提交改动。`remote_freshness=not_checked`：
离线模式不查询 GitHub，也不会知道远端 PR 是否已经前进。使用者应先取得需要审阅
的最新提交，再明确指定目标。报告始终为 `draft`，后续集成计划仍逐份选择并经维护者审核。
