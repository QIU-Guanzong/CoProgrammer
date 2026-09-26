# CoProgrammer 升级研究：跨客户端分发与证据可信度

研究日期：2026-09-27

本轮围绕 CoProgrammer 已有的分支摘要、审核汇总、Manager、MCP 和多模型
适配，核对了 Agent Plugins 规范、OpenAI/Codex、Claude Code、GitHub Copilot、
GitHub Actions 与 gstack 的一手文档和仓库实现。目标是找出下一块真实缺口，
而不是把热门工具的功能全部叠到一个产品里。

## 研究结论

### 把“谁在工作”与“模型来自哪里”分开

Codex、Claude Code 和 Copilot 是运行代码、产出分支或提供客户端工具的工作
环境；Claude API、GLM 和 DeepSeek 是可选模型服务。GitHub 则保存 PR、检查、
评审和维护者决策。CoProgrammer 的优势在这些系统之间保存可审阅的协作状态，
不需要变成第四个代码代理或统一推理网关。

对应的结构是：Skills 讲流程，CLI/MCP 读取或更改本地协作状态，GitHub 保存
团队级评审与集成结果；模型服务仅在明确选择并提交分析请求时提供建议。
各层应能单独工作，服务不可用时不能把“未验证”包装为成功。

### 分发层采用通用包，客户端行为仍由各自格式承载

Agent Plugins 1.0 是一个已发布的开放规范，固定了根目录 `plugin.json`、
`skills/` 和可选 `mcp.json`。Codex/OpenAI 文档支持此便携格式，并保留旧
`.codex-plugin/plugin.json` 作为兼容回退；GitHub Copilot 文档也列出 Agent
Plugins 1.0。Claude Code 仍要求原生 `.claude-plugin/plugin.json`，并通过
仓库根 `.claude-plugin/marketplace.json` 发现 monorepo 子目录插件。Codex 的
repo marketplace 则放在 `.agents/plugins/marketplace.json`，入口字段与 Claude
略有差别，所以本仓库为两个客户端分别维护薄目录清单。

因此，本次把现有五个 Skills 作为一个便携 Agent Plugin，并分别为 Codex 和
Claude Code 添加原生 marketplace 清单。没有新增第二份技能正文，也没有把
客户端专有的 hook、MCP 或安装选项伪装成通用协议。

### Skills 不能替代可执行产品

打包技能只解决“如何引导流程”，不负责运行 Manager 命令。原技能示例使用
`PYTHONPATH=src`，只适用于 CoProgrammer 源码仓库；从 marketplace 安装到其他
项目后会指向错误代码。本次将它们改为调用安装后的 `coprogrammer`，并明确写出
命令不可用时必须把状态标成 unavailable，不能假装已拿到租约、最新摘要或验证
结果。

PyPI 已发布 `0.1.0`，但本分支的开发版本为 `0.2.0a1`，包含了该稳定包没有的
集成配置与审核汇总命令。因此便携包和 Claude 插件暂不内置 MCP 配置；使用者需
从与技能匹配的 CoProgrammer checkout 安装 CLI，再生成并合并对应客户端的 MCP
配置。等当前命令进入稳定发布、客户端启动能端到端验证后，再添加“装插件即有
工具”的体验。没有从本轮检查中确认出可供客户端直接连接的托管 MCP endpoint。

### 从 gstack 借鉴内容指纹和验证凭证，不借用其特定实现

gstack 的工作树指纹把评审和测试记录绑定到实际文件内容，减少仅按提交 SHA
判断新鲜度时，amend、rebase、squash 导致证据断裂的问题。它的证据账本还记录
命令和新鲜度窗口。与此同时，项目说明的 review receipt 仍需要调用方报告
`completed` / `converged`；指纹证明凭证指向哪段内容，不证明模型完整理解了内容。

CoProgrammer 可按此思路推进：记录文件内容指纹、检查命令、运行环境、时间和
结果；只输出 fresh / stale / unverifiable；把指纹与审核建议分开，不授予批准或
合并权。引入前应覆盖重写提交、未跟踪文件、忽略文件与并行工作树，并走维护者
评审，因为证据格式可能影响共享契约。

## 本次代码范围与刻意保留的边界

- 新增 Agent Plugins 1.0 清单、Claude Code 插件清单和仓库 marketplace 项。
- 保留现有 Codex 兼容清单，版本统一到 `0.2.0-alpha.1`；对应 Python
  `0.2.0a1` 的预发布标签写法。
- 技能在其他项目执行时不再假定存在 CoProgrammer 的 `src/` 目录。
- 没有发布到 PyPI、MCP Registry、Anthropic 目录或 OpenAI 插件目录。
- 没有新增 hook、后台任务、PR 写权限、模型 API 请求或自动合并。

## 后续优先级

1. **CLI 稳定分发**：发布可安装版本并验证 Python 支持范围和平台；再考虑
   `pipx` / `uvx` 与 MCP Registry。
2. **证据新鲜度**：先形成研究提案和兼容策略，再改 schema / protocol，并由
   维护者审查；用实际 Git 重写场景验证。
3. **GitHub 原生呈现**：先通过 job summary 与 artifact 输出审核汇总，保持只读，
   并确保 fork PR 没有模型密钥或写令牌。
4. **多模型质量对比**：对同一份有界差异应用同一评审量表，分别标注 mock、live
   和不可用；未跑真实请求时不得宣称供应商效果已验证。
5. **开源协作流程**：保持小型 change manifest、示例与可复现案例；将设计决策放到
   issue/discussion/PR 中，避免把活跃状态写进 `AGENTS.md`。

## 一手来源

- [Agent Plugins Specification 1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md)
- [OpenAI：Package your plugin](https://developers.openai.com/plugins/build/plugins)
- [GitHub：About plugins for Copilot](https://docs.github.com/en/copilot/concepts/agents/about-plugins)
- [Claude Code：Plugins overview](https://code.claude.com/docs/en/plugins)
- [Claude Code：Create a marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude Code：Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference)
- [PyPI：CoProgrammer 0.1.0](https://pypi.org/project/coprogrammer/0.1.0/)
- [GitHub Actions：Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [gstack：README](https://github.com/garrytan/gstack)
- [gstack：Ship and verification workflow](https://github.com/garrytan/gstack/blob/main/ship/SKILL.md)
