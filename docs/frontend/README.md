# frontend 包（前端与可视化）· 刘帅华

> **你打开这个文件夹就能知道：你负责什么、最近要干什么、每次任务怎么干、改东西的红线在哪。**
> 包负责人：**刘帅华**（前端与可视化线）｜ 目录：`frontend/` ｜ 审核：吕建江、蒋励
> 配套依据：飞书《产品需求文档》Epic **F 前端可视化**；OpenSpec change `frontend-integration`；接口源 `../backend/api-spec.md`（契约三 v1.4）。

---

## 0. 👤 你的职责一句话

你是**前端与可视化线唯一负责人**：把后端四个接口变成「评审员看得懂、用得顺」的三个页面（风险列表 / 提交详情 / 缺陷引入趋势看板），并负责前后端联调。技术栈已定：**Vue 3 + Element Plus + ECharts**。

## 0.5 谁依赖你 / 你依赖谁（阻塞关系）

| 方向 | 对象 | 依赖什么 | 卡住的后果 |
|---|---|---|---|
| **你依赖** | `backend/`（吕建江） | `api-spec.md` 四接口 + 错误码 + 三态口径（联调唯一依据） | 接口未就绪 → 三页面拿不到数据 |
| **你依赖** | `model/`（蒋励） | `model/feature-columns.md` 14 项列名（详情页解释条与特征分组按此渲染） | 列名漂移 → 解释条静默空白 |
| **你依赖** | `repo/`（苏哲勋） | 分支模型 + PR 非作者审阅 + CI 门禁 | PR 无法合入 main |
| **被你依赖** | 演示 / 周报 | 三页面可演示 + 联调记录 + 录屏 | Sprint 1「至少 1 条界面→数据层完整流程」无法验收 |
| **被你依赖** | `design/addons.md` G1-1 / G1-2 | 行级定位与修复建议的展示层 | 附加功能无落地界面 |

## 1. 📋 你的任务清单（来自进度台账，带验收与下一步）

| # | 任务 | 验收标准（做到什么效果） | 状态 | 你下一步 |
|---|---|---|---|---|
| F1 | 合入 PR #33（Vue3+Vite 脚手架：三路由/axios/X-API-Key 鉴权头） | PR 进 main；`frontend/` 不再只有 README | ✅已完成 | 已合入，脚手架可用 |
| **F2** | 建 change `frontend-integration`（三页面+联调），走 propose→apply | change 进 `openspec/changes/`；看板可点回 | ✅已完成 | change 已具 proposal + `specs/frontend-pages/` + design + tasks（apply 已跑，未归档） |
| **F3** | 前端三页面实现（风险列表排序/筛选/分页、提交详情风险分+SHAP 归因、趋势看板） | 页面代码进 main；字段与 `api-spec.md` 一致 | 🔄进行中 | 2026-10-13 三页面已实现（`src/views/RiskList.vue`、`CommitDetail.vue`、`TrendBoard.vue`，共用常量与纯函数在 `src/constants.js`、`src/utils/`）；**待 `npm ci` 后跑 lint/build、待联调、待进 main** |
| **F4** | 前后端联调（对接 API-01~04，留联调记录） | 联调记录入库；详情页解释区非空 | ⬜未开始 | 前置 L1(#52) 已合入，blocker 解除；联调记录落 `docs/frontend/frontend-integration-log.md` |

> 实时状态以**飞书看板**为准。F3/F4 是 Sprint 1（10/23 验收）主交付，优先级最高。

## 2. 🚀 后续工作开展方式（每次接到任务的标准动作 · 必须走 OpenSpec）

1. **认领**：飞板置「进行中」。
2. **动接口/字段前先提 change**：页面要新字段 → **先改契约 / 提 change**，不要前端自己造（如「本次预测是否命中真实标签」接口不返回、页面也不显示）。
3. **提/续 change**：`frontend-integration` 已立，继续 `apply`；新需求另起 change。
4. **实现**：读 `pages.md`（三页面↔接口↔字段映射 + 三态 + 阈值），照 `implementation.md` 分步写 `views/*.vue`。
5. **自测**：三态（加载中/空数据/失败）各有表现；空数据不是错误；风险着色阈值只在 `pages.md` 一处定义（≥0.5 高 / ≥0.3 中）。
6. **联调**：起后端 `:8000`，按 `docs/repo/demo-script-sprint1.md` 跑通 API-01~04，记录入库。
7. **提 PR**：描述写 change id；请求**非作者成员**（苏哲勋）审阅。
8. **合入 + 回写**：合入 main → 看板完成 + 周报记证据。

> ⚠️ 课程硬要求：**改需求只改码不改规格 = 缺陷**；只勾 `tasks.md` ≠ 功能合格，要有运行/联调证据。

## 3. 🚫 你的红线

- **不碰**：接口格式（改走契约变更）、后端逻辑、数据库直连、自己算指标。
- **字段零自创**：页面展示字段必须与 `pages.md` / `api-spec.md` 一致。
- **模型下拉**：MVP 由前端维护已知模型版本清单，不新增 `GET /api/models`。
- **非作者审阅**：你的 PR 由苏哲勋审。

## 4. 本包交付物与课程对应

| 课程要求 | 本包落地 |
|---|---|
| 可视化前端（风险列表/趋势看板等） | 三页面 + ECharts |
| 产品须含用户可使用的界面/入口 | 三页面构成完整业务闭环 |
| 完整核心用户场景展示 | Demo Day 演示三页面 + 联调 |
| 单元测试（前端部分） | 三态与错误码处理、字段映射一致性测试 |

## 5. 子文件导航

- `pages.md` — 三页面 ↔ 接口 ↔ 字段映射 + 三态 + 阈值（契约三 + 页面映射）
- `implementation.md` — 三页面实现 + 联调 + 分步（F2/F3/F4）
- `openspec-compliance.md` — 前端改动如何走 change
- `acceptance.md` — 前端验收功能板块

## 6. 先读 common 里的哪几份

打开 `common/`：`openspec-rules.md`（每次改动必须走规范）、`dev-handbook.md` §前端落地、`team-charter.md`（分工与审阅人）。**common + 本文件 = 你开展工作的全部依据。**
