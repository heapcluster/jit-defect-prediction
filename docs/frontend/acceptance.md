# 前端验收功能板块（达到什么效果）

> 验收人：sober / 蒋励 ｜ Sprint：Sprint 1（三页面 MVP）→ Sprint 3（测试）

## 板块 F1：三页面可演示

- **效果**：风险列表 / 提交详情 / 趋势看板 三个页面均能打开并展示真实（或预置）数据，构成完整用户场景。
- **证据**：Demo Day 现场演示三页面 + 联调通过记录。
- **一票否决**：第四个页面（模型管理/用户设置）做了反而稀释完成度——课程只要求三页面。

## 板块 F2：字段映射一致

- **效果**：页面每个字段都能在 `docs/backend/api-spec.md` 响应里找到；无自创字段。
- **证据**：字段对照核对表（pages.md 映射表逐行打勾）。

## 板块 F3：三态齐全

- **效果**：加载中 / 空数据 / 请求失败 表现正确；**空数据不是错误**（文案与后续操作不同）。
- **证据**：三态各一测试用例 + 截图。

## 板块 F4：阈值统一

- **效果**：风险着色阈值（`≥0.5`/`≥0.3`）只在 `pages.md` 一处定义，三页统一；`high_risk_count` 用后端值不重算。
- **证据**：代码搜索确认无第二处硬编码阈值。

## 板块 F5：联调通过

- **效果**：前端按契约联调，字段对得上，鉴权头带齐。
- **证据**：联调记录 / 接口返回截图。

## 板块 F6：前端测试

- **效果**：三态 + 错误码 + 字段一致性有测试（课程测试实践 40 分）。
- **证据**：测试文件 + 运行结果。

## 三端联调 · 前端要求（2026-10-23 定稿）

**目标**：不刷新页面即可完成「选提交 → 看解释 → 换模型重预测」，三态齐全。

1. `api/index.js` 补 `postPredict(commitHash, modelName?)` → `POST /api/predict`，body `{commit_hash, model_name?}`。
2. 详情页加「重新预测」：模型下拉列**后端实际加载成功的交付模型** `lr_v1` / `rf_v1` / `xgb_v1`（`pages.md` §6 已裁定 MVP 不新增 `/api/models`，清单由前端维护；下拉列 8 个会因 `MODEL_DIR` 缺 `.pkl` 直接拿到 40001）。返回后刷新 `risk_score` / `model_name` / `predicted_at` / `explanation` 四个字段；其中 `predicted_at` 仅 `POST /api/predict` 返回（`GET /api/commits/{hash}` 不含），故只在预测成功后展示，详情首次加载时显示「—」。
3. `explanation` 渲染为横向条形图：正负贡献分色，显示特征名、数值、direction；不得直接打印 JSON。
4. `frontend/.env.local` 写 `VITE_API_KEY`（与后端 `API_TOKEN` 一致），否则全部 40100。
5. 三页面浏览器走查并截图：加载中 / 空数据（空态非报错）/ 接口失败（可重试）；风险阈值 0.5 与 0.3 的口径只在 `docs/frontend/pages.md` 一处定义。
6. 实跑 `npm run test:unit`、`npm run lint`、`npm run build`，结果与走查记录写入 `docs/frontend/frontend-integration-log.md`。
