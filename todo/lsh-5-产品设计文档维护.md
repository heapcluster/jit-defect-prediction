# lsh — 飞书《产品设计文档》维护与同步

> 任务编号：L-5｜负责人：lsh｜板块：设计文档｜优先级：P1
> 依赖：各线模块供稿、neon 排期｜关联评分：软件开发过程实践（40）
> 承接：原 sober S-5「设计文档（技术部分）」统稿职责已并入本任务

## 目标

维护飞书《产品设计文档》为**当前系统的设计基线**：系统架构、API 清单、库表设计、模块详设与现行实现一致，并承担技术部分统稿。本任务只管这一份文档；《产品需求文档》归 `L-4`。

## 依据（口径与分工）

> 代码怎么写、字段/接口叫什么 → 仓库 `docs/overview.md` 与 `docs/api/`、`docs/database/`、`docs/model/`、`docs/web_page/`、`docs/function_point/`
> 需求范围、功能说明、用户故事、页面原型与交互 → 飞书《产品需求文档》（`L-4`）
> 系统设计、架构、API 清单、库表设计 → 飞书《产品设计文档》（本文档）
> 任务分配、进度、截止 → 飞书《工作周报》「本周计划」表
> 文档与契约对不上，以契约为准；要改代码先提 OpenSpec change，不以「顺手改文档」绕过评审。

- 仓库总览 `docs/overview.md` 自述为最新设计唯一权威来源，是本次同步的比对基准；其第 65 行提示现库可能仍残留旧表旧列，**同步时以文档口径为准，不照抄代码残留**。
- 与 `L-4` 的分界：本文档写「系统怎么实现」，`L-4` 写「要做什么、用户怎么用」；页面技术设计在本文档，页面原型与功能说明在 `L-4`。两文档各自维护版本号与变更日志，不互相复制正文。

## 实读基线（2026-11-07，飞书文档技能 `outline` → `section`）

| 项 | 现状 |
|---|---|
| 文档 | `YdgBdOjm5otdvxx6P8nceSY2n1f`，v0.11 / revision 718 |
| §4.3 API 清单 | 仅 4 个（API-01~04） |
| §4.4 数据库概要 | 仅 4 表（`commit`/`commit_label`/`commit_feature`/`prediction`），含自增 `id`，ER 图引用不存在的 `docs/design/data-fields.md` v1.4 |
| §5.4.2 前端 | 「三条路由 / 三个页面 / 三个接口封装」+ 三页面流程图、时序图 |
| §5.1.6 | 是 2026-10-05 的 PR #44 / #47 / #52 补记，属历史修改记录却留在详细设计正文 |
| §二 变更日志 | 版本顺序错乱（v0.9 排在 v0.8 前、v0.10 夹在其后）；§一 版本信息写 v0.10，与日志末行 v0.11 不一致 |
| 附录 A / B | ActiveMQ v1 基线归档与 ActiveMQ → Camel 迁移说明，未标注为历史归档 |

## 要完成什么（技术部分统稿 + 逐节同步）

「现文档」为 2026-11-07 实读结果，逐节同步：

| 章节 | 现文档 | 应同步为（依据） |
|---|---|---|
| §4.3 API 清单 | 4 个（API-01~04） | 7 个路由模块 / 11 个端点：`commits`(2)、`models`、`trends`、`predict`、`sync`(2)、`figures`、`health`(3)；契约在 `docs/api/` 7 篇，OpenAPI 由 FastAPI 运行时产出而非随附静态文件（`backend/app/main.py`、`docs/api/*.md`） |
| §4.4 数据库概要 | 4 表 `commit`/`commit_label`/`commit_feature`/`prediction`，含自增 `id` | 5 表 `commit`/`model`/`commit_feature`/`model_figure`/`prediction`；`commit_label` 已并入 `commit_feature`（`is_bug_inducing` + `labeled_at`）、`runtime_setting` 删除、去自增 `id` 与 `updated_at`；ER 图与 Mermaid 同步重画（`infra/schema.sql`、`docs/database/`） |
| §4.1 / §4.2 架构与模块 | 旧分层 | 按当前 `backend/` + `frontend/` + `data_model/` 实现重画；明确 PR 门禁 / 质量看板 / 人工标注 / 测试集评估独立页**均已下线**（`docs/overview.md`） |
| §4.5 工程化 | PR 评审 / CI-CD 旧口径 | 按 `.github/workflows/ci.yml` 现状写；分支保护与 review 要求按仓库 ruleset 实际配置 |
| §5.1.4 错误码表 | 泛述 | 以 `backend/app/errors.py` 五码为准：`0 / 40001 / 40100 / 40400 / 50000`，包络 `{code,message,data}` |
| §5.4.1 模型线 | 待训练 / 8 模型 | 4 线 25 模型（expert / semantic / fused 各 8 + e2e 1），**在线仅 expert 8 个**；在线特征固定 Kamei 14 维（`docs/model/`、`backend/app/config.py`、`feature_order.txt`） |
| §5.4.2 前端 | 三条路由 / 三个页面 / 三个接口封装 | 4 个业务页 + 1 个 404 兜底、5 条路由、7 个 API 模块；菜单仅 3 项（详情页由列表进入，**菜单 3 项 ≠ 页面 3 个**）；补模型性能看板取数 `GET /api/figures` 与 `GET /api/commits?with_features=1&is_test=1`；三页面流程图 / 时序图重画为四页（`frontend/src/router/index.js`、`App.vue`、`docs/web_page/`） |
| §5.3 可选附加模块 | G1-1~G1-4 并列 | 按 `openspec/changes/` 实际状态标注：G1-1 / G1-2 仍为 Sprint 3 可选；G1-3 公开数据集治理、G1-4 语义特征已提升为承诺范围 / 模型线主线，不再写「仅立项未实现」 |
| 图源标注 / 附录 A、B | 指向 `docs/design/diagrams.md`、`docs/design/data-fields.md` 等失效路径 | 现行契约路径改为 `docs/api` / `docs/database` / `docs/model` / `docs/web_page` / `docs/function_point` + `docs/overview.md`；附录 A（ActiveMQ v1 归档）与附录 B（迁移说明）显式标为**历史归档，不代表当前实现**，与 §4 / §5 现行设计隔离 |

**技术部分统稿**（原 `S-5` 职责）：系统分层、核心流程图、关键链路时序图由各线供稿汇总到本文档；lsh 负责统稿与一致性，不替各线撰写其模块技术内容；发现偏差先提 OpenSpec change。

## 修改记录归并 / 删除冗余（必做）

1. **§二 版本顺序重排**：按版本号升序（现 v0.9 排在 v0.8 前、v0.10 夹在其后）；同一天同版本多条合并；压缩「仅登记未改正文」「老师裁定过程」「图源标注补齐」等过程流水为一条；§一 版本信息由 v0.10 与日志末行 v0.11 对齐。
2. **§5.1.6 移出详细设计正文**：内容是 2026-10-05 的 PR #44 / #47 / #52 与 Issue #46 / #50 补记，属历史修改记录而非当前设计。浓缩为 §二 一行或移入「附录 C · 历史实现变更归档」；§5.1 正文只保留仍成立的结论（模型加载 `joblib.load` + 特征数自检、五码错误包络、14 列特征顺序）。
3. **失效路径表述加溯源标注**：变更日志 v0.10「修正 19 处失效路径」所列 `docs/backend/api-spec.md`、`docs/design/data-fields.md`、`docs/model/feature-columns.md`、`docs/frontend/pages.md`、`docs/design/diagrams.md` 在当前仓库均已不存在。保留该条史实但加注「为 2026-10-13 六包重构时的路径，现行契约见 …」，正文一律用现行路径。
4. **附录 A / B 标为历史归档**：加显著标注「ActiveMQ v1 基线 / 迁移说明仅供溯源，不代表当前实现」，避免与 §4 / §5 现行设计混读；史实不删。
5. **统一格式**：变更人 / 日期 / 版本号 / 图源标注格式与《产品需求文档》一致；清理临时协作提示块；本次修订只在 §二 追加 1 行新版本记录。

> 需求文档侧「两处变更日志归一」「§二 16 条聚合」归 `L-4`，不在本任务重复处理。

## 范围

**做：** 本文档正文撰写 / 修订 / 统稿、逐节同步到当前实现、图与图源标注维护、变更日志归并、文档↔契约一致性核对记录。

**不做：**
- 不改仓库代码、不删史实数据、不把仓库契约搬到飞书另立一套说法。
- 不编造数据或结论；实测指标一律引用仓库已有报告。
- 不写需求范围 / 用户故事 / 页面原型与功能说明（归 `L-4`）。
- 不替各线撰写其模块技术内容，lsh 只统稿。

## 当前未完成

- 移交 lsh 后尚未与 `docs/overview.md` 及现行契约做全量一致性核对。
- §4.3 / §4.4 / §5.4.2 三处主口径仍停留在旧版（4 API / 4 表 / 3 页面）。
- 第 4 个页面（模型性能看板）在本文档的模块详设、流程图、时序图中均缺失。
- 修改记录归并 5 项全部未做。
- 原 `S-5` 技术部分统稿的「章节 → 撰写人」owner 尚未重新对齐。

## 输入

- 飞书《产品设计文档》（token 见上）。
- 仓库权威口径：`docs/overview.md`、`docs/api/`(7)、`docs/database/`(5)、`docs/web_page/`(4)、`docs/function_point/`(4)、`docs/model/`(4)。
- 实现证据：`backend/app/main.py`、`backend/app/errors.py`、`backend/app/config.py`、`frontend/src/router/index.js`、`frontend/src/App.vue`、`infra/schema.sql`、`data_model/pipelines/expert/models/feature_order.txt`。
- `openspec/changes/` 活跃 change、各线模块供稿、neon 的《工作周报》排期。

## 输出（交付物）

- 更新后的《产品设计文档》正文、图与图源标注、变更日志。
- 四页前端模块详设（含模型性能看板取数）与重画的流程图 / 时序图 / ER 图。
- 「文档 ↔ 契约一致性核对表」（章节 / 契约路径 / 结论 / 是否已走 change）。
- 技术部分统稿记录（各线供稿章节 → 撰写人 → 汇总结论）。
- 修改记录归并说明（哪几处合并、哪几处移出正文、史实保留位置）。

## 依赖与前置

- 前置：`docs/overview.md` 与现行契约已冻结；各线模块供稿到位。
- 协作：技术细节向 **蛋神的蛋** 确认；排期找 **neon**；仓库文档规范 / 断链治理问 **sober**（`S-3`）；前端页面口径与 **刘帅华** 供稿核对；与 `L-4` 对齐两文档边界。
- 阻塞项：`openspec/config.yaml` 里「前端三个页面」、三契约旧路径等断链由 `S-3` 修复后再定稿引用。

## 验收标准

- [ ] §4.3 = 11 端点 / 7 模块，§4.4 = 5 表且 ER 图一致，§5.4.2 = 4 业务页 + 5 路由。
- [ ] 全文不再引用 `docs/backend/api-spec.md`、`docs/design/*`、`docs/frontend/pages.md` 等失效路径。
- [ ] 变更日志：版本顺序正确、同版本多条已合并、§5.1.6 已移出详细设计正文、附录 A / B 已标历史归档、§一 与 §二 末行版本号一致、本次修订追加 1 行。
- [ ] 一致性核对表逐节有结论；口径冲突要么消除、要么已登记 OpenSpec change 编号。
- [ ] 技术部分能讲清一条完整预测链路，图与实现一致；各线供稿 owner 已登记。
- [ ] 未改动任何仓库代码 / 契约文件；史实数据零删除。

## 约束（用 agent 执行）

- 改动影响口径时，先提 OpenSpec change，不以「顺手改文档」绕过评审。
- 用飞书文档技能按章节局部读取（`outline` → `section`），不要整篇覆写；编辑走 `docs +update`。
- 归并修改记录 = 合并表述 / 统一编号 / 移出正文，**不是抹掉历史**。
- 同步以 `docs/overview.md` 口径为准，不照抄代码中残留的旧表旧列。
