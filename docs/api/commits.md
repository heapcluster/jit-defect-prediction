# 提交查询 API（commits）

一句话：只读查询已导入的提交、Kamei 特征、SZZ 标签和所选模型预测，为提交详情提供稳定分页数据，不在查询中执行任何业务计算。

展示数据来自 [storage.md](storage.md) 的可选导入；特征与标签语义引用 collected_commits 列契约，预测语义引用 predictions 列契约。

## 1. 职责与不负责范围

- 负责提交列表、详情、模型/数据集/时间/关键字筛选、稳定排序和可选特征返回。
- 不负责特征抽取、预测、解释、定位、修复建议或指标计算；详情页需要这些能力时分别调用对应端点。
- 不把缺少预测或标签转换成 0，不把数据库是否存在作为其他模块 run 的前置。

## 2. 端点契约

### GET /api/commits

| 参数 | 必填 | 契约 |
|---|---|---|
| `page` / `size` | 否 | 默认 1/20，1≤size≤100 |
| `model_name` | 是 | 必须显式指定；不设默认值或模型回退规则 |
| `dataset_id` | 否 | 仅筛选已导入 dataset_commit 成员 |
| `start_time` / `end_time` | 否 | committed_at 闭区间，纯日期按公共规则展开 |
| `q` | 否 | 最长 64，匹配 hash 前缀、作者、message，LIKE 特殊字符转义 |
| `with_features` | 否 | 0/1，默认 0 |
| `risk_min` / `risk_max` | 否 | [0,1]，且 min≤max |

响应 `data:{total,page,size,items[]}`，按 `risk_score DESC,commit_hash ASC` 稳定排序。items 每项：

| 字段 | 含义 |
|---|---|
| `commit_hash` / `repo_name` / `author_name` / `committed_at` / `message` | 提交元信息 |
| `model_name` / `risk_score` / `predicted_label` / `predicted_at` | 已导入预测；列表只含该模型有预测行的提交 |
| `features` | with_features=1 时返回 `commit_feature` 表的 Kamei 14 维 log 值（`ns,nd,nf,entropy,la,ld,lt,fix,ndev,age,nuc,exp,rexp,sexp`，fix 除外不变换） |
| `is_bug_inducing` / `labeled_at` / `label_method` | SZZ 标签，未打标为 null；不返回 `is_test` |

### GET /api/commits/{commit_hash}

路径 hash 归一小写；可选 `model_name`、`dataset_id`。响应 `data` 含提交元信息、`commit_feature` 特征与 collected_commits 列契约 标签，以及 `prediction` 对象：

`{model_name,risk_score,predicted_label,decision_threshold,model_version,feature_version,predicted_at,stale}`。

无该模型预测时 prediction=null 并 HTTP 200；提交或特征完全不存在才返回 40400。响应不含 explanation、localization 或 fix_references，详情编排分别请求 `/api/explain` 与 `/api/localize/run`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 分页、时间、风险范围、hash、with_features 或未知参数非法；含 `is_test` |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 详情提交不存在，或显式模型/数据集不存在 |
| 50000 | 500 | 未预期读取错误，不回显 SQL |

## 3. 输入契约

无文件输入。查询仅接受上述参数，未知参数返回 40001。`dataset_id` 只是展示筛选；`model_name` 必须显式给出，没有默认值或回退规则。

特征 JSON 的语义见 `database/commit_feature.md`：Kamei 14 维固定列序，值为 log 变换结果（fix 为 0/1）；`is_bug_inducing` 为 1/0/null，NULL 不得当负样本。预测 JSON 对应 predictions 列契约 的模型、概率、标签、阈值与版本字段，不重算风险。

## 4. 输出契约

仅输出 JSON，不生成 CSV/XLSX、图、报告或 manifest，不创建输出目录。需要 commits/predictions 文件时使用 [datasets.md](datasets.md) 导出；需要新计算时使用相应 run 端点。

列表只包含已有所选模型预测的成员，因此缺预测表现为不出现；详情允许 prediction=null。同分排序固定，空标签保持 null，时间统一 UTC ISO 8601 `Z`。

## 5. 可配置项

- default_dataset、risk_high_threshold、risk_mid_threshold 和 page_prefs 来自配置中心；模型每次显式选择。
- 请求可覆盖模型、数据集、时间、关键字、特征开关、风险区间和分页；`is_test` 不是有效参数，传入返回 40001；展示阈值不改变库中 risk_score。
- `.env` 仅提供出厂默认；查询不接收清洗步骤、训练超参或解释参数。

## 6. 状态持久化

- 只读 commit、commit_feature、prediction、dataset_commit，不写业务行、不创建 job、不写输出文件。
- storage 导入完成后新数据可见，服务重启不改变查询结果；预测版本变化只通过已导入元数据反映 stale。
- 查询缓存若存在必须按数据版本和当前显式选择的模型失效，缓存不是权威来源。

## 7. 验收

fixtures：`tests/fixtures/files/commits/`，由 collected_commits 列契约/predictions 列契约 正常、边界、非法样例导入构造，另用非法样例验证导入拒绝后的空态。

- **正常**：模型/数据集/时间/q/风险筛选与分页正确，with_features 返回 14 维，详情版本字段完整，同分跨页不重不漏。
- **边界**：无预测详情 prediction=null、空标签 null、空数据集、风险范围端点、未显式选择模型时的空态均符合契约；不回退到默认模型。
- **非法**：分页越界、非法 hash/时间/风险范围/未知参数返回 40001；不存在详情返回 40400；任何查询均不触发生产计算。
- 详情解释由独立端点获取，commits 响应无解释/定位字段；storage 未导入时本接口为空不影响 run 独立验收。

## 8. 边界

commits 是展示读模型，不是模块间数据通道。它消费的是数据库表，而业务模块之间只依约定文件的 schema 兼容；数据库为空不阻止任何上传文件运行，dataset_id 也不构成上游服务前置。


