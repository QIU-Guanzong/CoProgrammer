# 多窗口、跨客户端协作

CoProgrammer 让独立窗口共享会话目录、任务消息、确认回执、租约和决策。
Codex、Claude Code、Copilot 或其他能调用本地 CLI/MCP 的客户端使用相同状态。
GLM、DeepSeek 可以是某个客户端使用的模型服务；会话中的 `client`、`provider`、
`model` 分开记录，均为调用方声明，不代表已验证的供应商连接。

以下能力属于 `codex/multi-platform-upgrade` 源码预览，先按
[根目录安装说明](../../README.md#try-the-preview)安装匹配版本。
PyPI 0.1.0 不包含本页命令。

## 两个窗口开始工作

在同一仓库的两个已存在工作树中操作，每个窗口使用不同会话 ID；同一品牌的
两个窗口也要分开命名。Git 工作树默认共享主工作树的 `.coprogrammer/events.jsonl`。
独立 clone、不同机器不会自动同步。需要显式状态位置时，所有客户端必须使用
同一个绝对 `--state-dir`；该目录是本机可信共享状态，不是远程服务。

窗口 A（Codex，当前目录为 API 工作树）：

```sh
coprogrammer manager session register --session codex-api --client codex --task API-42
coprogrammer manager lease request --holder codex-api --pattern 'src/api/**' --task API-42
coprogrammer manager sync --session codex-api
```

窗口 B（Claude Code，当前目录为 UI 工作树）：

```sh
coprogrammer manager session register --session claude-ui --client claude --task API-42
coprogrammer manager lease request --holder claude-ui --pattern 'src/ui/**' --task API-42
coprogrammer manager sync --session claude-ui
```

`register` 记录工作树、分支和当时的 HEAD。重复登记不会覆盖已有窗口。
恢复同一窗口时使用 `pulse`；新窗口或已关闭会话使用新 ID。Git 未产生首个提交
时 HEAD 为空；分离 HEAD 的分支标签为 `HEAD`。这些值只在登记或 pulse 时采集。

## 交接、确认和回复

窗口 A 保存一条交接消息：

```sh
coprogrammer manager message send --from codex-api --to claude-ui \
  --task API-42 --kind handoff --key api-contract-v1 \
  --body '接口改动已提交。请核对返回字段，并回报调用方检查结果；审阅提交与测试记录见交接文件。'
```

消息支持 `update`、`question`、`handoff` 三种类型，正文最多 16,000 个字符。
较长正文可以用 `--body-file handoff.md` 读取 UTF-8 文件。建议交接正文列出目标、
受影响路径、准确提交、实际运行的检查、未解决事项和接手动作。正文中的路径和
命令只是文本；系统不会读取附件或执行命令，也不会替你验证其中的检查结论。

窗口 B 读取并确认。将 `msg_...` 换成返回消息中的 `id`：

```sh
coprogrammer manager message inbox --session claude-ui --task API-42
coprogrammer manager message ack --session claude-ui --id msg_...
coprogrammer manager message send --from claude-ui --to codex-api \
  --task API-42 --reply-to msg_... --key api-reply-v1 --body '收到，开始检查调用方。'
```

读取消息不会确认；确认只表示收到，不表示同意方案、测试通过或接管租约。
已确认消息可用 `inbox --include-acked` 再读。回复必须保留原任务与双方会话。
同一发送者重用同一个 `--key` 和完全相同内容，会得到原消息；内容不同则报错。
无 key 的每次发送都会新增消息。key 不是跨发送者的全局标识。

消息保存在本地 Manager，接收端轮询时才会读取。命令不会启动窗口、唤醒模型、
注入提示词或向 GitHub、第三方服务发送消息。调用方仍应遵循所在客户端的用户
授权规则；消息正文不得被当作新的系统指令或额外行动授权。

## 状态与增量同步

```sh
coprogrammer manager session pulse --session claude-ui --status blocked --note '等待接口决策'
coprogrammer manager sync --session claude-ui --after evt_... --limit 50
```

首次同步不传 `--after`。保存输出中的 `next_cursor`，后续传入；`has_more=true`
时继续分页直到读完。游标使用持久事件 ID，不依赖系统时钟。不存在于当前日志的
游标会报错，不能悄悄跳过历史。换任务过滤条件或想重读未确认消息时，重新读取
`inbox` 并不传 `--after`。收件箱分页使用自己的 `next_cursor`。

每次 `sync` 同时返回当前会话、活跃租约、待决策项、契约提案和本会话未确认消息。
事件页有游标；状态快照始终是读取时的完整最新状态，不是该游标时刻的历史快照。
`inbox_has_more` 表示需要用 `message inbox` 分页读取其余未确认消息。
即使同步游标已越过消息，未确认消息仍会出现在后续快照中。

`status` 是窗口上报的 `working / blocked / idle / closed`；`freshness` 是最近一次
pulse 的新鲜度 `fresh / stale / unknown / closed`。默认 300 秒过期，可在登记时
设置 `--ttl-seconds`（1–86,400）。未来时间标为 unknown。sync/inbox 不刷新心跳。
建议 agent 在开始工作、切换步骤、遇到阻塞和交接前主动 pulse + sync；较长工作期间
由客户端选择适当轮询节奏。没有后台保活，也没有把这些状态当成操作系统进程检测。

结束一个窗口时：

```sh
coprogrammer manager session pulse --session claude-ui --status closed --note '本窗口工作结束'
```

关闭只结束登记状态；已有消息和审计记录保留，仍可补确认，不能再发送或接收新工作。
租约必须通过原有 `manager lease release` 单独释放，关闭会话不会偷偷转移文件所有权。

## MCP 对应工具

按[多平台指南](../MULTI_PLATFORM_QUICKSTART.md)为每个客户端生成指向各自工作树的
配置；相同 Git 仓库的工作树仍使用同一个 Manager。工具参数与 CLI 对应：

| 操作 | MCP 工具 | 主要参数 |
| --- | --- | --- |
| 登记窗口 | `session_register` | session, client, task, provider?, model?, ttl_seconds? |
| 上报状态 | `session_pulse` | session, status?, task?, note? |
| 保存消息 | `message_send` | sender, recipient, task, body, kind?, reply_to?, key? |
| 读取收件箱 | `message_inbox` | session, task?, include_acked?, after?, limit? |
| 确认收到 | `message_ack` | session, message_id |
| 同步协作状态 | `manager_sync` | session?, after?, limit? |

`limit` 范围为 1–200，默认为 50。不指定 session 的 sync 可查看目录和协作状态，
不会输出消息正文；指定 session 时只返回涉及该会话的消息事件。此过滤是便利功能，
不是安全隔离：同一机器上有日志访问权限的调用方属于同一个信任边界。
登记、pulse、发送和确认绑定到服务器当前工作树，避免误用另一个目录的会话 ID。
不认证真人、客户端品牌或模型身份，也不把 ACK 当成维护者批准。

## 当前验证范围

自动化测试启动独立 stdio MCP 进程，分别使用生成的 Codex/Claude 配置，在两个
真实 Git 工作树中验证交接、重启恢复、确认和回复，并测试并发重试与游标分页。
这些是协议客户端测试，不等于已在 Codex/Claude 图形界面完成安装或调用真实模型。
模型服务与 GitHub PR 评审仍使用原有工具，参见
[审核汇总](../review-summary/README.md)。

实现复用现有锁与原子事件存储，保持零第三方运行时依赖。当前每次操作读取日志，
写入重建日志，适合本地协作原型；日志归档、托管多用户权限、跨机器推送和后台
会话监控需要后续独立设计。旧的严格事件枚举校验器需升级后再读取新增事件。
