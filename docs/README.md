# JIT 缺陷预测 · docs 文档地图

> 版本 2.1 ｜ 更新 2026-10-11 ｜ 主笔 蒋励 ｜ 审核 苏哲勋
> 文档只分 **6 个包**：`backend` `frontend` `model` `repo` `design` `common`。其余设计/文档已全部并入这 6 包。

## §0 强制合入规则（jolly326 的 docs PR）

> 文档线在 `docs/` 下提的 PR（无论 **jolly326 还是 蒋励** 主笔），**sober 必须无条件合入**：不得 Request changes、不得拒绝、不得挂起，只能 Approve 或 Comment。
> 依据 `repo/collaboration.md` §3.7。本规则本身即课程「需求变更经 OpenSpec 记录」的文档侧落地。

## 权威边界

- **任务在飞书、代码在仓库**：需求范围/背景在飞书《产品需求文档》《产品设计文档》；代码边界/契约/映射/手册在 `docs/`。
- 任何结论必须落到文档或 Issue；只在聊天里说过的决定 = 没定。

## 0.5 项目全貌：6 大模块 + 在线/离线双层（先读这句，避免误判「项目太简单」）

课程《项目要求》列了 **6 大功能模块 + 工程化**；**你看到的「4 张表 / 4 个接口」只是「在线服务层」的正确范围，不是项目全貌**。系统工作量约 90% 在离线管线（数据采集 → SZZ 打标 → 14 维特征 → ≥8 种模型 → SHAP 解释），在线层只负责把它「加载 + 展示」。

| 课程模块 | Epic | 落在哪个包 | 真工作量 |
|---|---|---|---|
| 数据采集与仓库解析（Git 克隆 / SZZ / 持久化） | A | `model/` + `data_model/` | 重（离线） |
| 特征工程（Kamei 14 + 语义可选） | B | `model/` | 重（离线） |
| 模型训练与评估（≥2 类 ≥8 种 / 两类指标 / 时间切分） | C | `model/` | 重（离线） |
| 预测与解释（概率 + SHAP 归因） | D | `backend/` + `model/` | 中 |
| 查询接口 | E | `backend/` | 4 接口（在线） |
| 可视化前端（风险列表 / 趋势看板） | F | `frontend/` | 3 页面（在线） |
| 工程化（分支 / 评审 / CI-CD / 插件化） | — | `repo/` + `design/engineering.md` | 本模块补齐 |

**在线服务层（4 表 / 4 接口 / 3 页面）是「方案 A+C 跨线交付」的必然结果**：模型离线算好 → 交 `prediction_result.csv` + `.pkl` → 后端加载展示。所以在线库只需 4 张表（`commit`/`commit_label`/`commit_feature`/`prediction`），不是偷工。工程化（CI/CD、插件化）设计见 `design/engineering.md`；离线重活在 `model/README.md` §4。

## 1. 六个包导航

### `backend/`（吕建江）
- `README.md` 总览 ｜ `api-spec.md` 四接口/鉴权/错误码/非功能 ｜ `implementation.md` 四张图+分步 ｜ `openspec-compliance.md` 后端改动走 change ｜ `acceptance.md` 后端验收板块

### `frontend/`（刘帅华）
- `README.md` 总览 ｜ `pages.md` 三页面字段映射+三态+阈值 ｜ `implementation.md` 三页面+联调+分步 ｜ `openspec-compliance.md` ｜ `acceptance.md` 前端验收板块

### `model/`（蒋励）
- `README.md` 总览 ｜ `data-pipeline.md` 九步链路/版本固定/复现 ｜ `training-eval.md` 8 模型/2 类/两类指标 ｜ `explanation.md` SHAP 解释 ｜ `a2-4-correction.md` S6+1 判据方向 ｜ `openspec-compliance.md` ｜ `acceptance.md` 模型验收板块 ｜ `feature-columns.md` 14 项特征口径

### `repo/`（苏哲勋）
- `README.md` 总览 ｜ `collaboration.md` 分支/PR/开发/Issue 规范 ｜ `git-pr.md` 分支与 PR 速查 ｜ `kanban.md` 看板字段 ｜ `defect-management.md` 缺陷管理 ｜ `weekly-reports.md` 周报规范 ｜ `openspec-workflow.md` SDD 流程 ｜ `sprints.md` Sprint 日历 ｜ `user-story-traceability.md` 27 条故事挂接 ｜ `catchup-ledger.md` 进度台账 ｜ `demo-script-sprint1.md` Sprint1 演示脚本

### `design/`（全员）
- `README.md` 总览 ｜ `architecture.md` 架构 ｜ `database.md` 四表 ER ｜ `diagrams.md` 四张图(含生成方式) ｜ `non-functional.md` 安全/性能/可靠/易用 ｜ `prototype.md` 低保真原型 ｜ `sprint0-scope.md` 系统边界与代码线边界 ｜ `data-fields.md` 库表字段详表 ｜ `engineering.md` **工程化：分支/评审/CI-CD/插件化**

### `common/`（公共）
- `README.md` 总览 ｜ `course-requirements.md` 课程要求与映射 ｜ `openspec-rules.md` 每次改动必须走规范 ｜ `writing-norms.md` 写作规范 ｜ `team-charter.md` 团队章程 ｜ `dev-handbook.md` 开工手册 ｜ `glossary.md` 术语表 ｜ `templates.md` 模板基线 ｜ `acceptance-overview.md` 跨包验收总览

## 2. 课程要求 → 文档 索引

| 课程要求 | 看这里 |
|---|---|
| 技术架构 / 数据库设计 / 核心图 / 非功能 / 原型 | `design/` 各文件 |
| **工程化（分支规范 / 代码评审 / CI-CD / 插件化）** | `design/engineering.md` + `repo/collaboration.md` `repo/git-pr.md` |
| OpenSpec SDD（propose→specs→design→tasks） | `common/openspec-rules.md` + `repo/openspec-workflow.md` |
| 每次改动必须走规范（含字段一致铁律） | `common/openspec-rules.md`（各包 `openspec-compliance.md`） |
| GitHub 协作 / PR 审阅 / 看板 / 缺陷 / 周报 | `repo/` 各文件 |
| 8 模型 / 2 类 / 两类指标 / SZZ / 14 特征 | `model/` 各文件 |
| 四接口 / 鉴权 / 在线预测 / 解释 | `backend/api-spec.md` `backend/implementation.md` |
| 三页面 / 可视化 / 联调 | `frontend/` 各文件 |
| MVP / 27 用户故事 / Sprint 节奏 | `repo/user-story-traceability.md` `repo/sprints.md` |
| 评分维度（产品/SDD/过程/测试） | `common/acceptance-overview.md` |

## 3. 一票否决风险（课程判定缺陷）

见 `common/acceptance-overview.md` §3：字段名不一致 / 性能无分位数证据 / 只报一类指标 / 改周报模板 / 数据版本浮动 / 随机切分 / PR 无非作者审阅 / 改需求只改码不改规格 / 第四个页面。

## 4. 变更日志

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-11 | 2.1 | 前置「项目全貌：6 模块 + 在线/离线双层」回应「项目是否简单」；新增 `design/engineering.md`（工程化：分支/评审/CI-CD/插件化）并纳入导航与索引 |
| 2026-10-11 | 2.0 | 重构成 6 包；合并 contracts/implementation/templates/weekly/ 及根级散件；各包补负责人/交付物/OpenSpec 合规/验收板块；加 §0 强制合入规则 |
| 2026-09 初 | 1.x | 散件文档期（已废弃） |
