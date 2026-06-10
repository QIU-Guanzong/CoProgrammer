# 战略备忘录：目标重读与对策

Last updated: 2026-06-10

本备忘录基于对仓库现有成果（`README`、`FRAMEWORK`、`COORDINATION_LIFECYCLE`、
`RESEARCH_LANDSCAPE`、`FEATURE_GAP_MATRIX`、`INTEGRATION_PATCH_DESIGN`、schemas、
CLI）的通读，以及 2026-06 的最新外部调研。目的是：(1) 重述目标；(2) 给出诚实的
形势判断；(3) 给出可执行的对策。

---

## 1. 目标重读（你们真正在做的事）

你们的命题已经很清晰，而且是对的：

> AI 时代的合并不是文本冲突问题，是语义集成问题。不要直接 merge 巨大的 AI 分支，
> 而要先理解 branch intent、提取核心 insight、丢弃噪声、在 main 约束下重建最小补丁。

围绕这个命题，仓库已经把它落成一个**贯穿始终的治理闭环**（开发前协议 → 开发中
通报 → 开发后消化 → 语义集成 → 反哺协议），并且有了五个 plane、八个 JSON schema、
一个能跑的 `digest/manager/manifest/integration-plan` CLI、一个 PR digest 的
GitHub Action。这是一个**协议 + 流程 + 工具**三位一体的雏形，方向不需要改。

需要改的是**定位的锐度和优先级** —— 因为外部世界在过去几周变了。

---

## 2. 形势判断：2026-06 发生了什么

你们的 `RESEARCH_LANDSCAPE.md` 截止 2026-05-25。这之后有四个变化直接影响策略。

### 2.1 编排层（orchestration）已经商品化、并且开始洗牌

并行 agent + git worktree/容器隔离 + 看板式调度，现在是**红海**：
Conductor（微软开源，MIT）、Sculptor（Imbue，容器隔离）、Composio
agent-orchestrator（已宣称"自动处理 CI 修复、merge 冲突、code review"）、
Claude Squad、Emdash、Baton… 而 Vibe Kanban 正在 sunset，Terragon 已于 2026-01
关停。

**含义**：不要把 CoProgrammer 的重心放在"再做一个并行 agent 编排器/看板"。那一层
正在被大厂和大量 OSS 填满，且死亡率很高。你们 `FEATURE_GAP_MATRIX` 里"不自建
runtime、消费上游 agent 输出"的判断，现在比一个月前更正确，应该写得更硬。

### 2.2 你们的核心差异点被学术界量化验证了（利好）

- **AgentSpawn / Coherence Manager** 给出了一个和你们"语义集成层"几乎同构的三档
  模型，并且带了真实占比：auto-merge 15%（同文件不重叠行）、**semantic merge 73%
  （LLM 按 intent 调和重叠改动）**、escalation 12%（不可调和，必须人工）。
  → 这是对你们 Preserve/Drop/Rebuild/Defer/Reject 模型的强背书，也说明 73% 的量
  正落在你们瞄准的那一层。
- **AgenticFlict**（arXiv 2604.03551）：GitHub 上 AI agent PR 合并冲突的**大规模
  数据集**。→ 这是你们"AI 一次改很多文件 → 冲突变大"论点的直接经验证据，也是一个
  现成的 benchmark 来源。

**含义**：把这两篇纳入 `RESEARCH_LANDSCAPE` 和 `FAILURE_TAXONOMY`。AgentSpawn 的
三档占比可以直接作为你们 digest 风险分档和"该不该 rebuild"判定的先验。AgenticFlict
应成为你们第一个**离线评测集**——证明 digest/integration 比裸 merge 好，需要数据。

### 2.3 出现了真正贴脸的竞品：共享 spec / 治理式合并

- **Intent**：被描述为"第一个把多 agent 编码当作协调系统来做、用一个 shared spec
  作为所有 agent 单一事实源"的工具。→ 这和你们的 contract-first + 协议层 + Manager
  Plane **高度重叠**。
- **MergeLoom / "governed AI coding"**：直接打"受治理的 AI 编码"，和你们的
  protocol/CODEOWNERS/protected-path 叙事重叠。

**含义**：你们不再是这个空间里唯一清醒的人。窗口还在，但要加速，并且要把**别人
还没做扎实的那一段**（见 §3）作为护城河，而不是和 Intent 比"共享 spec"的概念。

### 2.4 公认的未解难题，正好是你们的靶心

调研里反复出现同一句话：现有 OSS 编排器"仍然把 task 对齐、冲突解决、合并决策留给
开发者"，且"没有任何工具能让多个 agent 跨服务围绕一个**持续演进的共享计划**协调"。

**含义**：编排层解决了"让 N 个 agent 同时跑且不互相踩"，但没解决"N 个分支回来后，
如何在不破坏主干架构的前提下，把有价值的部分有选择地、语义地集成回去"。这正是
CoProgrammer 的 Branch Intelligence + Semantic Integration 两个 plane。**这条护城河
依然空着。**

---

## 3. 对策：把重心压在三件事上

结论先行：**砍掉与编排器重叠的野心，把全部锐度压在"消化 + 语义集成 + 可证明的闭环"
上，并尽快拿出能证明价值的数据。**

### 对策 A：重新切分边界——明确"在编排器之下游"

把 CoProgrammer 定位成 **"Integration & Governance layer that sits *after* any
orchestrator and *before* the merge queue"**。

- 上游（不自建）：Conductor / Sculptor / Vibe Kanban / Claude Squad / Codex /
  Copilot Cloud Agent 产出分支。
- CoProgrammer（自建）：消费这些分支 → digest intent → 在最新 main 上重建最小补丁
  → 产出更小、更安全的 integration PR。
- 下游（不自建）：GitHub Merge Queue / GitLab Merge Trains / Mergify 做最终落地。

**行动**：在 README 顶部画这张"上游 / CoProgrammer / 下游"三段图，并明确给
Conductor、Sculptor、Vibe Kanban 各写一个 1 段的"如何把它们的 worktree 分支喂给
CoProgrammer digest"的衔接说明。这会把你们从"又一个编排器"里区分出来。

### 对策 B：把"可证明"做出来——用 AgenticFlict 建评测

目前最大的风险不是没想清楚，而是**没有数字证明 digest/语义集成确实更好**。
竞品（Intent / AgentSpawn）已经在抛占比数据了。

**行动（这是接下来 2–3 周最高优先级）**：
1. 拉取 AgenticFlict 数据集（AI agent PR 冲突），选一个可复现子集。
2. 定义三条基线对比：裸 `git merge` / 结构化 merge / CoProgrammer digest+integration。
3. 指标：冲突自动消解率、保留有效 insight 的召回、引入回归的比例、reviewer 需要
   人工判断的条目数。
4. 把结果写成 `docs/EVAL_REPORT_*.md`，并对齐 AgentSpawn 的 15/73/12 三档，看你们
   在 73% 那一档上能不能做得更准。
没有这一步，协议再漂亮也只是叙事；有了这一步，你们就有了论文 + 开源 README 的硬核。

### 对策 C：MVP 收敛——先把"消化"这一刀磨利，暂缓全自动重建

你们的 `INTEGRATION_PATCH_DESIGN` 已经很完整（patch primitive 优先级、安全规则）。
但全自动 `llm_patch` 重建是重活且高风险，不要在证明价值之前投入。

**建议的落地顺序（在现有 CLI 基础上）**：
1. **Digest 质量**：让 `digest` 真正能区分"核心改动 / 噪声重构 / 契约改动 / 风险"。
   现在 CLI 1600 行已能跑，重点是把 intent 抽取和 contract-sensitive 检测做准——这
   是 reviewer 真正会用的那一格。
2. **Integration plan 半自动**：digest → 自动生成 Preserve/Drop/Rebuild 草案，人审。
   只实现 `git_apply` + `cherry_pick` + `manual` 三个确定性 primitive；
   `structural_search_replace`（接 ast-grep/Comby）和 `llm_patch` 标为 future。
3. **Integration record 闭环**：每次集成后落 `integration-record.json`，并自动产出
   一条"建议的协议更新"（新 protected path / 新 contract test）。把闭环跑通一次，
   哪怕是手动触发，也比五个 plane 都半成品强。
4. **Manager Plane 暂以本地 event log 为准**，不急着上云控制面——那是 §2.1 红海的
   隔壁，且不是你们的差异点。

### 对策 D（开发中通报层）：心跳要"高信号、低噪声"，并接住 worktree 现实

你们已经有 `agent-heartbeat`、`workspace-lease`、`contract-change` schema。结合
CodeCRDT（observation-driven coordination）的思路，开发中通报层的关键不是让 agent
互相聊天，而是**把"谁在改哪些路径、哪个共享契约正在承压"变成可预测冲突的结构化事件**。

**行动**：
- lease 以**路径前缀**为粒度做 advisory 锁，重叠即生成 `decision.requested`，这正好
  对接编排器的 worktree 模型（每个 agent 一个 worktree/分支）。
- 提供一个 `coprogrammer manager forecast`：基于当前 leases + 已声明 contract changes，
  **在 PR 之前**预测路径/契约冲突。这是"开发中"层唯一值得现在就做的高价值功能，因为
  它把冲突从"merge 时爆炸"提前到"编码时预警"，是编排器没覆盖的。

---

## 4. 取舍清单（要做 / 不要做）

**要做**
- 三段式定位图（上游/本体/下游）+ 与主流编排器的衔接说明。
- AgenticFlict 评测 + 对齐 AgentSpawn 三档的 EVAL 报告。
- Digest 质量 + 半自动 integration plan + integration record 闭环跑通一遍。
- PR 前的 conflict forecast。
- 把 AgentSpawn、AgenticFlict、CodeCRDT、Intent 纳入 landscape/failure taxonomy。

**先不要做**
- 自建并行 agent 编排器 / 看板 / 容器隔离（红海，非差异点）。
- 全自动 `llm_patch` 重建（证明价值前不投）。
- 云端 Manager 控制面 SaaS（隔壁红海，过早）。
- 通用 AI code reviewer（你们自己也已经判断"集成而非替代"）。

---

## 5. 一句话定位

> CoProgrammer 不是又一个并行 agent 编排器。它是编排器与 merge queue **之间**缺失的
> 那一层：把多个 AI agent 产出的分支，**消化成可安全融入 main 的语义补丁**，并用一个
> 协议闭环让团队的主干架构原则随每次集成自我强化。

---

## 6. 待补充的外部参考（建议加入 RESEARCH_LANDSCAPE 的 Sources）

- AgenticFlict: A Large-Scale Dataset of Merge Conflicts in AI Coding Agent Pull
  Requests on GitHub — arXiv 2604.03551
- AgentSpawn / Coherence Manager（auto-merge 15% / semantic merge 73% /
  escalation 12% 三档模型）
- CodeCRDT: Observation-Driven Coordination for Multi-Agent LLM Code Generation —
  arXiv 2510.18893
- Multi-agent Collaboration with State Management — arXiv 2605.20563
- Intent（shared-spec 单一事实源的多 agent 协调器）
- MergeLoom（governed AI coding 叙事，直接竞品候选）
- Conductor（微软开源，确定性编排）/ Sculptor（Imbue，容器隔离）/
  Composio agent-orchestrator（已含冲突/CI/review 自动化）—— 上游编排层参照
