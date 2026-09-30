# 审核交接示例

以下内容使用临时仓库和合成审核工件演示；未调用 Claude、GLM 或 DeepSeek。
工件中的完成字段仅为测试数据，不是服务商执行凭证。检查建议尚未执行。

## 离线审核汇总（待人工审核）

身份及审核独立性未经验证；仅覆盖选定的已提交内容，未检查远端 PR 状态。

Base: main (1c0b03988c1a3d96e80861c868f77e4be888b118)
Head: feature (b0d76d1596d0f53a4aa2ea6325d8792d44f5d9a0)

需要处理未完成审核、覆盖缺口、风险或建议分歧。

## 审核工件

| Label | Status | Provider / model | Coverage | Notes |
| --- | --- | --- | --- | --- |
| sample\-claude | current | anthropic / synthetic\-fixture | collected | Evidence matches the selected committed target\. |
| sample\-glm | current | glm / synthetic\-fixture | collected | Evidence matches the selected committed target\. |
| sample\-deepseek | missing |  /  |  | Expected review artifact was not supplied\. |

## 审核说明

以下风险和待执行检查来自审核建议，不表示测试已运行或通过。

### sample\-claude

合成审核建议，用于展示交接状态。
- 待执行检查：验证新旧调用方读取版本的行为。

### sample\-glm

合成审核建议，用于展示交接状态。
- 风险：旧调用方的兼容性尚需确认。
- 待执行检查：验证新旧调用方读取版本的行为。

## 文件建议

| File | Reviewer | Decision | Reason | Disagreement | Coverage gap |
| --- | --- | --- | --- | --- | --- |
| api\.py | sample\-claude | preserve | 保留新增版本标记，便于调用方识别。 | true | true |
| api\.py | sample\-glm | rebuild | 建议先保留旧版本兼容入口，再提交新标记。 | true | true |
