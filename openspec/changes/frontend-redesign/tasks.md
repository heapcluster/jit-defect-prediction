# frontend-redesign — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/ui/spec.md`
> 创建：2026-10-27 ｜ 状态：进行中

## 1. 共享组件

- [x] 1.1 `components/PageHint.vue`：一句话引导 + 右侧主操作 — `frontend/src/components/PageHint.vue`
- [x] 1.2 `components/StatCard.vue`：概览指标卡（未知显示 `—`）— `frontend/src/components/StatCard.vue`
- [x] 1.3 `components/RiskTag.vue`：风险等级标签（优先后端 `risk_level`）— `frontend/src/components/RiskTag.vue`
- [x] 1.4 `utils/features.js` 补 `FEATURE_LABELS`（14 项中文名，对齐后端）— `frontend/src/utils/features.js`

## 2. 页面重构

- [x] 2.1 `App.vue` 导航加「质量看板」，标题集中一处 — `frontend/src/App.vue`
- [x] 2.2 `RiskList.vue`：三条重复提示合并为 PageHint + 四张卡；空库引导精简 — `frontend/src/views/RiskList.vue`
- [x] 2.3 `CommitDetail.vue`：风险结论一行 + 操作归拢 + 特征中文名 — `frontend/src/views/CommitDetail.vue`
- [x] 2.4 `PrList.vue`：四张概览卡 + 同步提示压成一行 + RiskTag — `frontend/src/views/PrList.vue`
- [x] 2.5 新增 `QualityBoard.vue`：指标卡 + 混淆矩阵 + 阈值校准 — `frontend/src/views/QualityBoard.vue`

## 3. 接线

- [x] 3.1 `api/index.js` 补 `getQuality` / `getQualityDataset` / `postCalibrate` / `getConfig` / `putConfig` — `frontend/src/api/index.js`
- [x] 3.2 `router/index.js` 注册 `/quality` — `frontend/src/router/index.js`

## 测试与验证

### 单元测试

- 前端无单测框架（项目现状），以构建与人工走查为准
- 命令：`cd frontend; npm run build`
- 证据：`✓ 2266 modules transformed`、`built in 15.55s`，无编译错误

### 集成测试

- 后端全量：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/ -o addopts="" -q`
- 证据：`313 passed`（本 change 未改后端，用于确认无回归）

### 验收测试

- 按 `specs/ui/spec.md` 逐条走：首屏结构 → 空库引导 → 降级状态卡 → 未预测 PR → 质量看板无样本 → 校准未改善 → 特征中文名
- 证据：`npm run build` 产物 + 五个页面人工检查

### 非功能验证

- 冗余度：`RiskList` 顶部提示由 3 条降为 1 条引导 + 4 张卡；`CommitDetail` 的「尚未预测」由 2 处降为 1 处；`PrList` 同步说明由 2 行降为 1 行
- 契约：`MUST NOT` 改接口；后端测试 313 passed 不变即证明

### 已知缺口

- 未做前端单元测试（项目无测试框架）
- 未做暗色主题与移动端适配
- 质量看板未展示按时间窗口的质量趋势（`GET /api/quality` 支持 start/end，但页面暂未提供选择器）
