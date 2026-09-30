# 2026-09-30：协作工具生态与 CoProgrammer 升级取舍

核验日期：2026-09-30（UTC+8）。本报告依据官方仓库、官方文档和 GitHub API；
没有安装或运行这些第三方项目，也没有测量使用量、效果或市场份额。
比较范围包含五个采用 MIT 许可的项目和一个带附加许可条款的相邻公开仓库，
不把“代码可见”一律写成标准开源许可。以下建议是产品判断，不是已交付功能。

本地基线为 `dc49277900cfcb80a9670a0e62ec44e8bdd9dd75`，版本 `0.2.0a1`。
已对照 [项目说明](../../README.md)、[9 月 27 日研究](../RESEARCH_UPDATE_2026-09-27.md)、
[协作研究](../collaboration/research.md)、[调度研究](../scheduling/research.md) 和
[接入研究](../knowledge/research.md)，并检查 Manager 存储、任务看板实现。
分支能力、安装包发布、真实客户端连通和线上采用情况必须分别核验。

## 结论

CoProgrammer 最有辨识度的方向是：让独立运行的编程助手共享任务归属、文件范围、
交接记录和审核证据，帮助维护者判断哪些改动能够集成。当前已经有原子任务领取、
租约、消息回执、CLI/MCP、分支摘要和审核汇总；再增加一层普通任务列表，价值有限。

本轮优先把已有状态变成一份可操作的协作简报，缩短新用户得到第一个结果的路径，
并用可复现示例展示“两个窗口争用同一范围时发生什么”。这些改进可以复用现有
核心，不需要接管终端进程、自动合并或新增模型调用。

## 六个项目分别解决什么问题

| 项目与一手来源 | 核验到的重点 | 可借鉴的选择 | 本轮明确不做 |
| --- | --- | --- | --- |
| [Beads](https://github.com/gastownhall/beads) | 持久化任务依赖图；`bd ready` 找出无阻塞任务，`bd update --claim` 领取任务，`bd prime` 汇总工作上下文；当前主存储为 Dolt。 | 用一个简报入口帮助刚恢复的窗口理解现状；保持 ready 与实际领取的区别；阻塞理由应可追溯。 | 不替换现有 Manager 为 Dolt，不复制完整问题跟踪系统，不把导出的 JSONL 当作通用数据库接口。 |
| [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail) | 身份、持久消息、线程、回执和建议性文件预留；提供组合操作 macros 降低接入步骤；文档区分任务状态与会话记录。 | 将读状态的常见组合收敛为一个只读入口；任务 ID 在消息、租约和审核交接中保持一致。 | 不复制实现、不新增默认依赖，不自动联系外部成员，不把回执当成批准。其 [LICENSE](https://github.com/Dicklesworthstone/mcp_agent_mail/blob/3fad5ec672869f81d2ca0a4c525dde004ac96f45/LICENSE) 带额外限制，不能称为标准 MIT。 |
| [Overstory](https://github.com/jayminwest/overstory) | 组合独立 worktree、消息、运行时适配和工作者生命周期；`ov prime` 提供上下文，状态界面帮助观察队伍。仓库已归档。 | 借鉴“恢复上下文”和“先看阻塞”的操作顺序，明确进程状态与声明状态的区别。 | 不以已归档项目作为持续兼容承诺，不实现 worker 启停、终端注入或自动冲突合并。 |
| [agent-deck](https://github.com/asheshgoplani/agent-deck) | 通过终端界面管理多个编程会话，覆盖搜索、分组、worktree、会话分叉及 MCP/Skill 管理。 | 协作简报首先回答谁在做什么、哪里需要注意；在 README 先展示具体任务入口，再列工具。 | 不重做终端管理器，不扫描私有会话文件推断活动，不修改用户全局 MCP/Skill 配置。 |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | 以规格、计划、任务和验证结果组织开发；文档按使用目的提供入口并给出可重复步骤；支持独立流程。 | 用简短案例串联 task brief、执行范围、验证和交接；入口区分首次体验、接入已有项目和多人协作。 | 不强制用户迁移规格系统，不自动把 Markdown 中的“完成”认定为验证成功，不让流程文档变成第二份实时任务状态。 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 面向有状态执行的基础设施；官方文档分别描述 [持久化](https://docs.langchain.com/oss/python/langgraph/persistence) 与 [中断恢复](https://docs.langchain.com/oss/python/langgraph/interrupts)。恢复节点可能重新执行之前的步骤。 | 对重启、重试和幂等行为写清合同与测试；只读汇总必须与实际恢复动作分开。 | 不引入通用图运行时或托管服务；一条 Manager 消息不能启动任意代码或自动恢复有副作用的动作。 |

这些工具不是同一种替代品。Beads 偏向任务记忆，Agent Mail 偏向通信，
agent-deck 偏向会话操作，Overstory 偏向运行时编排，Spec Kit 偏向开发流程，
LangGraph 偏向执行基础设施。CoProgrammer 可以与这些层共存；这种定位来自
上述功能范围与本地实现的对照，并非对任何项目质量或用户数量的排名。

## 对旧资料的两处修正

1. `steveyegge/beads` 现重定向至 `gastownhall/beads`。Beads 当前 README 明确
   `.beads/issues.jsonl` 是导出与交换产物，不是主存储或备份；Agent Mail README
   仍有将不同 Beads 实现描述为共享此格式的段落。需要导入任务时，应先固定
   来源实现、版本和导出格式，不依据旧文章直接读取该路径。
2. Overstory 仓库页面显示 2026-05-28 归档；本次 GitHub API 也返回
   `archived: true`。它仍能提供设计参考，但已有研究中将它作为参考的链接
   不能被解释为当前活跃的上游依赖或维护承诺。

来源：[Beads 存储说明](https://github.com/gastownhall/beads#-storage-modes)、
[Agent Mail 的 Beads 集成说明](https://github.com/Dicklesworthstone/mcp_agent_mail#integrating-with-beads-dependency-aware-task-planning)、
[Overstory 仓库](https://github.com/jayminwest/overstory)。

## 本轮可以落地的优先级

| 优先级 | 建议交付 | 为什么现在做 | 可检查的完成条件 |
| --- | --- | --- | --- |
| P0 | 只读协作简报，例如 `manager briefing`，并提供同源 MCP 工具 | 现有状态分散于 sessions、task board、leases、decisions 和 inbox；恢复工作需要多次调用。 | 从同一次事件读取形成摘要；显示时间、阻塞、过期归属、待回执和下一步命令；有条数限制与截断提示；不新增事件、不刷新 heartbeat、不领取任务、不自动回执。 |
| P0 | 简报复用现有任务判定并解释含义 | 现有 `scheduler.board` 已有 `blocked_reasons` 和 `ready`，无需重写调度器。 | “全局无依赖/租约阻塞”不得写成“当前窗口必定可领取”；领取仍检查 client、worktree、session freshness 等条件；过期 claim 指向显式恢复流程。 |
| P0 | 可重复的无密钥体验与双语入口 | 读者应该先看到一个结果和一个明确问题，再阅读完整协议。 | 在临时仓库中展示领取、冲突、交接与恢复；命令可以在新环境重跑；明确为本地示例；首次步骤不依赖模型 API、GitHub 写权限或真实客户端账户。 |
| P0 | README、GitHub About 和 topics 同步 | 简短描述承担搜索入口；README 负责证明能力与说明接入。 | 首屏出现用户、问题、命令、当前发布状态；链接直达 quickstart；保留 source preview 与 live verification 边界；远端修改后读回 About/topics。 |
| P1 | Manager 重放成本基准与派生状态复用 | 当前写入事务校验并重写完整日志；多个读取入口各自重建状态。性能改动应由测量驱动。 | 固定事件量与输出等价性，记录冷/热运行时间和环境；先减少同一次请求的重复重建，再考虑缓存；缓存失效与跨进程一致性必须测。 |
| P1 | 外部任务源的显式预览导入 | 可复用 Beads/Spec Kit 的任务来源，同时保留单一任务归属。 | 来源与版本可识别；预览映射、冲突和路径范围；重复导入幂等；外部字段不授予租约或审批；共享格式改变需维护者审核。 |
| P1 | 审核凭证的新鲜度与实际 Git 场景 | 证据与代码发生偏移，影响集成判断，且已有 9 月 27 日研究基础。 | 覆盖 rebase/amend、脏工作树和缺失证据；区分 fresh、stale、unverifiable；不把指纹相同解释为审核质量相同。 |
| 暂缓 | 跨机器托管、终端控制、通用图调度和自动合并 | 这些改变信任模型、权限或产品责任，需要独立设计。 | 不写入本轮已实现能力，不为关键词曝光而加到 GitHub 描述。 |

P0 的简报是“降低理解现有状态的成本”；不应承诺它能降低模型费用或提升成功率，
除非后续对相同工作流做了可复现测量。P1 的性能工作也不能用其他项目的
数据替代本项目基准。涉及 schema、protocol、迁移或批准语义的改动，继续遵守
仓库现有审核要求。

## GitHub 呈现建议

建议 About 使用可搜索、能被现有实现支撑的描述：

> Coordinate Codex, Claude Code and Copilot with shared tasks, file leases, handoffs and reviewable branch digests. Local CLI + MCP.

建议 topics 从真实能力中选取：`multi-agent`、`coding-agents`、`mcp-server`、
`codex`、`claude-code`、`github-copilot`、`git-worktree`、`code-review`、
`developer-tools`、`python`。不要用自动合并、托管调度或供应商官方集成等
未被证明的标签。

README 的建议顺序：一句定位 → 最短可运行示例 → 一次真实输出 → 两窗口协作
场景 → 与相邻工具的分工 → 安装与接入 → 当前限制 → 贡献入口。
中文页应是完整入口，英文页保持面向全球开发者的简洁说明。更多文档链接不等于
更高可发现性；安装成功、实际使用和公开曝光效果应分别收集证据。

## 可复核的来源快照

下表为 2026-09-30 通过 `GET /repos/{owner}/{repo}` 和
`GET /repos/{owner}/{repo}/commits/main` 读取的状态。SHA 固定到当次默认分支，
不代表本地安装、稳定发行版或项目所有分支；许可列仅记录仓库元数据与文件观察。
未采集或比较星数。

| 官方仓库 | 当次 main SHA / README | archived | 许可观察 |
| --- | --- | --- | --- |
| gastownhall/beads | [3f9561db2bd1](https://github.com/gastownhall/beads/blob/3f9561db2bd1b1903ca8cbb39e9fc0cb37b0bccb/README.md) | false | GitHub 元数据：MIT |
| Dicklesworthstone/mcp_agent_mail | [3fad5ec67286](https://github.com/Dicklesworthstone/mcp_agent_mail/blob/3fad5ec672869f81d2ca0a4c525dde004ac96f45/README.md) | false | 元数据：NOASSERTION；LICENSE 为 MIT 加附加限制 |
| jayminwest/overstory | [ff38f3f76f08](https://github.com/jayminwest/overstory/blob/ff38f3f76f084abcc34f519bcaa69580f6e53cf1/README.md) | true | GitHub 元数据：MIT |
| asheshgoplani/agent-deck | [035fd602eda5](https://github.com/asheshgoplani/agent-deck/blob/035fd602eda5e3ed7e95edb63b6418fbe285f74d/README.md) | false | GitHub 元数据：MIT |
| github/spec-kit | [2c0a57abe1e7](https://github.com/github/spec-kit/blob/2c0a57abe1e7383a864c7d5e4dfa2457d7537734/README.md) | false | GitHub 元数据：MIT |
| langchain-ai/langgraph | [07b33185eab8](https://github.com/langchain-ai/langgraph/blob/07b33185eab893be2ed031eedae52f09314bf77c/README.md) | false | GitHub 元数据：MIT |

本报告只提炼问题、流程与边界，没有引入第三方代码或运行时依赖。
