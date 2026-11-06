# feature-addons-sprint3 — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/defect-visualization/spec.md`、`specs/fix-suggestion/spec.md`
> 负责人：跨线（蒋励统稿） ｜ 创建：2026-10-11
> 关联需求：G1-1 / G1-2（G1-3 / G1-4 已移出）
> 状态：进行中（以任务勾选和证据为准）

## 1. 立项与看板
- [x] 1.1 看板新增 Sprint 3 两行（缺陷可视化定位 `reczz28LeOxoj2h2` / 高质量修复建议 `reczz28LeOxolfuA`），「规格变更或任务」列填 `feature-addons-sprint3`，可点开；迭代=Sprint 3、状态=未开始、优先级=中
- [x] 1.2 飞书《产品需求文档》第五章已含「可选附加功能 Epic G」：`G1-1`（缺陷可视化定位，行级）/ `G1-2`（高质量修复建议），并同步入《需求范围表》（见 PRD v0.8/v0.9 变更日志）；状态写实
- [x] 1.3 课程 2026/10/12 新增两项可选附加功能：`G1-3`（公开缺陷数据集加载与质量治理）/ `G1-4`（预训练语义特征建模），已登记入 PRD 第五章与《需求范围表》；看板新增 Sprint 3 两行（G1-3 `reczz28MirZUzuxq` / G1-4 `reczz28MirZV4HRJ`），关联本 change

## 2. 缺陷可视化定位（Sprint 3）
- [ ] 2.1 详情页接入文件级 SHAP / 行级高亮
- [ ] 2.2 联调记录入库（前置：前端三页面 F3 完成）

## 3. 高质量修复建议（Sprint 3）
- [ ] 3.1 历史修复提交检索脚本（data_model/）
- [ ] 3.2 高风险提交 Top-K 建议输出与联调

## 4. 公开数据集加载与质量治理（G1-3）—— 已于 2026-10-13 移出本 change
> **已移出**：G1-3 由 `public-dataset-quality` 承接。本节仅保留迁移记录，不属于本 change 的待办或验收范围。

## 5. 预训练语义特征建模（G1-4）—— 已于 2026-10-13 移出本 change
> **已移出**：G1-4 由 `semantic-feature-mainline` 承接。本节仅保留迁移记录，不属于本 change 的待办或验收范围。

## 6. 立项文档（2026-10-13）
- [x] 6.1 设计文档 5.3.3 / 5.3.4 展开 G1-3 / G1-4 详设（飞书设计文档 v0.9）
- [x] 6.2 G1-3/G1-4 后续分别转入 `public-dataset-quality`、`semantic-feature-mainline`；本 change 的 `specs/` 仅保留 G1-1/G1-2
---

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-assessment-guide.md`；模板见 `openspec/TASKS_TEMPLATE.md`。
> 本 change 的待实施功能仅为 G1-1/G1-2；G1-3/G1-4 的测试与验收分别见 `public-dataset-quality`、`semantic-feature-mainline`。下列结果以当前 change 为范围，未执行项如实保留。

### 1. 单元测试
| 项 | 内容 |
|---|---|
| 覆盖对象 | G1-1 行级定位降级逻辑；G1-2 修复建议检索与空态 |
| 测试文件 | G1-1/G1-2 → `frontend/tests/`（拟新增；当前未执行） |
| 用例数与结果 | 0 条（未开始） |
| 复现命令 | `cd data_model && python -m pytest -q`；`cd frontend && npm run test:unit` |
| 异常 / 边界用例（最低要求） | G1-1 行级数据缺失 → 降级到提交级并提示，**不报错**；G1-2 无依据 → 返回空态，**不编造建议** |

### 2. 集成测试
| 项 | 内容 |
|---|---|
| 集成范围 | G1-1/G1-2 的返回数据 ↔ 提交详情页；缺少后端数据时显示明确空态 |
| 测试文件 | `frontend/tests/`（待新增），真实后端联调记录见 `docs/common/integration-log.md` |
| 用例数与结果 | 0 条（未开始） |
| 关键断言 | 不伪造行级证据或修复建议；现行接口未提供对应字段时明确记为未实现，不改现行 `docs/api/` 契约 |

### 3. 验收测试
| 项 | 内容 |
|---|---|
| 验收依据 | `specs/defect-visualization/spec.md`、`specs/fix-suggestion/spec.md` |
| 用例数与结果 | 0 条（未开始） |
| 证据归档 | 实测页面与接口证据待记录在 `docs/common/integration-log.md` 或对应 PR；目前未提供 |

### 4. 非功能验证
| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 附加功能不进入交付链路（MVP 契约不变） |
| 安全 | 否 | 本 change 不再负责公开数据集下载；若新增对外输入另评估 |
| 可靠 | 是 | G1-1 行级证据缺失时降级到提交级 |
| 易用 | 是 | 降级提示与空态文案 |

### 5. 已知缺口与后续计划
| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| G1-1/G1-2 功能任务 2.1–3.2 未完成 | 当前接口与页面没有可验收的行级证据和修复建议 | 蒋励 / 刘帅华 | 由飞书看板确定 |
| 测试计划已立但无实测证据 | 功能尚未交付 | 同上 | 对应功能 PR 中补 |
| G1-3/G1-4 的文献与实验缺口 | 已移交独立 change，本 change 不验收 | 蒋励 | 见 `docs/common/research-notes.md`，由对应 change 追踪 |
