# 多平台协作升级任务说明

## 问题

用户要求继续升级 CoProgrammer，特别结合 Codex、Claude、GitHub、GLM、DeepSeek。
当前并发租约可能重复获批，工作区默认账本分离，MCP 异常请求可能终止服务，
分支报告尚缺可调用的模型分析接口。

## 预期结果

- Codex、Claude Code、GitHub Copilot 可生成各自原生 MCP 配置。
- 工作区共享协调状态，租约申请原子化，具有到期、续期和释放机制。
- Claude、GLM、DeepSeek 提供显式调用的分析接口，默认只生成本地请求预览。
- GitHub PR 的只读交接绑定 base/head 提交；分析结果可转成待审核集成计划。
- 配置探测、模拟接口测试、真实客户端连接、远程模型调用分别报告验证状态。

## 允许修改路径

- `src/coprogrammer/`、相关 `tests/`
- `README.md`、`docs/MULTI_PLATFORM_QUICKSTART.md`、本任务交付记录

## 禁止修改路径

不因本任务修改其他项目、全局客户端配置、账户凭据、生产配置。
协议和 schema 保持现有格式；不自动批准契约、架构或最终合并。

## 共享契约

CLI 与 MCP 共用租约业务函数。新接口以增量命令交付。
默认共享状态发现需保留主工作区旧日志；发现多个旧日志必须报告冲突。
模型输出仅作为建议，集成计划始终生成 draft。

## 验证命令

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m coprogrammer config validate
PYTHONPATH=src python3 -m coprogrammer manifest validate docs/upgrade-v0.2/change-manifest.json
```

## 交接说明

本任务由用户授权开发，最终架构/契约审阅仍待维护者完成。
不以测试通过代替服务商真实调用成功、客户端授权完成或版本发布。
