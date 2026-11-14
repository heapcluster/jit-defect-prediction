# 前端信息架构重构：提升引导性、去除冗余表述

## Why

功能补齐后，页面反而更难用，两个问题最突出：

1. **引导性弱**：进到 `/` 只看到一张表和一条长提示，不知道「该先做什么、看完下一步干什么」。空库时给的是两段技术说明 + 一条命令行，而不是一个明确的开始动作。
2. **表述冗余**：同一件事说两三遍。`RiskList` 顶部同时有「运行状态长句」「已预测覆盖长句」和「空库说明卡」；`CommitDetail` 的「尚未预测」在大字和标签各出现一次；`PrDetail` 同步提示铺两行。文案越长，用户越读不出重点。

另外 `quality-loop` / `ops-hardening` 交付的能力（质量指标、阈值校准、配置热更新）完全没有入口，页面上看不见就等于不存在。

本 change 只动前端：**统一页面结构、把引导压缩成一句话、给每组数字一个位置、补上质量看板**。

## What Changes

- **统一页面骨架**：`PageHint`（一句话说明 + 右侧主操作）→ `StatCard` 行（先看数）→ 筛选 → 内容。五个页面同一套结构，用户不需要每页重新找重点。
- **新增共享组件**：
  - `components/PageHint.vue`：唯一一处写「这页干什么」，右侧放主操作；
  - `components/StatCard.vue`：概览指标卡（标签 / 数值 / 一行注解）；
  - `components/RiskTag.vue`：风险等级标签统一（优先用后端 `risk_level`，没有才按分数兜底）。
- **新增「质量看板」`/quality`**：精确率 / 召回率 / F1 / 评估样本 四张卡 + 混淆矩阵 + 阈值（当前 vs 推荐）+「按标签校准」「应用推荐阈值」。
- **`RiskList` 重构**：三条重复提示合并为「一条 PageHint + 四张卡（当前结果 / 已人工确认 / 已预测覆盖 / 服务状态）」；空库卡片从两段说明 + 命令行精简为一句说明 + 同步控件。
- **`CommitDetail` 重构**：风险结论收成一行（大字 + 等级标签 + 模型 + 确认状态），标记/撤销与重新预测各归一处；14 项特征改显示中文名（悬停看原始字段）；删掉永远取不到的 `predicted_at` 展示。
- **`PrList` 重构**：四张卡（PR 总数 / 高风险 / 待预测 / 模型）；同步提示压成一行；风险列统一用 `RiskTag`。
- **`utils/features.js`** 补 `FEATURE_LABELS`（14 项中文名，逐字对齐 `app/explain.py`）。
- **`api/index.js`** 补 `getQuality` / `getQualityDataset` / `postCalibrate` / `getConfig` / `putConfig`。

## Capabilities

### Added Capabilities

- `ui`：页面引导结构、概览指标、风险标签、质量看板。

### Modified Capabilities

- `query-api`：不涉及后端契约（纯前端消费既有端点）。

## Impact

- 前端：新增 `components/{PageHint,StatCard,RiskTag}.vue`、`views/QualityBoard.vue`；重写 `views/{RiskList,CommitDetail,PrList}.vue` 与 `App.vue`；`router/index.js`、`api/index.js`、`utils/features.js` 调整。
- 后端：**零改动**（`quality` / `config` 端点已在上两个 change 交付）。
- 测试：无后端用例变化；以 `npm run build` 通过 + 五个页面人工走查为验收证据。

## 不做什么

- `MUST NOT` 引入新的 UI 框架或替换 Element Plus（只做结构与文案重构）。
- `MUST NOT` 改动任何接口字段、路径、错误码（本 change 前端唯一）。
- 不做暗色主题、移动端专门适配（当前为桌面运维/评审场景）。
- 不做图表库替换（趋势图仍用现有 `RiskTrendChart`）。
- 不在前端复制后端阈值：风险等级优先用后端返回的 `risk_level`，前端常量只作兜底。
