# Codex、Claude、GitHub、GLM、DeepSeek 接入指南

本指南对应 `0.2.0a1` 升级预览。版本发布前，从此分支安装；生成配置不代表
客户端已连接，检测到环境变量也不代表服务商认证通过。

## 各平台如何协作

| 平台 | 本次实现 | 输入与结果 |
| --- | --- | --- |
| Codex | 原生 TOML MCP 配置 | 共享心跳、租约、契约提案、冲突预警、分支摘要 |
| Claude Code | 原生 `.mcp.json` 配置 | 使用同一套 MCP 工具与本地协作账本 |
| GitHub Copilot | VS Code `mcp.json` 配置 | 使用同一套 MCP 工具 |
| GitHub | `gh` 只读 PR 交接 | PR 元数据、完整 base/head 提交 ID；沿用现有摘要 Action |
| Claude API | Anthropic Messages 适配 | 对指定提交的代码差异提出结构化建议 |
| GLM | Z.AI Chat Completions 适配 | 同上，服务地址与模型可显式指定 |
| DeepSeek | Chat Completions 适配 | 同上 |

Codex 和 Claude Code 是协作客户端，模型 API 是独立服务入口。
模型建议不会直接写代码、执行返回的命令、批准契约或合并 PR。

## 安装与本地检查

在包含本次升级的源码目录安装：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/coprogrammer integrations list
.venv/bin/coprogrammer integrations doctor
```

Windows 使用 `.venv\Scripts\python.exe` 和 `.venv\Scripts\coprogrammer.exe`。
下文的 `coprogrammer` 指已安装版本，可替换为对应完整路径。
`doctor` 仅检查已知程序是否存在、指定环境变量是否有值，以及共享账本位置。
它不访问网络、不输出密钥、不读取客户端认证文件。

## 生成客户端配置

从实际要协作的项目目录运行；也可用 `--cwd /path/to/project` 指定项目。

```sh
coprogrammer integrations config --client codex --output .coprogrammer/clients/codex.toml
coprogrammer integrations config --client claude --output .coprogrammer/clients/claude.json
coprogrammer integrations config --client copilot --output .coprogrammer/clients/copilot.json
```

- Codex：将生成的 `mcp_servers.coprogrammer` 配置加入该项目 `.codex/config.toml`。
- Claude Code：将 `mcpServers.coprogrammer` 合并到项目 `.mcp.json`。
- GitHub Copilot / VS Code：将 `servers.coprogrammer` 合并到 `.vscode/mcp.json`。

保留已有服务条目。工具只生成独立文件，不自动改写全局设置或客户端授权状态。
输出路径已存在时会拒绝覆盖；重新生成请使用新文件名。

生成器固定使用当前 Python 和 CoProgrammer 包位置，采用隔离启动，避免目标项目
中的同名模块覆盖服务。配置包含本机绝对路径，不能原样分享给其他机器；移动源码、
虚拟环境或安装位置后需要重新生成。每个 worktree 应指向自己的项目目录。

启动客户端后，通过客户端的 MCP 管理界面检查工具是否出现。服务提供：
`manager_status`、`lease_request`、`lease_renew`、`lease_release`、`heartbeat`、
`contract_propose`、`manager_forecast`、`digest_branch`、`review_summary`。

仅声明同步 stdio tools 子集，协商支持 `2024-11-05`、`2025-03-26`、
`2025-06-18`、`2025-11-25`；不声明支持 2026 协议、远程 HTTP 或分布式锁。

## 让多个客户端共享协作状态

默认账本位于同一 Git 仓库主工作区的 `.coprogrammer/events.jsonl`。
Codex 和 Claude 即使位于不同 worktree 或子目录，也会解析到同一账本。
显式 `--state-dir` 保持原语义：相对路径基于当前目录，绝对路径使用指定位置。

```sh
coprogrammer manager lease request --holder codex-api --pattern 'src/api/**' --ttl-seconds 3600
coprogrammer manager heartbeat --agent codex-api --task 'Implement API change'
coprogrammer manager forecast --json
coprogrammer manager lease renew --actor codex-api --id LEASE_ID --ttl-seconds 3600
coprogrammer manager lease release --actor codex-api --id LEASE_ID
```

租约是协作约定，不是用户身份认证或文件访问控制。默认有效期一小时，允许
1 秒至 7 天；已过期租约不能续期，需要重新申请。旧版本无到期时间的租约保持有效，
由原持有人续期或释放。CLI 为兼容旧脚本，冲突仍返回退出码 0，必须读取提示；
MCP 调用应检查 `granted`。不确定的 glob 交集和大小写别名按可能冲突处理，可能误报。

升级时保留主工作区旧账本。发现其他已注册 worktree 根目录或当前目录祖先中存在
非空旧账本，会停止默认解析并报告位置，不自动合并或丢弃历史。检测不递归扫描其他
无关子目录；迁移前应检查团队曾配置的目录。新的事务保证适用于所有客户端都已升级
且使用同一本地账本的情况；旧进程应先退出，网络文件系统的锁行为需单独验证。

通用 `manager event append` 不再接受 `lease.*` 和 `decision.recorded`；改用专门命令，
确保状态检查与记录原子完成。旧版程序的任意日志写入不在新保证范围内。

## 交给 Claude、GLM 或 DeepSeek 分析

模型名称必须显式指定，以服务商账户当前可用名称为准；不会自动更换模型或区域。
凭据只从进程环境读取，不写入配置或报告：

| `--provider` | 默认 API 根地址 | 环境变量 |
| --- | --- | --- |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` |
| `glm` | `https://api.z.ai/api/paas/v4` | `ZAI_API_KEY`，其次 `GLM_API_KEY` |
| `deepseek` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |

可通过 `--base-url` 指定兼容的 HTTPS 根地址。GLM 中国入口可显式指定
`https://open.bigmodel.cn/api/paas/v4`，此时优先读取 `GLM_API_KEY`。
需自行确认该入口与账户地区、套餐一致；本次未完成该区域服务实测。
自定义地址会在显式发送时接收对应凭据，工具不跟随服务端重定向。

先生成本地预览，不需要密钥，也不产生模型调用：

```sh
coprogrammer review --provider deepseek --model YOUR_MODEL_ID \
  --base origin/main --head HEAD --output .coprogrammer/deepseek-preview.json
```

预览含实际目标地址、模型、待发送代码差异、证据摘要和输入范围。检查后，追加
`--send` 才会调用服务商，可能消耗账户额度：

```sh
coprogrammer review --provider deepseek --model YOUR_MODEL_ID \
  --base origin/main --head HEAD --send --output .coprogrammer/deepseek-review.json
```

切换为 `--provider glm` 或 `--provider anthropic` 可独立复核同一对提交。
各模型输出独立保存；系统不把多模型意见一致当作集成批准。
只有正常完成且通过结构校验的结果会保存为 `advisory`。不自动重试，避免重复计费。

证据只覆盖指定提交，不包含未提交修改。常见敏感路径（如 `.env*`、私钥文件）
不采集内容；这不是对普通源码内凭据的完整检测。报告和预览仍可能含私有代码，
应保存在忽略目录并检查后再发送。默认最多采集 64,000 字节 diff，截断或遗漏都会
明确标记；截断时所有文件建议强制暂缓。二进制文件仍需单独验证。

## GitHub PR 交接

```sh
coprogrammer github-context --pr https://github.com/OWNER/REPO/pull/123 \
  --output .coprogrammer/pr-context.json
coprogrammer review --provider glm --model YOUR_MODEL_ID \
  --pr-context .coprogrammer/pr-context.json --output .coprogrammer/pr-preview.json
```

GitHub 命令需要已安装并认证的 `gh`。它只读取 PR 元数据，绑定 GitHub 返回的完整
base/head SHA，不发布评论、不修改 PR、不执行 PR 文本。缺少对应本地提交时会停止，
需先从正确远端取得提交；fork 的 head 可能不在本地分支历史中。
文件列表不完整时拒绝生成交接。当前读取入口限定 github.com，未扩展企业实例。

现有 `github-comment` 仍是独立的显式发布命令；模型分析不会自动调用它。
现有 GitHub Action 继续生成确定性分支摘要，不自动发送代码到模型服务。

## 汇总多份审核结果

将已保存的审核工件对照同一组目标提交，未提供的审核继续显示为缺失：

```sh
coprogrammer review-summary --base origin/main --head HEAD \
  --review claude=.coprogrammer/claude-review.json \
  --review glm=.coprogrammer/glm-review.json \
  --expect deepseek --format markdown \
  --output .coprogrammer/review-summary.md
```

该命令完全离线，不会重新调用服务商。它保留缺失、预览、过期、无效和重复状态，
分别显示部分证据、待判断项、风险提示和文件建议分歧；身份与审核独立性未经认证。
可使用 `--fail-on-attention`，在报告生成后针对缺口或分歧返回退出码 1。
没有缺口也不代表批准合并。状态、路径规则和 MCP 示例见
[审核汇总指南](review-summary/README.md)。

## 生成待审核集成计划

```sh
coprogrammer integration-plan create --review .coprogrammer/deepseek-review.json \
  --output .coprogrammer/integration-plan.json
coprogrammer integration-plan validate .coprogrammer/integration-plan.json
```

计划重新核对提交、文件列表、diff 正文与摘要、覆盖范围和完成字段；分支移动或
证据被修改时必须重新分析。缺少正常完成元数据的旧手工工件会被拒绝，不能靠手动
补填字段证明服务商真的执行过审核。
它保留模型的保留、舍弃、重建、暂缓建议，列明受保护路径和人工决策，状态始终为
`draft`。验证命令保持空白，维护者填写可信项目检查后再执行；模型生成的文字只作为
验证名称保存。此版本不自动应用补丁、执行检查文字、创建集成 PR 或合并。

## 官方依据

核对日期：2026-09-26。客户端功能以实际安装版本为准。

- [Codex MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [GitHub Copilot MCP](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp-in-your-ide/extend-copilot-chat-with-mcp)
- [GitHub CLI PR JSON 字段](https://cli.github.com/manual/gh_pr_view)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create)
- [Z.AI Chat Completions](https://docs.z.ai/api-reference/llm/chat-completion)
- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)
- [MCP 2025-11-25 生命周期](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
