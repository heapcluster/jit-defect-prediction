# test-detail

**一句话**：测试集评估的明细接口——返回检验集逐条明细（commit 信息 + 14 维特征 + 真标签 + 选中模型分），只读已存预测。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「测试集评估」页板块一「测试集信息 + 预测结果」 | 切换线 → 模型后浏览明细表 |

## 处理功能
- **方法 / 路径**：`GET /api/test-detail`（**待实现**）
- **权限**：沿用后端统一鉴权。
- **数据范围**：仅 `commit_feature.is_test = 1` 的检验集提交。
- **关联数据**：`commit` / `commit_feature`（含 `is_bug_inducing` 真标签）/ `prediction` / `model`（`line` 分组）。

## 参数
| 参数 | 必填 | 含义 |
|---|---|---|
| `model_name` | 是 | 如 `lr_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| `page` / `size` | 否 | 分页，默认 `page=1` |
| `sort` / `order` | 否 | 排序字段与方向（如 `risk_score` / `desc`） |
| `q` | 否 | 关键字（commit_hash / author_name / message） |
| `is_bug_inducing` | 否 | 按 szz 真标签筛选（0/1） |

## 响应 `data`
| 字段 | 含义 |
|---|---|
| `total` / `page` / `size` | 分页信息 |
| `items[]` | 明细数组 |
| `items[].commit_hash` / `author_name` / `committed_at` / `message` | 提交信息 |
| `items[].features{ns..sexp}` | Kamei 14 维；**仅 `line=expert` 的模型返回**，semantic / fused / e2e 不返回特征列。**注意是 log 变换后的值（可负），不是原始行数**——见 `database/commit_feature.md` |
| `items[].is_bug_inducing` | 真标签（szz，来自 `commit_feature`） |
| `items[].risk_score` | 选中模型概率 `[0,1]` |

**判定口径**：接口只回 `risk_score`，**不返回 `predicted` 布尔判定**——高/中/低由调用方按 `.env` 写死阈值算（与 `POST /api/predict` 同口径）。

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 缺少 `model_name` 或参数非法 |
| 40100 | 401 | 缺 / 错 token |
| 40400 | 404 | `model_name` 不存在 |

## 口径
- **模型标识统一用 `model_name`**：请求/响应都用 `model_name`，库表 `prediction.model_name` 外键同名，无中间转换。
- 本接口**只读不计算**：只查 `prediction` 已有行，不触发特征抽取或推理。
- 某提交在测试集内但选中模型没有预测行 → `risk_score` 为 `null`，前端标「未预测」，与「预测为 0」区分。
- 特征列只在 expert 线展示（那 14 维是 expert 的模型输入，其余线展示会误导）。
- 缺口表达：页顶「测试集 N / 已预测 M / 缺 K」，缺口走 `/api/sync` 补齐。
