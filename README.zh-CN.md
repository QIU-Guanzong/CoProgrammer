# CoProgrammer：多助手、多窗口编程协作

**让编程助手协作有序。Teamwork for coding agents.**

让同一 Git 仓库中的多个 AI 编程窗口共享任务、检查文件范围冲突、保留交接记录。
支持 Codex、Claude Code、Copilot、OpenClaw、WorkBuddy 的项目接入，
通用 agent harness 可通过 CLI 或 MCP 使用。

[![CI](https://github.com/QIU-Guanzong/CoProgrammer/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/QIU-Guanzong/CoProgrammer/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-black)](LICENSE)

[English](README.md) · [先体验](#先体验一次完整流程) ·
[双窗口实操](docs/GETTING_STARTED.md) · [客户端接入](docs/knowledge/README.md) ·
[版本发布](https://github.com/QIU-Guanzong/CoProgrammer/releases)

[什么情况下值得用？](docs/USE_CASES.md) · [原生检查与自动执行](docs/NATIVE_RUNTIME_WORKFLOW.md)

## 它解决什么问题？

一个 Codex 窗口修改接口，另一个 Claude 窗口修改调用方。谁正在改哪些文件？
上游任务完成了吗？窗口重启后怎样接上之前的工作？Git 分支隔离了编辑，
团队仍需要一份共享的协作记录。

CoProgrammer 记录**任务归谁、允许修改哪些文件、工作被什么阻塞，以及交接时
需要知道什么**。编程工具负责写代码；CoProgrammer 通过本地命令行和 MCP 协调工作。

| 常见问题 | CoProgrammer 的处理方式 |
| --- | --- |
| 两个窗口同时领取重叠工作 | 原子领取检查任务归属、工作树与文件范围租约。 |
| 上游还没完成，下游就开始修改 | 依赖未完成时，任务保持阻塞。 |
| 交接信息散落在终端里 | 消息和明确回执持久保存，重启后仍可查看。 |
| 测试通过后，代码又发生变化 | 验证记录核对文件内容、命令、运行环境及有效期。 |
| 换电脑后版本、分支或文件不一致 | 交接包比对版本、提交、基线和文件内容。 |

## 先体验一次完整流程

需要 **Python 3.10+、Git 2.36+**。在已激活的 Python 虚拟环境中运行：

```sh
python -m pip install --pre --upgrade coprogrammer
coprogrammer demo
```

无运行时 Python 第三方依赖，演示不需要模型密钥。它会创建两份真实 Git 工作树，
验证任务领取、依赖、范围冲突、交接消息、回执和完成流程，最后清理临时项目。
它不启动真实编程客户端，也不调用模型。

一次实际运行的输出节选：

```text
[passed] Create two Git worktrees: Two branches share one repository and one Manager event log.
[passed] Block unfinished dependencies: Claude cannot claim documentation until the API task is finished.
[passed] Reject overlapping work: A different worktree cannot claim src/api.py while Codex holds src/**.
```

[查看演示的验证范围 →](docs/DEMO.md)

## 在自己的项目中使用

`start`、`status` 需要 **0.3.0a2+**。进入已有提交、位于具名分支的 Git 项目，
每个编程窗口使用独立工作树。在项目 `.gitignore` 中加入 `.coprogrammer/`，
让本地运行记录留在版本控制之外。

```sh
# Codex 所在工作树
coprogrammer start --client codex --session codex-api --task api-v2
coprogrammer status --session codex-api

# Claude Code 所在的另一份工作树
coprogrammer start --client claude --session claude-ui --task api-v2
coprogrammer status --session claude-ui
```

`start` 登记当前窗口，并预览客户端配置状态；它不启动编程工具，不安装配置。
加 `--dry-run` 可先预览登记。休息或重启后，加 `--resume` 明确恢复同一个窗口。
状态查询不会刷新会话；默认会话活跃期为五分钟。

在 Codex 工作树中创建任务，查看下一步，再领取：

```sh
coprogrammer manager task create --session codex-api --id api-v2   --title '更新接口' --pattern 'src/api/**' --client codex
coprogrammer status --session codex-api
coprogrammer manager task claim --session codex-api --id api-v2
```

领取结果包含归属令牌，后续检查文件范围和完成任务时使用它。
[双窗口实操指南](docs/GETTING_STARTED.md) 包含依赖、消息、回执和完成流程。
指定窗口查询状态时，会区分仓库中待办的工作与该窗口真正能够领取的工作。

### 接入 Codex、Claude Code 或 Copilot

先预览项目内的 Skills、Markdown 指引和 MCP 配置：

```sh
coprogrammer setup --client codex --include-content
```

检查输出后，明确创建缺失文件：

```sh
coprogrammer setup --client codex --apply
```

另外两个客户端分别使用 `claude`、`copilot`。已有项目指令会保留；不同内容的
Skills 或 MCP 配置会报告冲突。随后重新加载客户端，完成其项目和 MCP 信任流程。
配置生成成功不代表客户端已经连接。

升级包或移动 Python/项目路径后，运行 `coprogrammer setup --client codex --upgrade`
预览更新，再加 `--apply` 写入。只更新有安装记录且未被改动的生成文件；自定义内容
继续报告冲突。见[安装后如何升级](docs/INSTALLATION_MAINTENANCE.md)。

MCP 提供同一套本地协作能力。`workspace_status` 汇总工作状态，`task_dispatch`
筛选可领取任务。插件包含六个 Skills，当前候选构建提供十六个只读 Markdown
资源，包括 worker 和中断核对指引。
[接入指南](docs/knowledge/README.md) · [插件安装](docs/PLUGIN_QUICKSTART.md)

`0.3.0a8` 预发布候选包含 Codex task adapter 和诊断；从 PyPI 安装前先核对
[发布状态](https://github.com/QIU-Guanzong/CoProgrammer/releases)，`0.3.0a7` 不含这些新增功能。
在包含该升级的 Python 环境运行 `python -m coprogrammer.codex_harness --check`，
普通检查不启动 Codex；通过 `coprogrammer knowledge show templates/CODEX_TASK_HARNESS`
阅读随包的版本/help 诊断与明确执行流程。模块或资源缺失时先核对安装构建，
不要据此重试原任务。

当前候选也包含 Claude Code 的 task-only 适配器。运行
`python -m coprogrammer.claude_harness --check` 查找可信原生程序，不启动客户端；
通过 `coprogrammer knowledge show templates/CLAUDE_TASK_HARNESS` 阅读安装、已有
账户核对、任务执行与明确消息回执流程。默认只提供内置读取工具；明确指定
`--access workspace-write` 才提供编辑工具，仍遵循原生权限。找到客户端和
GLM/DeepSeek 会话标签都不证明模型可用。

## 其他能力从哪里开始？

### 连续处理任务和交接消息（0.3.0a7+）

`start --apply-setup --dry-run` 一起预览项目接入和窗口登记，审阅后去掉
`--dry-run` 应用。`worker watch` 连续处理可领取任务；明确指定 `--handle-inbox`
后处理 harness 给出的已投递消息回执，`--wait` 有限等待其他窗口的变化。
失败、人工决策和文件范围问题会停止。需要提供可信 JSON harness，不代替客户端
登录或启动其界面。见[前台自动协作指南](docs/FOREGROUND_WORKERS.md)。

### 减少手动同步（0.3.0a3+）

提供 **Skill 版、MCP 版、完整接入版**。`setup --edition skills` 安装 Skill
与 Markdown 指引；`--edition mcp` 只生成原生 MCP 配置；默认 `full` 包含两者。
三个版本共用现有的六个 Skill 与调度器。

`coprogrammer worker step --session codex-api --apply` 串起心跳、收件箱、待决事项、
任务选择与范围检查，自动续期有效归属或领取合适任务。未确认接收的消息会暂停
工作。完成时用 `worker finish --notify <窗口编号>` 记录交接通知，重复提交同一
结果不会重复发送消息。

GLM、DeepSeek 已配置在 Claude Code 中的窗口，登记 `--client claude`，分别添加
`--provider glm` 或 `--provider deepseek`。任务可按客户端或提供方标签筛选；
登记标签不会配置密钥，也不代表模型连接已验证。MCP 提供同样的 `worker_step`
和 `worker_finish`，由参与窗口调用。[安装与自动协作指南 →](docs/AUTOMATIC_COLLABORATION.md)

| 需要做的事 | 入口 |
| --- | --- |
| 查看分工、阻塞和下一步 | `coprogrammer status`；[入门指南](docs/GETTING_STARTED.md) |
| 发送交接消息、确认收到 | `manager message`；[通信指南](docs/AGENT_RUNTIME_INTEROP.md) |
| 编辑前检查文件范围 | `manager task guard`；[调度指南](docs/MULTI_PLATFORM_QUICKSTART.md) |
| 核对测试结果是否仍有效 | `check run` / `check verify`；[验证记录](docs/VALIDATION_EVIDENCE.md) |
| 换电脑继续工作 | `manager handoff` / `workspace compare`；[跨电脑交接](docs/WORKSPACE_HANDOFF.md) |
| 审阅并整理分支改动 | `digest` / `integration-plan`；[命令参考](docs/GETTING_STARTED.md#prepare-a-pr) |
| 请求第二份审核意见 | 明确调用 Claude、GLM 或 DeepSeek；[多平台指南](docs/MULTI_PLATFORM_QUICKSTART.md) |

### 接入更多 AI 工作环境（0.3.0a4+）

OpenClaw 可以加载工作区 Skills；WorkBuddy 可以导入 Skill/MCP 接入包。
通用 agent harness 可以导入 MCP，或在工作步骤之间调用 CLI，复用任务队列、
范围检查和持久收件箱。

```sh
coprogrammer setup --client openclaw --edition full --include-content
coprogrammer setup --client workbuddy --edition full --include-content
coprogrammer setup --client harness --edition mcp --include-content
```

检查所选方案后加 `--apply`。报告会说明需要哪些客户端导入步骤；生成文件不代表
已经连接。Grok 也可用于明确发起的代码评审：
`review --provider grok --model MODEL`。
[接入步骤、能力边界与 Grok 指南 →](docs/EXTENDED_AI_INTEGRATIONS.md)

## 怎样配合现有工具？

如果你已经使用多个编程助手，希望它们共享任务归属、沟通记录和审核材料，
CoProgrammer 就是中间的协作层，可以配合现有编程工具与 GitHub 审阅流程。

[gstack](https://github.com/garrytan/gstack) 提供开发与审阅工作流；
[Beads](https://github.com/gastownhall/beads) 提供持久任务记录；
[Gas Town](https://github.com/gastownhall/gastown) 管理多助手工作空间及编排。
CoProgrammer 聚焦本地任务归属、文件范围协调、持久交接与可审阅的集成材料，
以小型 Python CLI/MCP 包提供这些能力。
[比较与本轮设计依据 →](docs/research/onboarding-2026-10-12.md)

同一台电脑的 Git 工作树共享 Manager；独立克隆各自拥有 Manager。
交接包核对上下文，不转移全局租约。范围租约属于合作检查，不是文件系统权限。
验证记录是未经身份认证的本地证据。PR 审批和合并仍遵循项目自身规则。
演示不代表真实客户端或模型供应商已经连接。

## 参与改进与反馈

[报告可复现问题](https://github.com/QIU-Guanzong/CoProgrammer/issues) ·
[提出接入建议](https://github.com/QIU-Guanzong/CoProgrammer/discussions) ·
[贡献指南](CONTRIBUTING.md)

适合首次贡献的改进包括：小型客户端接入示例、更清楚的错误提示，或真实工作树
冲突的回归测试。请附上命令、版本、预期和实际结果，移除私有代码及凭据。
如果这个工具对你的团队有帮助，欢迎 Star，让更多人发现它。

从源码开发：

```sh
git clone https://github.com/QIU-Guanzong/CoProgrammer.git
cd CoProgrammer
python -m pip install -e .
python -m unittest discover -s tests
```

[MIT 许可证](LICENSE)。当前为预发布软件，欢迎具体问题与反馈。
