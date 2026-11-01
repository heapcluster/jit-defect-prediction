# commits

**一句话**：提交查询接口——风险列表页和提交详情页的数据来源，**只读不计算**。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「风险列表」页 | 打开页面 / 点查询：按「线 → 模型 + 时间区间 + 风险下限」取提交分页 |
| 前端「提交详情」页 | 点列表某行进入：取单条提交的元信息 + 14 维特征 + 解释因子 + 真标签 + 选中模型分 |

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/commits` | GET | 提交列表：按线 → 模型两级选择 + commit 时间区间筛选，可加风险下限，分页 |
| `/api/commits/{commit_hash}` | GET | 单提交详情 |

- **权限**：沿用后端统一鉴权（`X-API-Key`）。

## 参数（列表）
| 参数 | 必填 | 含义 |
|---|---|---|
| `line` | 否 | **待实现**：线别筛选（`expert` / `semantic` / `fused` / `e2e`），按 `model.line` 过滤 |
| `model_name` | 否 | 选中模型；省略时取默认模型 = 已加载模型中 `version_key` 最大者 |
| `page` / `size` | 否 | 分页，默认 `1` / `20`（`1 <= size <= 100`） |
| `min_risk` | 否 | 风险分下限 `[0,1]`。**字段名是 `min_risk`**，不是 `risk_min` / `risk_max` |
| `start_time` / `end_time` | 否 | commit 时间区间，**两端闭区间**（含首末两天）；`since` / `until` 是同义别名 |
| `q` | 否 | 关键字，最长 64 字符（匹配 hash / 作者 / message） |

**已移除**：`has_label`（原按人工标签过滤，人工标注下线后无意义）、`scope`（测试集明细已由独立端点 `/api/test-detail` 承接）。

## 响应

### 列表响应 `data`
| 字段 | 含义 |
|---|---|
| `total` / `page` / `size` | 分页信息（`total` 是**已预测且命中筛选**的行数） |
| `items[]` | 提交数组 |
| `items[].commit_hash` / `author_name` / `committed_at` / `message` | 提交信息 |
| `items[].model_name` / `risk_score` | 选中模型与该提交的风险分 |

### 详情响应 `data`
| 字段 | 含义 |
|---|---|
| `commit_hash` / `author_name` / `committed_at` / `message` | 提交元信息 |
| `model_name` / `risk_score` | 选中模型的风险分；**只回一个模型** |
| `features{ns..sexp}` | Kamei 14 维（log 变换值，见 `database/commit_feature.md`） |
| `explanation[]` | 解释因子：`feature` + `contribution` + `direction` + `label`（中文名） |
| `is_bug_inducing` | **szz 真标签**（0/1，来自 `commit_feature`）；未打标时为 `null` |

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 参数非法（越界、格式错） |
| 40100 | 401 | 缺 / 错 token |
| 40400 | 404 | 提交或特征不存在 |

## 口径
- **模型标识统一用 `model_name`**：库表 `prediction` 外键即 `model_name`（`model` 表以 `model_name` 为主键），请求参数与响应字段同名同值，无中间转换。
- **详情不返回「各模型分数列表」**：换模型 = 换一次请求参数 `model_name`；横向比对多模型走测试集评估明细（`api/test_detail.md`）。
- 原 `label` 字段（人工标签）已下线，详情改回 `is_bug_inducing` 真标签字段。
- **只读不计算**：任何筛选（含 `q` / `line` / 时间区间）都不得触发特征抽取或预测。
- 列表是 `prediction` 与 `commit` 的内连接，**只有已预测的提交会出现**；「尚未预测」表现为少一行，而不是 `risk_score = null`。详情里 `risk_score` 可为 `null`（该提交没有选中模型的预测行）。遇到未预测的提交，前端走「补齐」入口 → `/api/sync`。
