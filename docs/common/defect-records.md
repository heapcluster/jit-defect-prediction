# 缺陷记录入口

当前缺陷状态以 GitHub Issues 或飞书缺陷看板为准。本页只记录入口，不复制动态状态。提交测试报告时，每条失败至少给出 Issue/飞书条目链接、复现步骤、预期与实际结果、严重度、责任人和关联 PR。旧 `docs/repo/defect-records.md` 已删除，不能把历史行号当成当前缺陷状态。

> **2026-11-12 复核与定性**：最初 4 条里有 2 条定性错误（把「产物未放约定路径」写成「代码默认路径写错」/「无生成脚本」），已在 Issue 内更正；#218 与 #217 同根因，已合并关闭。判断口径：**先区分「代码/权重缺陷」「交付布局缺口」「文档偏差」，只有第一类才打 `bug` 标签**。

## 已登记（GitHub Issues）

| Issue | 类型 | 标题 | 严重度 | 关联 | 状态 |
|---|---|---|---|---|---|
| [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) | **代码/权重缺陷** | `tabnet_semantic_v1` / `tabnet_fused_v1` 权重绑定 CUDA，CPU 机器加载抛 `RuntimeError: Attempting to deserialize object on a CUDA device`；`expert/models/tabnet_v1.pkl` 正常 | P1 | `afdee84`、`backend/scripts/evidence/2026-11-12-online-25.md` | 待修复 |
| [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217) | 交付布局缺口 | 语义表与 e2e 文本表未放到 `pipelines/*/data`（后端默认值与模型线 config 一致，不是路径写错）；补齐后 **23/25** 模型可预测 | P1 | `afdee84`、`evidence/2026-11-12-online-25.md` | 待处理（#218 已合并） |
| [#219](https://github.com/heapcluster/jit-defect-prediction/issues/219) | 部署缺口 | `backend/Dockerfile` 未装 `transformers`，容器内 e2e 必然降级 | P2 | `docker-compose.yml` | 待处理 |
| [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220) | 文档偏差 | 接口文档与实现 6 处偏差（D-02~D-07；D-01 复核不成立已剔除） | P3 | `endpoint-inventory.md` §3 | 待裁定 |

已关闭：[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)（duplicate → #217）。

## 复核后**不成立**、不要重复登记

- **D-01**：文档称「`features` 仅 `with_features=1` 时返回」，代码确实只在 `want_features` 时写入该键（`api/commits.py:106-119`）——文档正确。
- 「后端 `SEMANTIC_EMBEDDINGS` 默认路径写错」：默认值与 `pipelines/semantic/config.py`、`pipelines/fused/config.py` 一致，属产物未按布局生成。
- 「e2e 无生成脚本」：脚本在 `data_model/pipelines/e2e/build_text_dataset.py`。
- 「e2e 模型文件缺失」：`data_model/pipelines/e2e/models/codebert_e2e_v1/model.safetensors`（475MB）在位；把文本表放到约定路径后 e2e 实测出分 `0.44606`。

## 未立 Issue 的观察（非缺陷，暂不建单）

- `GET /api/health` 的 `models_loaded` 是「已懒加载模型数」（实测 8→9），`/api/models` 列 25 个；字段语义靠文档说明即可。
- `nfr-evidence` 规格要求「模型缺失 → 50000」，实现为 40001；已在 `backend/scripts/evidence/2026-11-12-security.md` 记录，待 sober 裁定规格侧。
- 前端单测 5 条 `Failed to resolve directive: loading` 警告，用例仍全过，属测试环境配平问题。
- `backend/.env` 内置 `HTTP_PROXY` 指向失效代理，会让本地 HTTP 客户端走代理；测试脚本已 `trust_env=False` 规避，未改 `.env`。

## 复测与关闭要求

- 修复 PR 需引用对应 Issue；关闭前在 Issue 内写复测命令与结果（含提交 SHA）。
- 不得把未修复缺陷标为已关闭；不得补造复测记录。
