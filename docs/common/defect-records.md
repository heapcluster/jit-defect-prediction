# 缺陷记录入口

当前缺陷状态以 GitHub Issues 或飞书缺陷看板为准。本页只记录入口，不复制动态状态。提交测试报告时，每条失败至少给出 Issue/飞书条目链接、复现步骤、预期与实际结果、严重度、责任人和关联 PR。旧 `docs/repo/defect-records.md` 已删除，不能把历史行号当成当前缺陷状态。

> **2026-11-12 复核说明**：最初登记的 4 条里有 2 条定性错误（把「产物未按布局生成」写成「代码默认路径写错」/「无生成脚本」），已在 Issue 内更正并在此同步；D-01 复核后不成立已剔除。判断口径：**先确认是代码缺陷还是交付/文档缺口，再决定是否建 Issue**。

## 已登记（GitHub Issues）

| Issue | 类型 | 标题 | 严重度 | 关联 | 状态 |
|---|---|---|---|---|---|
| [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217) | 交付缺口 | semantic/fused 在线所需的 `semantic_embeddings.npz` 未按 pipelines 布局生成，16 模型默认 40001（**非路径写错**：后端默认值与 `pipelines/semantic/config.py` 一致，仓库仅有 `data_model/data/` 旧副本） | P1 | `afdee84`（PR #216） | 待处理 |
| [#218](https://github.com/heapcluster/jit-defect-prediction/issues/218) | 交付缺口 | e2e 在线所需 `commit_text.csv` 未生成到 `pipelines/e2e/data/`（**生成脚本 `build_text_dataset.py` 存在**，仓库仅有 `data_model/data/` 旧副本） | P1 | `afdee84` | 待处理 |
| [#219](https://github.com/heapcluster/jit-defect-prediction/issues/219) | 部署缺口 | `backend/Dockerfile` 未装 `transformers`，容器内 e2e 必然降级 | P2 | `afdee84`、`docker-compose.yml` | 待处理 |
| [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220) | 文档偏差 | 接口文档与实现 6 处偏差（D-02~D-07；D-01 复核不成立已剔除） | P3 | `afdee84`、`endpoint-inventory.md` §3 | 待裁定 |

## 复核后**不成立**、不要重复登记

- **D-01**：文档称「`features` 仅 `with_features=1` 时返回」，代码确实只在 `want_features` 时写入该键（`api/commits.py:106-119`），文档正确——此前判断有误。
- 「后端 `SEMANTIC_EMBEDDINGS` 默认路径写错」：默认值与模型线配置一致，属产物未生成，不是路径 bug。
- 「e2e 无生成脚本」：脚本在 `data_model/pipelines/e2e/build_text_dataset.py`。

## 未立 Issue 的观察（非缺陷，暂不建单）

- `GET /api/health` 的 `models_loaded` 是「已懒加载模型数」（实测 8→9），而 `/api/models` 列 25 个；字段语义靠文档说明即可，不构成缺陷。
- `openspec/specs/nfr-evidence/spec.md` 要求「模型缺失 → 50000」，实现为 40001；属规格与实现口径冲突，已在 `backend/scripts/evidence/2026-11-12-security.md` 记录，待 sober 在规格侧裁定。
- 前端单测 5 条 `Failed to resolve directive: loading` 警告（`RiskList.spec.js`），用例仍全过，属测试环境配平问题。

## 复测与关闭要求

- 修复 PR 需引用对应 Issue；关闭前在 Issue 内写复测命令与结果（含提交 SHA）。
- 不得把未修复缺陷标为已关闭；不得补造复测记录。
