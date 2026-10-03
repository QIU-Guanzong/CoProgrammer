# CoProgrammer

**让 Codex、Claude Code 和 Copilot 共享任务归属、文件范围与交接记录。**

CoProgrammer 为分布在不同 Git 工作树中的编程助手提供本地协作工具：按依赖领取
任务，检查文件范围冲突，交换交接消息，并把分支改动整理成可审阅的摘要。
同一套能力通过命令行和 MCP 提供。需要 Python 3.10+ 和 Git 2.36+，无运行时 Python 第三方依赖。

[English](README.md) · [客户端接入](docs/knowledge/README.md) ·
[生态调研](docs/research/ecosystem-2026-09-30.md) · [贡献指南](CONTRIBUTING.md) · [MIT](LICENSE)

> 当前源码为 `0.3.0a1` 预发布版，请查看
> [PyPI](https://pypi.org/project/coprogrammer/) 的已发布版本，或使用下面的源码安装方式。配置生成与本地协议测试不代表真实客户端已连接，
> 模型供应商的在线调用仍需单独验证。

## 先运行一次完整示例

macOS / Linux：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --pre coprogrammer
coprogrammer demo
```

如需从源码运行，请克隆默认分支，再用 `python -m pip install -e .` 安装：

```sh
git clone https://github.com/QIU-Guanzong/CoProgrammer.git
cd CoProgrammer
```

Windows PowerShell 使用 `python -m venv .venv` 创建环境，再运行
`.venv/Scripts/Activate.ps1`。其余安装与演示命令相同。

演示创建临时仓库和两个真实工作树，通过现有接口验证任务领取、依赖与路径保护、
消息回执及完成流程，退出时清理临时文件。它不需要模型密钥，也不启动真实
Codex 或 Claude 客户端。`coprogrammer demo --json` 会输出逐步证据。
参见 [演示说明](docs/DEMO.md)。

## 它解决什么问题

一个窗口改接口，另一个窗口改调用方，各自通过测试仍可能在集成时产生分歧。
CoProgrammer 让双方先明确任务范围和归属，并保留可核对的交接与审核材料。

| 开发阶段 | 可以检查的结果 |
| --- | --- |
| 接入项目 | 预览 Skills、Markdown 指引和 MCP 配置，保留已有配置 |
| 领取任务 | 依赖、客户端约束、工作树归属及路径租约检查 |
| 开始或恢复工作 | 一份协作简报汇总可做任务、阻塞、过期窗口和下一步 |
| 跨窗口交接 | 持久消息、任务讨论、回执与可恢复的同步游标 |
| 准备审阅 | 分支摘要、受保护路径和绑定提交的审核材料 |
| 集成决策 | 保留、丢弃、重建或延后的建议，由维护者审核 |

## 接入已有项目

保持刚才的 Python 环境激活，进入需要协作的项目目录：

```sh
coprogrammer integrations doctor
coprogrammer knowledge list
coprogrammer setup --client codex --include-content
```

先检查预览，再决定是否运行 `coprogrammer setup --client codex --apply`。
`claude` 和 `copilot` 对应另外两个客户端。安装器创建缺失文件，保留现有项目
指令；Skills、生成文档或 MCP 设置存在不同内容时会报告冲突。
客户端仍需按自身流程信任、加载并连接配置。

需要保留 MCP 配置自行接入时使用 `--no-mcp`。完整的原生路径、冲突处理、
六个 Skills 和十二个只读资源见 [接入指南](docs/knowledge/README.md)。

## 两个窗口如何协作

先为每个窗口准备独立的 Git 工作树，再分别注册会话：

```sh
# 在 Codex 所在工作树
coprogrammer manager session register --session codex-api --client codex --task api-v2

# 在 Claude Code 所在工作树
coprogrammer manager session register --session claude-ui --client claude --task api-v2
```

Git 工作树默认共享同一份本地 Manager 记录。在第一个窗口创建并领取任务：

```sh
coprogrammer manager task create --session codex-api --id api-v2 \
  --title '更新接口' --pattern 'src/api/**' --client codex
coprogrammer manager task claim --session codex-api --id api-v2
coprogrammer manager briefing --session codex-api
```

保存返回的 `claim_id`，编辑或提交前用 `task guard` 检查范围；长任务用
`task renew` 续期。已过期的领取需要显式恢复，不会自动转交给另一个窗口。
用 `message send` 发送交接、`message inbox` 查看、`message ack` 确认收到。
详见 [任务调度](docs/scheduling/README.md) 和 [窗口通信](docs/collaboration/README.md)。

## 一份简报理解当前状态

```sh
coprogrammer manager briefing
coprogrammer manager briefing --session claude-ui --json
coprogrammer manager briefing --fail-on-attention
```

CLI 与 MCP 的 `manager_briefing` 使用同一实现。简报显示任务阻塞原因、会话
新鲜度、租约冲突、待决事项和待回执数量，并给出下一步建议；不执行这些建议。
默认每组最多 20 条，完整计数和省略数量始终可见。

`--session` 限定待回执和已领取任务的展示范围；任务就绪状态和仓库风险仍是
全局视角。就绪不保证当前窗口能够领取，实际领取会重新检查约束。
不输出消息正文或领取令牌。详细语义见 [协作简报](docs/BRIEFING.md)。

## 审阅分支

```sh
coprogrammer digest --base origin/main --head HEAD --language zh-CN
coprogrammer review-summary --base origin/main --head HEAD \
  --review claude=.coprogrammer/claude-review.json --expect deepseek --format markdown
```

根据项目选择正确的基准分支。审核汇总会保留缺失、过期、不完整和冲突证据，
不会调用模型。可选 Claude、GLM、DeepSeek 审核适配器只在显式 `--send` 时
发送已捕获的差异，可能产生供应商费用；模型建议不等于维护者批准。

## v0.3 升级与边界

- `manager dispatch --session <窗口>` 给出当前客户端和工作树可领取的任务及阻塞原因。
- `check run` 记录显式检查，`check verify` 根据真实文件内容、命令、运行环境和时效判断结果是否仍有效。
- `manager handoff` 导出任务交接包，另一台电脑用 `workspace compare` 核对版本、提交、基准和内容。

完整流程见[跨窗口与跨电脑交接](docs/WORKSPACE_HANDOFF.md)、[验证记录](docs/VALIDATION_EVIDENCE.md)
及[本轮调研](docs/upgrade-2026-10-04/research.md)。接收端仍需运行本地检查并领取本地任务；
独立克隆使用独立 Manager，交接包不会转移租约。

租约和 guard 依赖参与者遵守约定，不拦截任意文件写入。窗口活跃度来自显式
pulse，不等于操作系统进程探测。消息回执表示收到，任务完成表示记录完成，
两者都不能代替测试、审核或合并。当前不提供托管 Manager、自动补丁重建或自动合并。

欢迎贡献最小可复现的冲突案例、真实客户端接入报告和有验证依据的改进。
先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，本地检查：

```sh
python -m unittest discover -s tests
coprogrammer config validate
```
