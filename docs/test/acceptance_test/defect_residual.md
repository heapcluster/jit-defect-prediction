# 缺陷遗留评估报告

> **状态：待 neon 人工评估（占位）。** 课程要求：系统测试遗留缺陷清单、影响评估、修复计划；并据此判定「无致命/严重缺陷遗留」「一般缺陷 ≤3 个且有明确修复计划」。

## 当前遗留（取自 GitHub Issues，须人工复核）

| Issue | 级别 | 标题 | 影响 | 修复计划 |
|---|---|---|---|---|
| #222 | 严重 | tabnet 权重绑定 CUDA，CPU 加载失败 | 25 模型中 2 个不可预测 | 待人工评估 |
| #217 | 严重 | 语义表 / e2e 文本表未放约定路径 | 干净检出下 semantic/fused/e2e 降级 | 待人工评估 |
| #219 | 一般 | 容器内缺 `transformers` | Docker 部署 e2e 降级 | 待人工评估 |
| #220 | 轻微 | 接口文档与实现 6 处偏差 | 契约可读性 | 待人工评估 |

权威动态状态以 GitHub Issues / 飞书缺陷看板为准，逐条明细见 [`../system_test/bug_list.md`](../system_test/bug_list.md)。

## 待人工判断

- 上述两项「严重」级别缺陷是否会阻断验收通过；课程要求致命/严重缺陷必须全部修复并回归验证。
- 遗留项数量、影响范围与修复责任人和时间；结论须写入 [`acceptance_report.md`](acceptance_report.md) 并签字。
- 表中级别为仓库侧记录，**未经人工确认前不得作为验收结论依据**。

## 课程通过标准对照（结论由人工判断，AI 不代判）

| 条件 | 课程要求 | 当前可核验事实 | 判定 |
|---|---|---|---|
| 无致命 / 严重缺陷遗留 | 全部修复并回归验证通过 | #222、#217 两项「严重」仍为待修复 / 待处理，无回归记录 | **不满足** |
| 一般缺陷遗留 ≤3 | 且有明确修复计划与影响评估 | #219 一项；修复计划与影响评估均为「待人工评估」 | 待人工判定 |
| 影响评估与修复计划 | 每条列明责任人、时间与影响范围 | 表中 4 条均未填 | 未闭合 |
| 验收结论 | 「验收通过」或「验收不通过」 | [`acceptance_report.md`](acceptance_report.md) 仍为占位 | 待人工判定 |

按课程 §5.1，严重缺陷未闭环时不得给出「验收通过」结论；整改要求须写入 [`acceptance_report.md`](acceptance_report.md) 并由 neon 签字。

## 候选遗留项（有证据，待人工定性后决定是否计入）

| # | 观察 | 证据 |
|---|---|---|
| C-01 | 10 并发 × 10 请求时 `POST /api/predict` p95 = 694.0ms，超 500ms 判据（错误率 0%） | [`../system_test/performance/README.md`](../system_test/performance/README.md) §2.1 |
| C-02 | `sync/status.started_at` 无 `Z`，与规格 UTC + `Z` 不符（D-06，已并入 #220） | [`../integration_test/report.md`](../integration_test/report.md) §6 |
| C-03 | 模型缺失时规格要求 `50000`，实现收敛为 `40001` | `backend/scripts/evidence/2026-11-12-security.md` §规格偏差 |
| C-05 | `openspec/specs/` 五个能力目录无 `spec.md` | [`../integration_test/endpoint_inventory.md`](../integration_test/endpoint_inventory.md) §3.1 |

详见 [`../system_test/bug_list.md`](../system_test/bug_list.md) §3；这些项目前**不计入缺陷数**，是否升级为缺陷、级别与修复计划均须人工确认。

## 闭环要求

- 每条遗留缺陷须有：状态、影响评估、修复责任人、计划时间、回归验证证据、关闭记录。
- 动态状态以 GitHub Issues / 飞书缺陷看板为唯一真源；本文件只登记交付时的快照，须注明采集日期与被测 SHA。
- 修复后重新执行 [`../system_test/bug_list.md`](../system_test/bug_list.md) 对应回归用例，并把结果写入验收报告。
