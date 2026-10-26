# CoProgrammer 云端开发交接

## 原始升级

基线为 `d9e55083b506013f2c38380cb0d3f35a61e92a37`。原始 Codex
CLI task harness 经私有云端交接后继续开发；原始提交链及对象校验回执保留
在项目的私有开发证据中。本公开说明不包含内部协调标识、账户信息或运行日志。

适配器使用既有 JSON task/result 契约，要求明确执行，默认 read-only；
父 worker 持有 claim、保护文件范围并完成任务。失败不自动重试，inbox
消息由既有客户端/MCP 流程明确接收。未改变协议、schema 或 CI。

## 当前可审阅成果

后续升级加入安装后 discovery/version/help 诊断、失败和中断报告、打包使用
指南，以及独立的 Claude Code task-only adapter。客户端与模型 provider
保持分离；GLM/DeepSeek 标签不配置账户，也不证明连通。

安装后的命令见 [Codex 指南](../CODEX_TASK_HARNESS.md)、
[Claude 指南](../CLAUDE_TASK_HARNESS.md)与
[前台 worker 指南](../FOREGROUND_WORKERS.md)。默认测试使用离线合成进程。
真实模型、Windows native 和 GUI 验收需分别提供真实证据，不能由 fixture
测试代替。

## 公开移交

公开 review 提交以核验后的最终源码文件树为基础；私有原始提交历史保留，
不将内部交接材料作为公开 Git 历史上传。由 GitHub 连接器创建独立审阅分支
和 draft PR，保持 main 不变。合并、发布包和账号/provider 配置需分别处理。
