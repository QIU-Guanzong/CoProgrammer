# Skill、MCP 与 Markdown 项目接入

三种能力共用 CoProgrammer 已实现的任务调度和协作流程：

| 入口 | 当前提供 |
| --- | --- |
| Skill | 项目接入、项目约定、任务简报、开发中同步、分支摘要审阅、集成计划，共 6 个工作流 |
| MCP Tools | 任务领取、范围检查、会话、消息、租约和审阅等现有操作 |
| MCP Resources | 6 个 Skill 与 6 份 Markdown，共 12 个固定目录资源 |
| MCP Prompts | 任务简报、交接说明，共 2 个带参数的模板入口 |
| Markdown | AGENTS、CLAUDE、Copilot 说明、协作指南、任务简报、交接模板 |

## 先查看，再接入

安装匹配本分支的 CLI 后，在需要协作的项目目录运行：

```sh
coprogrammer knowledge list
coprogrammer knowledge list --kind skill
coprogrammer knowledge show templates/COORDINATION
coprogrammer setup --client codex --include-content
```

最后一条只预览，列出实际路径、拟生成内容、文件大小、摘要和现有文件状态。
`--include-content` 不会输出已有配置中的凭据或规则。用 `--cwd /path/to/project`
可以指定已存在的目标目录。确认范围后，以同样选项添加 `--apply`：

```sh
coprogrammer setup --client codex --apply
# 其他客户端选择 --client claude 或 --client copilot
```

默认安装全部 Skill，也可以重复指定完整名称：

```sh
coprogrammer setup --client codex \
  --skill coprogrammer-task-brief --skill coprogrammer-active-sync --apply
```

`--no-skills` 跳过 Skill；`--no-mcp` 跳过原生 MCP 配置。接入不会修改全局
设置、安装模型或启动客户端。

## 文件位置

| 客户端 | Skill 路径 | 稳定规则 | 原生 MCP 配置 |
| --- | --- | --- | --- |
| Codex | `.agents/skills/<name>/SKILL.md` | `AGENTS.md` | `.codex/config.toml` |
| Claude Code | `.claude/skills/<name>/SKILL.md` | `AGENTS.md`、`CLAUDE.md` | `.mcp.json` |
| Copilot / VS Code | `.agents/skills/<name>/SKILL.md` | `AGENTS.md`、`.github/copilot-instructions.md` | `.vscode/mcp.json` |

三个客户端均生成 `docs/coprogrammer/COORDINATION.md`、`task-brief.md` 和
`handoff.md`。Claude 的新说明通过 `@AGENTS.md` 导入根规则；已有说明保留，
需要按项目现状手动补充引用。Codex/Copilot 共用 `.agents/skills`；其他目录
存在同名 Skill 时会提示。已通过插件安装这组 Skill 的客户端，宜用
`--no-skills` 避免重复发现。

## 已有文件

| 状态 | 行为 |
| --- | --- |
| `create` | 文件缺失，应用后返回 `created` |
| `unchanged` | 内容相同，不重写、不改变修改时间 |
| `preserve` | 已有项目说明内容不同，原样保留并提示手动引用协作指南 |
| `conflict` | 同路径 MCP、Skill 或生成文档内容不同，本次不应用任何接入文件 |
| `blocked` | 目标或父目录是链接、类型不符或不可检查，本次不应用 |

冲突返回状态码 1；检查 `conflicts`。不会自动重写 JSON/TOML，避免破坏 JSONC
注释、未知设置或已有服务器。可以先使用 `--no-mcp --apply` 安装 Skill 和文档，
再以 `integrations config --client <client>` 获取服务片段，按现有结构手动合并。
没有强制覆盖选项。写入失败时尝试撤回本次已完整创建且未被改动的文件；
残留空目录、部分写入或并发修改需检查后再重试。

## MCP 文档与提示入口

连接 MCP 后，客户端可通过 `resources/list` 查看目录，并精确读取其中的 URI，
例如 `coprogrammer://skills/coprogrammer-active-sync` 或
`coprogrammer://templates/COORDINATION`。资源从安装包读取，不依赖源仓库；
不接受任意文件路径、URL 或目录外的项目 Markdown。

| Prompt 名称 | 必填参数 | 可选参数 |
| --- | --- | --- |
| `coprogrammer-task-brief` | `task` | `scope` |
| `coprogrammer-handoff` | `task` | `summary` |

通过 `prompts/list` 查看，再用 `prompts/get` 请求模板上下文。它不调用模型、
保存文件或领取任务；参数只是任务资料，不授予额外权限。入口如何显示取决于
客户端。本实现支持原有 4 个 MCP 协议版本，不提供资源订阅、后台通知或唤醒。

## 验证与维护

1. 检查生成文件，将项目规则和模板纳入正常审阅。
2. 将 `.coprogrammer/` 运行状态排除在版本控制之外；提交接入文件后再开始新的
   范围受控开发任务。
3. 重载客户端，按它自己的项目信任和 MCP 授权流程连接。
4. 读取资源列表，再调用 `manager_status`；实际成功后才认为连接已验证。

配置固定本机 Python、包安装位置和项目目录。移动路径或更换环境后需重新生成
并审阅，不能直接称作团队通用配置。文件写入成功不代表客户端已信任或连接。

Skill 插件原文与安装包副本有逐字节一致性测试，修改时须同步。目录由
`knowledge.py` 显式维护。自定义技能市场、第三方 MCP 自动安装、任意项目文档
索引不包含在本次功能中。见[研究依据](research.md)、[验证记录](validation.md)
及[任务范围](task-brief.md)。
