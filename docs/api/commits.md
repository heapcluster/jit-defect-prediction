# commits

**一句话**：提交查询接口——风险列表、提交详情、模型性能看板的数据来源，**只读不计算**。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「风险列表」页 | 打开页面 / 点查询：按架构 → 模型两级级联 + 独立时间范围取提交分页 |
| 前端「提交详情」页 | 点列表某行进入：取单条提交元信息 + 14 维特征 + 解释因子 + SZZ 真标签 + 选中模型分 |
| 前端「模型性能看板」 | 多维指标表：`with_features=1&is_test=1` 一次取测试集提交 + 14 维 + SZZ + 所选模型概率 |

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/commits` | GET | 提交列表：按模型 + commit 时间区间筛选，分页；可选返回 14 维特征 |
| `/api/commits/{commit_hash}` | GET | 单提交详情 |

- **权限**：沿用后端统一鉴权（`X-API-Key`）。
- **数据来源**：MySQL 的 `commit` / `commit_feature` / `prediction`。测试集由 `data_model/evaluation/out/data_init.sql` 导入；接口不在请求时执行 `data_model` 脚本，也不直接读 `out/`。

## 参数（列表）
| 参数 | 必填 | 含义 |
|---|---|---|
| `page` / `size` | 否 | 分页，默认 `1` / `20`（`1 <= size <= 100`） |
| `model_name` | 否 | 选中模型；省略时取默认模型 = 已加载模型中 `version_key` 最大者 |
| `start_time` / `end_time` | 否 | commit 时间区间，**两端闭区间**（含首末两天）；`since` / `until` 是同义别名 |
| `q` | 否 | 关键字，最长 64 字符（匹配 hash / 作者 / message） |
| `with_features` | 否 | `1` = 返回 `items[].features`；默认 `0`，避免风险列表背 14 列 |
| `is_test` | 否 | `0` / `1`；`1` = 只返回检验集（`commit_feature.is_test = 1`）。模型性能看板固定传 `1`，风险列表不传 |

**已移除**：`min_risk`（页面不再提供最低风险筛选）、`has_label`（原按人工标签过滤，人工标注下线后无意义）、`scope`（测试集筛选改由 `is_test=1` + `with_features=1` 承接）。

## 响应

### 列表响应 `data`
| 字段 | 含义 |
|---|---|
| `total` / `page` / `size` | 分页信息（`total` 是**已预测且命中筛选**的行数） |
| `items[]` | 提交数组，按 `risk_score` 降序、`commit_hash` 升序 |
| `items[].commit_hash` / `author_name` / `committed_at` / `message` | 提交信息 |
| `items[].model_name` / `risk_score` | 选中模型与该提交的风险分 |
| `items[].features{ns..sexp}` | **仅 `with_features=1` 时返回**：Kamei 14 维，log 变换值（可负），见 `database/commit_feature.md` |
| `items[].is_bug_inducing` | SZZ 真标签：`1` = 引入缺陷 / `0` = 非缺陷 / `null` = 未打标 |

### 详情响应 `data`
| 字段 | 含义 |
|---|---|
| `commit_hash` / `author_name` / `committed_at` / `message` | 提交元信息 |
| `model_name` / `risk_score` | 选中模型（默认模型）的风险分；**只回一个模型** |
| `predicted_at` | 该模型对该提交的预测时间；无预测行时为 `null` |
| `features{ns..sexp}` | Kamei 14 维（log 变换值，见 `database/commit_feature.md`） |
| `explanation[]` | 解释因子：`feature` + `contribution` + `direction` + `label`（中文名；与已下线的人工标签 `label` 对象无关） |
| `is_bug_inducing` | SZZ 真标签：`1` / `0` / `null`（未打标） |

**详情不返回 `label` 对象**（人工标签已下线），**也不返回 `pr_submitted_at`**（无 commit→PR 持久数据源，见口径）。

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 参数非法（越界、格式错） |
| 40100 | 401 | 缺 / 错 token |
| 40400 | 404 | 提交或特征不存在 |

## 口径
- **真标签字段名统一 `is_bug_inducing`**（库内外同名，无映射）：`1` = 引入缺陷，`0` = 非缺陷；未打标返回 `null`，**不是 `0`**（不能把「不知道」当负样本）。
- **真标签来源**：SZZ 自动标签（`commit_feature.is_bug_inducing`；原 `commit_label` 已并入）。人工标签与 `label` 对象已下线。
- **`predicted_at`**：来自 `prediction` 表 `(commit_hash, model_name)` 对应行；该提交没有选中模型的预测行时为 `null`。
- **`pr_submitted_at` 本期不提供**：没有 commit→PR 持久关联；PR 能力已在 #195 下线。一个 PR 可包含多个 commit，PR 时间不是提交自身属性，不放进提交详情。
- **模型标识统一用 `model_name`**：请求参数与响应字段同名同值，无中间转换。
- **排序固定**：`risk_score DESC, commit_hash ASC`；同分分页不会重复或漏行。
- **模型名已隐含架构**：`/api/commits` 不接收 `line`；架构只用于 `GET /api/models` 的级联选择。
- **只读不计算**：任何筛选（含 `q` / 时间区间）都不得触发特征抽取或预测。
- **14 维是 log 值**：`with_features=1` 与详情返回的都是对数变换后的值（可负），MUST NOT 当原始行数 / 人数展示。
- **模型性能看板固定 `is_test=1`**：表格只取测试集，与性能图 / 指标同一口径，不混入训练集；风险列表不传该参数。`total` 即测试集内已预测且命中筛选的行数。
- 列表是 `prediction` 与 `commit` 的内连接，**只有已预测的提交会出现**；「尚未预测」表现为少一行，而不是 `risk_score = null`。详情里 `risk_score` / `predicted_at` 可为 `null`（该提交没有选中模型的预测行）。
- 详情不返回「各模型分数列表」：换模型 = 换列表 / 趋势的 `model_name` 参数，或在详情页重新预测；横向比对多模型走模型性能看板。
