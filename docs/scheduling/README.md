# 跨平台调度与开发中沟通

CoProgrammer 把同一台机器上、共享 Manager 的开发窗口接入一个任务队列。
CLI 与 MCP 使用同一套任务状态、路径租约和消息记录。Codex、Claude Code、
Copilot 的配置生成器已提供；使用 GLM 或 DeepSeek 的其他客户端，只要支持
这套本地 MCP 工具，也可以参与。模型名称是标签，不能证明已连接对应服务。

## 运行流程

```text
注册窗口 → 创建有范围的任务 → 检查依赖、客户端、窗口和路径占用
                                      ↓
                             原子领取任务与路径租约
                                      ↓
                      修改前 guard → 开发 / 沟通 / 续期
                                      ↓
                      提交前 guard → 完成并释放 → 人工审阅
```

并行开发使用不同 Git worktree。同一工作目录同时只允许一个已领取任务，
即使两个任务修改不同文件，也避免共享 Git 暂存区带来的干扰。
同一仓库的 worktree 默认共享 Manager；独立 clone、不同机器不自动共享。
首次接入时将本地运行状态 `.coprogrammer/` 加入 `.gitignore` 或本地 Git
exclude，避免消息和状态被提交；已被 Git 跟踪的文件不会因忽略规则自动移除。

每个窗口注册一次，日后恢复用 `pulse`：

```sh
# API worktree 中的 Codex 窗口
coprogrammer manager session register --session codex-api --client codex --task api-v2

# UI worktree 中的 Claude Code 窗口
coprogrammer manager session register --session claude-ui --client claude --task ui-v2
```

在 Codex 窗口定义任务。被依赖的任务必须先创建，避免循环依赖：

```sh
coprogrammer manager task create --session codex-api --id api-v2 \
  --title '调整 API 响应' --pattern 'src/api/**' --client codex
coprogrammer manager task create --session codex-api --id ui-v2 \
  --title '同步调用方' --pattern 'src/ui/**' --depends-on api-v2 --client claude
coprogrammer manager task claim --session codex-api --id api-v2
```

保存返回的 `claim_id`，替换后续示例的 `claim_...`。省略 `--id` 时按创建顺序
领取当前窗口可执行的第一个任务；不做模型能力评分或费用调度。
`--client` 对注册的客户端标签进行大小写不敏感匹配，不代表身份认证。

```sh
# 修改前检查计划操作的具体路径
coprogrammer manager task guard --session codex-api --id api-v2 \
  --claim claim_... --file src/api/routes.py

# 长任务在有效期内主动更新窗口状态和租约
coprogrammer manager session pulse --session codex-api --status working
coprogrammer manager task renew --session codex-api --id api-v2 \
  --claim claim_... --ttl-seconds 3600

# 提交前检查当前已暂存、未暂存、未忽略的未跟踪文件
coprogrammer manager task guard --session codex-api --id api-v2 \
  --claim claim_... --working-tree
```

guard 检查窗口、工作目录、分支、领取令牌、活跃租约及文件范围。重命名同时
检查原路径和新路径；符号链接的实际目标也必须在范围内。每次最多检查 128
个不同路径。具体路径使用正斜杠 `/`，拒绝含反斜杠的输入，避免把实际文件名
误当成目录路径。Git 仓库须在命名分支上领取任务，拒绝 detached HEAD；非 Git
目录可以参与本地协作，但不具备分支检查。正常提交推进分支不会使领取失效。

guard 是执行当时的协作检查，不拦截之后的文件写入，也不检查代码语义。
不要绕过失败检查继续编辑。提交前还需执行项目要求的验证及人工审阅。

## 完成、暂停和回收

完成时填写真实工作结果、实际验证及剩余事项：

```sh
coprogrammer manager task finish --session codex-api --id api-v2 \
  --claim claim_... --summary '填写已完成内容、实际运行的检查及剩余事项'
```

`finish` 原子释放该任务的租约，将状态设为 `done`，其依赖任务可以领取。
这是作者报告的完成状态，不会验证提交、测试、合并或审阅结果，也不会把
API worktree 的代码自动搬到 UI worktree；交接时必须明确提交和集成步骤。

暂时让出工作用 `task release`，参数与 finish 相同；任务回到 `queued`，
文件不会自动还原。切换分支前先完成或释放任务。结束窗口前先处理任务和
租约，再 `session pulse --status closed`，关闭后不能恢复同一会话 ID。

租约到期或被移除后，任务仍保持已领取，旧令牌不可继续使用。创建者先确认
原窗口已停止修改、保存并协调已有改动，再主动回收：

```sh
coprogrammer manager session pulse --session codex-api --status working
coprogrammer manager task reclaim --session codex-api --id api-v2 \
  --summary '原窗口已停止；说明已保存的改动和重新领取前的处理'
```

只有创建者可以回收，且原租约必须已失效。回收不停止旧进程；重新领取生成
新令牌。若创建者会话已关闭，本预览没有管理员接管工具，需要维护者处理。

`task board` 展示任务、依赖、路径冲突、租约失效和负责人不可用原因。
看板的 `ready` 仅表示任务依赖与路径检查通过；具体窗口领取时还会检查
客户端资格、会话新鲜度及工作目录是否空闲。

## 任务讨论与变化等待

参与窗口在用户授权的协作范围内发送进度、问题、交接及回复。消息的 `--task`
使用队列中的同一个任务 ID，便于关联；消息也允许不在队列中的普通任务标签。

```sh
coprogrammer manager message send --from codex-api --to claude-ui \
  --task api-v2 --kind handoff --key api-handoff-v1 --body-file handoff.txt
coprogrammer manager message thread --session claude-ui --task api-v2
coprogrammer manager message ack --session claude-ui --id msg_...
coprogrammer manager sync --session claude-ui
# 先用 sync --after <next_cursor> 读完 has_more 页，再等待
coprogrammer manager wait --session claude-ui --after evt_... --timeout-seconds 25
```

`message thread` 保留自己发出和收到的消息及当前回执；分页按发送顺序。
已读不等于 ACK，ACK 只确认收悉。回复使用 `--reply-to msg_...`，保留原任务
及双方参与者。任务讨论不是所有参与者均可见的广播群聊。

wait 返回 `changed`、`pending` 或 `timeout` 以及新的 `next_cursor`。
有未确认消息时立即返回；处理并确认后再等待。若 `has_more` 为真继续读取。
会话变旧、租约过期也可能触发状态变化。等待期间释放锁；同一个 MCP 服务
进程按序处理请求，其他窗口的独立进程可以继续写入。
wait 不刷新会话、不续租、不自动确认，也不唤醒空闲的模型客户端。

## MCP 对照与平台边界

| CLI | MCP |
| --- | --- |
| `manager task create / claim / renew` | `task_create` / `task_claim` / `task_renew` |
| `manager task guard / board` | `task_guard` / `task_board` |
| `manager task finish / release / reclaim` | `task_finish` / `task_release` / `task_reclaim` |
| `manager wait` | `manager_wait` |
| `manager message thread` | `message_thread` |

MCP 参数以 `task_id` 对应 CLI 的 `--id`，`claim_id` 对应 `--claim`，
`working_tree: true` 对应 `--working-tree`。工具使用相同核心和事件记录。

这次实现了本地任务调度和客户端主动拉取的沟通通道。真实客户端登录、原生
跨会话唤醒、远程机器、启动模型进程，以及 GLM/DeepSeek 在线调用均不由这些
测试证明。实际支持范围和后续方向见[研究依据](research.md)及[验证记录](validation.md)。
