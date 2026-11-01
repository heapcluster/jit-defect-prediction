# predict

单条提交现算预测接口（模块 `predict.py`）。

## 处理功能
- **方法 / 路径**：`POST /api/predict`
- **用途**：对单条提交**现算特征并预测**（不依赖预存 prediction），用于新到提交的即时补算。
- **调用约定**：现算要扫全历史，属**后台任务级耗时**，前端 MUST NOT 把它当同步请求等待。
- **权限**：沿用后端统一鉴权。
- **请求体**：`commit_hash`（必填）+ `model_name`（可选）。仓库固定取服务端配置的源仓库，**不接受 `repo_name`，也不接受 diff 文本**（非法请求体返回 `40001`）。

## 传输模型
### 请求（body）
| 字段 | 必填 | 含义 |
|---|---|---|
| `commit_hash` | 是 | 目标提交（需能在源仓库中检出） |
| `model_name` | 否 | 指定模型；省略时取全站冠军模型 |

### 响应（200 OK）
| 字段 | 含义 |
|---|---|
| `commit_hash` / `model_name` | 提交标识与实际使用的模型 |
| `risk_score` | 风险概率 `[0,1]` |
| `predicted_at` | 本次现算时间 |
| `features{ns..sexp}` | 现算的 14 维特征 |
| `explanation[]` | 解释因子（`feature` / `contribution` / `direction` / `label`） |

**没有 `predicted` 二值判定字段**（实测响应只有上面 6 个键）：高/中/低判定由调用方按运行时阈值算（前端 `utils/risk.js`），后端只在 `prs` 一类已下线的能力里才输出过等级。

### 错误响应
| 状态码 | 含义 |
|---|---|
| 400 | 请求体非法 |
| 404 | 提交/模型不存在 |

### 性能口径（实测）
- 单条现算 P50 ≈ **108 秒**：特征抽取每次都要重扫全历史（`data_model/preparation/03_extract_features.py` 的 `extract_single_commit` → `scan_history`），Apache Camel 84,461 提交 / 995,022 行 numstat 的规模下限。
- 批量补算走 `/api/sync` + `/api/sync/stream` 看进度；本接口只承担单条补算与集成测试用例。
- 优化落地前，任何页面与报告都 MUST NOT 把现算写成秒级响应。
