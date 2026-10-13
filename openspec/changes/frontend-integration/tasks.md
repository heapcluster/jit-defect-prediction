# frontend-integration — 任务清单

## 1. 立项（F2）
- [x] 1.1 本 change 进 `openspec/changes/frontend-integration/`（propose → apply），看板「规格变更或任务」列可点回
- [x] 1.2 飞书 PRD 第五章增补前端三页面 User Story（**F Epic**，非 C —— PRD 第五章分层为 A–F + G，见 `repo/user-story-traceability.md`），状态写实

## 2. 脚手架与接口层（F3 前置）
- [x] 2.1 `npm create vue@latest` + 装 `element-plus`/`echarts`/`axios`；配 `/api` 代理 → PR #33 已合入 main：`frontend/package.json` 四依赖齐、`vite.config.js` 将 `/api` 代理到 `localhost:8000`、`.env.example` 给出密钥示例（真实密钥走 `.env.local`，不入库）
- [x] 2.2 `src/api/request.js`（**实际为 `.js` 而非 `.ts`**：本组前端不使用 TypeScript，已在 tasks 中订正口径）：axios 实例 + `X-API-Key` 拦截器 + 统一解包 `code===0` + 错误码分发三态

## 3. 三页面（F3）
- [x] 3.1 风险列表 `views/RiskList.vue`（**实际文件名为 `RiskList.vue`，非 `CommitList.vue`**）：排序固定 `risk_score` 降序、筛选、分页、点击整行跳详情；字段与 `docs/frontend/pages.md` §2 逐条对应
- [x] 3.2 提交详情 `views/CommitDetail.vue`：风险值 / 模型版本 / SHAP 解释条（`increase` 右、`decrease` 左，按 `|contribution|` 降序取前 8）/ 特征值五维度分组
- [x] 3.3 趋势看板 `views/TrendBoard.vue`：ECharts 折线（`avg_risk`）+ 三项汇总（总数 / 高风险数求和、平均风险按 `commit_count` 加权）；数据点 < 2 不画折线

> ⚠️ 3.1–3.3 于 2026-10-13 实现，**尚未过 lint/build 实跑校验**（本机 `frontend/node_modules` 未安装，需 `npm ci` 后执行 `npm run lint` 与 `npm run build`），也**未与后端联调**。按课程「只勾 tasks ≠ 功能合格」，此三条标「已实现」而非「已验收」，联调通过后才可在周报记完成。

## 4. 联调（F4）
- [ ] 4.1 起后端 `:8000`，按 `repo/demo-script-sprint1.md` 跑通 API-01~04
- [ ] 4.2 联调记录入库 `docs/frontend/frontend-integration-log.md`（原写 `docs/implementation/...`，该目录在六包重构后不存在）
- [ ] 4.3 PR 合入 main，看板行指向本 change
