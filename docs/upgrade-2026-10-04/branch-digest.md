# v0.3 integration review

Latest main baseline: `ef81bcbe1072444f9bbc94822251614621471f4c`.
Source branch: `codex/v0.3-workspace-handoff`.

- Preserve: all current main scheduling, messages, MCP, Skills, provider-review
  and setup behavior. PR #1 already squash-merged the old branch commits.
- Drop: old branch versions and any reapplication that removes newer main files.
- Rebuild: additive dispatch preview, content-bound checks, portable handoff
  and receiving-clone comparison on latest main.
- Compatibility: existing events, task lifecycle and setup semantics unchanged.
  Only CLI can execute an explicit command. New MCP tools are read-only.
- Review fixes: bind claimed/completed handoffs to the owner's original checkout;
  isolate all project Git calls from inherited redirection; reject duplicate,
  nonfinite, oversized or inconsistent artifact input.
- Protected matches: CLI and package metadata. Current user authorization covers
  the next version and merging after verification; no protected schema, auth,
  migration or Manager architecture change is included.
- Validation: focused acceptance passed; complete source/wheel and existing
  cross-platform PR checks must pass before release. See `validation.md`.
- Rollback: revert the integration PR and pin the previous package version;
  no event/config migration is necessary.

The generated inventory below is a drafting aid; TODO sections are not approvals.

# 分支消化报告

生成时间: `2026-10-03T17:10:58+00:00`

Base: `origin/main`
Head: `WORKING_TREE`

## 分支意图

TODO: 说明这个分支要解决的问题。

## 核心贡献

TODO: 列出值得保留的思路、实验结果和实现决策。

## 变更文件

- `M` `README.md`
- `M` `README.zh-CN.md`
- `M` `docs/PLUGIN_QUICKSTART.md`
- `M` `plugins/coprogrammer/.claude-plugin/plugin.json`
- `M` `plugins/coprogrammer/.codex-plugin/plugin.json`
- `M` `plugins/coprogrammer/plugin.json`
- `M` `plugins/coprogrammer/skills/coprogrammer-active-sync/SKILL.md`
- `M` `pyproject.toml`
- `M` `src/coprogrammer/__init__.py`
- `M` `src/coprogrammer/assets/skills/coprogrammer-active-sync/SKILL.md`
- `M` `src/coprogrammer/assets/templates/handoff.md`
- `M` `src/coprogrammer/cli.py`
- `M` `src/coprogrammer/mcp_server.py`
- `A` `docs/VALIDATION_EVIDENCE.md`
- `A` `docs/WORKSPACE_HANDOFF.md`
- `A` `docs/upgrade-2026-10-04/change-manifest.json`
- `A` `docs/upgrade-2026-10-04/integration-plan.json`
- `A` `docs/upgrade-2026-10-04/research.md`
- `A` `docs/upgrade-2026-10-04/task-brief.md`
- `A` `docs/upgrade-2026-10-04/validation.md`
- `A` `src/coprogrammer/evidence.py`
- `A` `src/coprogrammer/workflow.py`
- `A` `src/coprogrammer/workflow_cli.py`
- `A` `src/coprogrammer/workflow_mcp.py`
- `A` `src/coprogrammer/workspace.py`
- `A` `tests/test_workspace_workflow.py`

## 提交摘要

- 未检测到提交。

## 契约与架构信号

- **构建/依赖**
  - `pyproject.toml`

## 风险等级

`medium`

## 受保护路径命中

- `pyproject.toml` matches `pyproject.toml` [medium] (package and entrypoint configuration; 需要 owner review)
- `src/coprogrammer/cli.py` matches `src/coprogrammer/cli.py` [medium] (CLI behavior affects PR digest generation)

## 噪声 / 非必要变更

TODO: 标记格式化扰动、大范围重写、临时调试、生成物或无关重构。

## 融合计划

TODO: 说明如何基于最新 main 重建最小安全补丁。

## 需要验证

- [ ] 格式化
- [ ] Lint 检查
- [ ] 类型检查
- [ ] 单元测试
- [ ] 集成测试
- [ ] 契约测试
- [ ] 受保护区域 owner review

## 需要人工判断

TODO: 列出不应交给自治 agent 决定的问题。
