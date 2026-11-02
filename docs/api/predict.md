# predict

**一句话**：单条提交的**现算**预测接口——对一条提交现场抽 14 维特征 + 打一个模型的分，结果落库并返回。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「提交详情」页「重新预测」 | 选定 `model_name` 后单条现算并落库，刷新详情 |
| 集成测试 | 单条预测用例 |

**批量补算不调用本接口**，统一走 `/api/sync`。

- **方法 / 路径**：`POST /api/predict`
- **权限**：沿用后端统一鉴权。

## 请求体
| 字段 | 必填 | 含义 |
|---|---|---|
| `commit_hash` | 是 | 目标提交（需能在源仓库中检出） |
| `model_name` | 否 | 指定模型；省略时取默认模型 = 已加载模型中 `version_key` 最大者 |

**注意**：仓库固定取服务端配置的源仓库，**不接受 `repo_name`，也不接受 diff 文本**（非法请求体返回 `40001`）。

## 响应 `data`
| 字段 | 含义 |
|---|---|
| `commit_hash` / `model_name` | 提交标识与实际使用的模型 |
| `risk_score` | 风险概率 `[0,1]` |
| `predicted_at` | 本次现算时间 |
| `features{ns..sexp}` | 现算的 14 维特征（log 变换值，见 `database/commit_feature.md`） |
| `explanation[]` | 解释因子（`feature` / `contribution` / `direction` / `label`） |

**没有 `predicted` 二值判定字段**（实测响应只有上面 6 个键）：高/中/低判定由调用方按 `.env` 写死阈值算（前端 `utils/risk.js`）。

**模型标识统一用 `model_name`**：请求/响应都用 `model_name`，库表外键即 `model_name`，无中间转换。

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 请求体非法 / `model_name` 不在已加载清单 |
| 40100 | 401 | 缺 / 错 token |
| 40400 | 404 | 提交或特征不存在 |
| 50000 | 500 | 内部错误 / 模型注册表为空 |

## 性能口径（实测）
- 单条现算 P50 ≈ **108 秒**：特征抽取每次都要重扫全历史（`data_model/preparation/03_extract_features.py` 的 `extract_single_commit` → `scan_history`），Apache Camel 84,461 提交 / 995,022 行 numstat 的规模下限。
- 批量补算走 `/api/sync` + `/api/sync/status` 看进度；本接口只承担单条补算与集成测试用例。
- 优化落地前，任何页面与报告都 MUST NOT 把现算写成秒级响应。
