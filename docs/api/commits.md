# commits

提交相关查询接口（模块 `commits.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/commits` | GET | 提交列表：按**选中模型 + commit 时间区间**筛选，可加风险下限，分页 |
| `/api/commits/{commit_hash}` | GET | 单提交详情（元信息 + 14 维特征 + 解释因子 + 选中模型风险分 + 真标签） |

- **权限**：沿用后端统一鉴权。

## 关键参数（列表）
| 参数 | 含义 |
|---|---|
| `page` / `size` | 分页，默认 `1` / `20` |
| `model_name` | 选中模型；省略时取运行时默认模型（冠军口径见 `runtime_setting`） |
| `min_risk` | 风险分下限，`[0,1]`。**字段名是 `min_risk`**，不是 `risk_min` / `risk_max` |
| `start_time` / `end_time` | commit 时间区间，**两端闭区间**（含首末两天）；`since` / `until` 是同义别名 |
| `has_label` | 只看已打标签的提交。**现实现按 `label_method=manual` 过滤**（`services/commits.py:66-68`），人工标注下线后须改指 szz 行，否则该筛选恒为空 |
| `scope` | **待实现**。省略 = 全部提交；`scope=test` = **只要测试集**，即 `committed_at >= runtime_setting.test_split_at`。测试集评估页的明细靠它，**不另开端点**。当前代码没有该参数，多余 query 会被静默忽略 → 未实现前前端不得用它当筛选 |
| `q` | 关键字，最长 64 字符（匹配 hash / 作者 / message） |

## 传输模型
### 列表响应 `data`
| 字段 | 含义 |
|---|---|
| `total` / `page` / `size` | 分页信息（`total` 是**已预测且命中筛选**的行数） |
| `test_total` | **仅 `scope=test` 时返回**：测试集提交总数（含未预测）。缺口 = `test_total - total`，前端据此显示「测试集 N / 已预测 M / 缺 K」并引导补齐 |
| `items[]` | 提交数组 |
| `items[].commit_hash` / `author_name` / `committed_at` / `message` | 提交信息 |
| `items[].model_name` / `risk_score` | 选中模型与该提交的风险分 |
| `items[].is_bug_inducing` | szz 真标签（0/1）；**仅 `scope=test` 时返回**，其余请求省略该字段 |

### 详情响应 `data`
| 字段 | 含义 |
|---|---|
| `commit_hash` / `author_name` / `committed_at` / `message` | 提交元信息 |
| `model_name` / `risk_score` | 选中模型的风险分；**只回一个模型** |
| `features{ns..sexp}` | Kamei 14 维 |
| `explanation[]` | 解释因子：`feature` + `contribution` + `direction` + `label`（中文名，见 `app/explain.py`） |
| `label` | 该提交的人工标签字段位。**现实现只读 `label_method=manual` 行**（`services/commits.py:49-62`），库里 manual 行为 0 → 今天恒为 `null`。待改为读 szz 行后，含义才是「真标签（`is_defect` / `labeled_at`）」 |

## 口径说明
- **详情不返回「各模型分数列表」**：换模型 = 换一次请求参数 `model_name`。要横向比对多模型或只看测试集，加 `scope=test`（见 `function_point/test_eval.md`）。
- `label` 字段名沿用不改（改字段名会连累前端），但**数据源必须从 manual 行改指 szz 行**——这是人工标注下线后本接口唯一要动的地方，与 `has_label` 的筛选口径是同一个改动点。
- 本接口**只读不计算**：任何筛选（含 `q` / `has_label` / 时间区间 / `scope`）都不得触发特征抽取或预测。
- 列表是 `prediction` 与 `commit` 的内连接，**只有已预测的提交会出现**；「尚未预测」表现为少一行，而不是 `risk_score = null`。详情里 `risk_score` 可为 `null`（该提交没有选中模型的预测行）。
- 参数校验：`page >= 1`、`1 <= size <= 100`、`0 <= min_risk <= 1`，越界返回 `40001`。
