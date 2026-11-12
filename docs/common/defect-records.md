# 缺陷记录入口

当前缺陷状态以 GitHub Issues 或飞书缺陷看板为准。本页只记录入口，不复制动态状态。提交测试报告时，每条失败至少给出 Issue/飞书条目链接、复现步骤、预期与实际结果、严重度、责任人和关联 PR。旧 `docs/repo/defect-records.md` 已删除，不能把历史行号当成当前缺陷状态。

## 已登记缺陷（GitHub Issues）

> 状态列只写「登记时状态」，以 Issue 页面为准；修复后回到 Issue 复测并关闭。

| Issue | 标题 | 严重度 | 关联提交 / change | 来源 | 状态 |
|---|---|---|---|---|---|
| [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217) | semantic/fused 在线预测默认路径失效：`SEMANTIC_EMBEDDINGS` 指向不存在的 npz | P0 | `afdee84`（PR #216） | PR #216 审阅 | 待修复 |
| [#218](https://github.com/heapcluster/jit-defect-prediction/issues/218) | e2e 在线推理缺 `commit_text.csv` 且无生成脚本，恒返回 40001 | P0 | `afdee84`（PR #216） | PR #216 审阅 | 待修复 |
| [#219](https://github.com/heapcluster/jit-defect-prediction/issues/219) | 详情接口新增 `model_name` 未同步契约文档，Dockerfile 缺 `transformers` | P1 | `afdee84`（PR #216） | PR #216 审阅 | 待修复 |
| [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220) | 接口文档与实现存在 6 处口径偏差（D-01 ~ D-06） | P2 | 现行 11 端点（静态核对） | `endpoint-inventory.md` §3 | 待裁定 |

另有两类**未立 Issue 的规格层缺口**（待团队决定归属）：`openspec/specs/nfr-evidence/spec.md` 要求但仓库不存在的 `backend/scripts/perf_loop.py`、`security_cases.py`；`openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality`、`ui` 五个空能力目录。

## 复测与关闭要求

- 修复 PR 需引用对应 Issue；关闭前在 Issue 内写复测命令与结果（含提交 SHA）。
- 不得把未修复缺陷标为已关闭；不得补造复测记录。
