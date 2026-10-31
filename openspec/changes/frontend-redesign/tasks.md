# frontend-redesign — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无独立 design.md ｜ 规格：`specs/ui/spec.md`
> 负责人：frontend 刘帅华 ｜ 创建：2026-10-27 ｜ 状态：进行中（以任务勾选和证据为准）
> 关联需求：无（界面优化）
> 统一格式见 `docs/common/openspec-task-template.md`；末尾「测试与验证」为强制板块。


## 1. 共享组件

- [x] 1.1 `components/PageHint.vue`：一句话引导 + 右侧主操作 — `frontend/src/components/PageHint.vue`
- [x] 1.2 `components/StatCard.vue`：概览指标卡（未知显示 `—`）— `frontend/src/components/StatCard.vue`
- [x] 1.3 `components/RiskTag.vue`：风险等级标签（优先后端 `risk_level`）— `frontend/src/components/RiskTag.vue`
- [x] 1.4 `utils/features.js` 补 `FEATURE_LABELS`（14 项中文名，对齐后端）— `frontend/src/utils/features.js`

## 2. 页面重构

- [x] 2.1 `App.vue` 导航加「质量看板」，标题集中一处 — `frontend/src/App.vue`
- [x] 2.2 `RiskList.vue`：三条重复提示合并为 PageHint + 三张卡（条数交给分页器）；空库引导精简 — `frontend/src/views/RiskList.vue`
- [x] 2.3 `CommitDetail.vue`：风险结论一行 + 操作归拢 + 特征中文名 — `frontend/src/views/CommitDetail.vue`
- [x] 2.4 `PrList.vue`：两张概览卡（去掉与筛选栏、表格重复的模型与总数）+ 同步提示压成一行 — `frontend/src/views/PrList.vue`
- [x] 2.5 新增 `QualityBoard.vue`：指标卡 + 混淆矩阵 + 阈值校准 — `frontend/src/views/QualityBoard.vue`
- [x] 2.6 `TrendBoard.vue`：补 PageHint 与三张 `StatCard`，明细表降为「画不出折线」时的兜底 — `frontend/src/views/TrendBoard.vue`
- [x] 2.7 `QualityBoard.vue`：校准结果就地显示在阈值卡，去掉独立「最近一次校准」卡 — `frontend/src/views/QualityBoard.vue`
- [x] 2.8 `PrDetail.vue`：去掉与布局标题重复的 `el-page-header`，改用 PageHint + 返回按钮 — `frontend/src/views/PrDetail.vue`

## 3. 接线

- [x] 3.1 `api/index.js` 补 `getQuality` / `getQualityDataset` / `postCalibrate` / `getConfig` / `putConfig` — `frontend/src/api/index.js`
- [x] 3.2 `router/index.js` 注册 `/quality` — `frontend/src/router/index.js`

## 测试与验证（强制板块）

### 1. 单元测试

- 前端已有 vitest（`frontend/tests/*.spec.js`，`npm run test:unit`）；#81 起即存在，此前 tasks 里「无单测框架」的记录已失效并订正
- 命令：`cd frontend; npm run test:unit` ｜ 证据：**7 个文件 / 27 条全通过**
- 本轮同步修掉两处存量红：`risk.spec.js` 阈值口径（0.3 → 0.2）、`RiskList.spec.js` 的 api mock 缺 `getCommitsCoverage`/`getHealth`
- 构建：`cd frontend; npm run build` ｜ 证据：`✓ built in 3.57s`，无编译错误

### 2. 集成测试

- 后端全量：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/ -o addopts="" -q`
- 证据：`313 passed`（本 change 未改后端，用于确认无回归）

### 3. 验收测试

- 按 `specs/ui/spec.md` 逐条走：首屏结构 → 空库引导 → 降级状态卡 → 未预测 PR → 质量看板无样本 → 校准未改善 → 特征中文名
- 证据：`npm run build` 产物 + 五个页面人工检查

### 4. 非功能验证

- 冗余度：`RiskList` 顶部提示由 3 条降为 1 条引导 + 3 张卡；`CommitDetail` 的「尚未预测」由 2 处降为 1 处；`PrList` 同步说明由 2 行降为 1 行
- 第二轮密度收敛：`TrendBoard` 删掉与折线重复的明细表（仅 <2 点时兜底）、`PrList` 卡片 4→2、`PrDetail` 不再出现两次「PR 详情」与重复的模型名、`QualityBoard` 去掉一次性的「最近一次校准」卡
- 契约：`MUST NOT` 改接口；后端测试 313 passed 不变即证明

### 5. 已知缺口与后续计划

- 未做前端单元测试（项目无测试框架）
- 未做暗色主题与移动端适配
- 质量看板未展示按时间窗口的质量趋势（`GET /api/quality` 支持 start/end，但页面暂未提供选择器）
