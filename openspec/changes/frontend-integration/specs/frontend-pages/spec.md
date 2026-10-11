# Capability: frontend-pages

## 需求
- 前端须提供三个页面：风险列表、提交详情、缺陷引入趋势看板。
- 风险列表按 `risk_score` 降序，支持 `min_risk` / `model_name` / 时间范围筛选与分页。
- 提交详情展示风险分与 SHAP 解释（`explanation` 的 `feature`/`contribution`/`direction`），及 14 项特征值分组。
- 趋势看板按 `week`/`month` 聚合展示平均风险与高风险数，单模型单维度。
- 所有页面统一三态（加载 / 空数据 / 错误），空数据不是错误。
- 所有请求带 `X-API-Key`；字段名与契约 `docs/contracts/api-format.md` 完全一致，前端不改名。

## 验收
- 三页面代码进 `frontend/src/views/` 并合入 main。
- 字段与 `docs/pages.md` 逐字一致（联调无字段错位）。
- 联调记录证明 API-01~04 跑通。
