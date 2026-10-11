# frontend-integration — 任务清单

## 1. 立项（F2）
- [ ] 1.1 本 change 进 `openspec/changes/frontend-integration/`（propose → apply），看板「规格变更或任务」列可点回
- [ ] 1.2 飞书 PRD 第五章增补前端三页面 User Story（C Epic），状态写实

## 2. 脚手架与接口层（F3 前置）
- [ ] 2.1 `npm create vue@latest` + 装 `element-plus`/`echarts`/`axios`；配 `/api` 代理
- [ ] 2.2 `src/api/request.ts`：axios 实例 + `X-API-Key` 拦截器 + 统一解包 `code===0` + 错误码分发三态

## 3. 三页面（F3）
- [ ] 3.1 风险列表 `views/CommitList.vue`（排序/筛选/分页/跳详情）
- [ ] 3.2 提交详情 `views/CommitDetail.vue`（风险分 + SHAP 解释条 + 特征分组）
- [ ] 3.3 趋势看板 `views/TrendBoard.vue`（ECharts 折线 + 汇总；点<2 不画）

## 4. 联调（F4）
- [ ] 4.1 起后端 `:8000`，按 demo-script 跑通 API-01~04
- [ ] 4.2 联调记录入库 `docs/implementation/frontend-integration-log.md`
- [ ] 4.3 PR 合入 main，看板行指向本 change
