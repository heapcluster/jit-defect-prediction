# 预测结果解释 API（explain）

一句话：独立消费模型包与待解释提交的特征行，按所选 SHAP/LIME 等技术输出统一贡献结构；predictions 文件仅用于可选的版本与范围核对，不支持的组合以明确 reason_code 交付。

实现状态：已实现　期次：一期

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.3、§3.4、§3.7、§3.9；公共口径见 [README.md](README.md)。

## 1. 职责与不负责范围

- 负责解释器注册、模型族与技术适配、单条及文件批量解释、缓存、多技术比较和统一文件交付。
- 一期至少支持 SHAP 与 LIME；支持性由算法族与技术矩阵决定，不限定某一模型线。
- 不负责预测打分、重训、指标计算或行级定位；解释不得改变 risk_score 与 predicted_label。
- predict 服务不调用本模块；详情页独立调用 `/api/explain`，重新预测成功后另行刷新解释；解释失败不影响预测展示。
- 页面层作为⑤预测的子页，可从预测结果/提交详情带入 commit/model；接口本身独立，不依赖⑤在线。

W8 实现包括带符号 SHAP、真实 LIME 局部代理、参数注册表、提交/模型/特征/参数/代码 checksum 缓存及独立 CLI。线性 SHAP 输出尺度为 log_odds，树 SHAP 为 tree_raw；LIME 为 local_probability_coefficient，不能把两种技术的数值直接相加或比较绝对大小。未提供真实背景数据时，线性 SHAP 使用零参考，LIME 使用零值和正负单位值合成参考并明确提示，不冒称真实训练分布。

## 2. 端点契约

### GET /api/explain/techniques

查询参数均可选：`line`、`model_name`。响应 `data`：

| 字段 | 含义 |
|---|---|
| `techniques[]` | `{key,name,description,params_schema[]}`，一期含 shap/lime |
| `compatibility[]` | `{family,technique,supported,reason_code}` |
| `default_technique` | `user_config.default_xai` |
| `compare_enabled` | `explain.compare_enabled` 当前值 |

非法 line/model_name 分别返回 40001/40400。

### POST /api/explain

单条同步 JSON，供详情编排；只读已存预测与已加载模型，不调用 predict 服务。

| 字段 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 已存在预测与特征输入的提交 |
| `model_name` | 是 | 必须显式指定已加载模型；不设默认值或回退 |
| `technique` | 否 | 缺省读 default_xai |
| `params` | 否 | 按技术 schema 校验，如采样数、背景集大小、top_n |

响应 `data` 为 `{commit_hash,model_name,technique,model_version,feature_version,items[],reason_code,message}`；items 元素与 §3.7 的特征贡献字段一致。不支持组合必须带 reason_code，不得静默返回空数组。

### POST /api/explain/run

`multipart/form-data`：主输入为含待解释提交特征行的 commits/cleaned 表格与模型；`files[]` 必须含特征表，模型可由上传 `model_package.zip` 或已加载模型提供；已登记但未加载的模型须先在模型管理中显式加载。predictions 表格仅为可选的模型版本与提交范围核对文件，不能作为运行前置；只上传模型包与特征表即可解释。产物选择与伴随 manifest 提交遵循 [公共流程](README.md#产物库选择与上传等价)，配置放 `config` JSON part。不超过 20 条提交同步执行，其他输入创建 `kind=explain` job。合计上传与归一化重试快照均限制 64MiB；输入文件至多 6 个且名称去重。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 已导入输入文件的便利选择；显式上传优先 |
| `model_name` | 否 | 未上传模型包时必须显式指定已加载模型 |
| `techniques[]` | 是 | 非空技术数组；比较时需 `explain.compare_enabled=true` |
| `params` | 否 | `{technique:{param:value}}` |
| `top_n` | 否 | 每行每技术输出的最大特征数，正整数 |
| `cache_ttl` | 否 | 缺省读 `explain.cache_ttl`；0 禁用缓存 |
| `commit_hashes[]` | 否 | 非空去重小写哈希，必须在输入特征表范围内 |
| `format` | 否 | `csv` / `xlsx`，默认 `csv` |

同步响应 `{job_id,status:"success",outputs[],summary}`；异步 `{job_id,status:"queued"}`。summary 含输入样本数、成功解释数、技术列表与 reason_code 计数，不以预测文件存在与否决定输入计数。

### GET /api/explain/outputs/{job_id}/{name}

下载 explanations 或 manifest。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 技术或参数非法、组合不支持、特征/模型/预测不匹配、同 kind 冲突、非法文件名 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 提交、模型、可选 dataset、job 或输出不存在 |
| 50000 | 500 | 未预期服务错误；运行期失败写脱敏 job 日志 |

## 3. 输入契约

可选 predictions 核对文件逐字采用 §3.4；未提供时只依据模型包与特征表中的提交范围执行解释：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40) | 是 | 提交 |
| model_name | string | 是 | 模型 |
| risk_score | float [0,1] | 是 | 概率（5 位小数） |
| predicted_label | int 0/1 | 是 | 按 decision_threshold 的二分类标签 |
| decision_threshold | float | 是 | 本次判定阈值 |
| model_version / feature_version | string | 是 | 版本元信息 |
| predicted_at | datetime | 是 | 预测时间 |
| is_bug_inducing | int 空可 | 否 | 透传真标签（便于 evaluate 单文件输入） |

待解释提交来自 §3.1 `collected_commits` 或 §3.2 `clean_dataset`，两表均为提交元信息 + 标签 + 基础派生列，**不含 Kamei 14 维、语义向量或 `is_test`**。expert 的模型输入特征由训练阶段内部生成并固化进模型包的 `feature_order.txt` / `feature_schema.json`；加载模型包后按包内特征顺序，从绑定仓库的该提交快照现算 14 维（与训练侧同一抽取器），不从上传表格读取特征列。semantic 线按 `commit_hash` 取预计算 `semantic_embeddings.npz`（冻结头 CodeBERT 768 维），缺失且有本地冻结编码器时在线编码，仍不可用返回 40001，不编造向量。要求上传含 14 维 / `is_test` 列的文件属于已废止口径，按未知列拒绝。仅提供可选 predictions 时才按 hash 核对提交范围与模型版本；未提供时以输入表中的提交为解释对象。§3.1 的固定契约为：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40 hex) | 是 | 提交标识（小写） |
| repo_name | string | 是 | 仓库名或数据集名 |
| repo_url | string | 否 | 仓库 URL 或数据集来源 |
| author_name / author_email | string | 否 | 作者 |
| committed_at | datetime | 否 | 提交时间，UTC ISO 8601 |
| message | string | 否 | 提交信息 |
| parent_hash | string(40) | 否 | 父提交 |
| is_bug_inducing | int 空可 | 是 | 缺陷标签 1/0/空；评估场景非空 |
| label_method | string | 否 | `szz_v1` / `szz_lite` / `third_party` |
| label_source | string | 是 | `git_szz` / `public_dataset` |
| labeled_at | datetime | 否 | 打标时间 |
| fix_commit_hash | string(40) | 否 | SZZ 回溯修复提交 |
| source_type | string | 是 | `git_repo` / `public_dataset` |

模型所需仓库来源由 `collect.allow_roots` 白名单内的本地仓库提供；CLI 需显式 `--repo` / `--allow-root`，HTTP 运行由配置中心绑定仓库路径。缺可读仓库或提交不可达时前置拒绝（40001），不猜测特征、不填 0。

模型包逐字采用 §3.3：

> zip 内含：权重文件均为 `.pkl`（`expert`=Kamei 14 维、`semantic`=冻结头 CodeBERT 768 维）、`feature_order.txt`、`feature_schema.json`、`model_meta.json`（model_name/line/algo/feature_set/version_key/feature_version/trained_at/超参快照/划分 mode/种子）、`checksum.sha256`。`fused` / `e2e` 及其 safetensors 产物已取消。predict/explain MUST 校验 checksum 与特征列宽后再加载。

上传执行大小、扩展名魔数、schema、ZIP 路径穿越、checksum 和公式注入校验。模型包与特征表必须兼容；仅在提供 predictions 时额外核对其模型版本、特征版本与提交范围，不一致返回 40001。未提供 predictions 不算缺少输入，不猜测对齐。

## 4. 输出契约

主文件 `explain_explanations_<job_id>.csv`（或 `.xlsx`），manifest `explain_explanations_<job_id>.manifest.json`。§3.7 逐字规定：

> `commit_hash,model_name,technique,feature,raw_value,contribution,direction,rank,label,model_version,feature_version`；不支持组合产 `reason_code` 行（feature 空、contribution 空、reason_code 非空），MUST NOT 静默缺行。

- 多技术结果写入同一长表，以 technique 区分；每提交每技术按 rank 排序，contribution 保留符号，direction 至少区分 increase/decrease。
- 不支持的组合必须保留 reason_code 行，不能以缺少输出代替说明；合法空特征与不支持不得混淆。
- CSV UTF-8 BOM、XLSX 单 sheet，两格式均交付；解释主表采用 §3.7 的 11 列并固定增加 reason_code（成功行为空）。comparison JSON 另带 base_value、output_space、说明、逐提交/技术结果；summary 统计 input_rows、success_count（提交 × 技术）、reason_counts 和 cache_hits。贡献图展示首个成功提交/技术，完整结果见主表与 comparison。
- manifest 严格采用 §3.9，每个基础产物同 stem 一份，CSV/XLSX 共用；记录输入/模型 checksum、技术参数、缓存配置和输出 checksum。
- 单条 POST 只返回 JSON，不产生交换文件；批量 run 必须交付主表与 manifest。

## 5. 可配置项

- 全局 `default_xai`；命名空间 `explain.cache_ttl`、`explain.compare_enabled`。
- 单次运行：技术数组、逐技术参数、top_n、缓存 TTL、输出格式；技术默认值与比较开关重启恢复。
- 缓存键至少包含 commit_hash、模型版本、特征版本、技术和参数摘要；模型或特征变化必须失效。
- `.env` 仅提供出厂默认；技术清单由注册表给出，不在前端写死。

## 6. 状态持久化

- 批量 run 同步写终态，异步 kind=`explain` 写五态；同 kind 条件更新互斥，重启遗留 running 置 failed，可 retry/cancel。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore）；job 登记技术、产物和 reason_code 统计。
- 缓存不是唯一结果存储，最多保留 1024 项进程内成功结果；缓存键含实际特征内容、模型权重 checksum、版本、技术、参数、top_n 和代码摘要。重启只丢缓存，不影响已交付文件。
- 上传模型不放入在线注册表；校验包后在受限工作进程中解释。子进程以 `-I -B` 启动，可信依赖加载完成后、pickle 反序列化之前收紧：macOS 叠加系统 sandbox-exec，所有平台统一启用不可卸载的 Python 审计钩子，白名单外的文件读取/写入、网络、新建进程与动态库加载一律拒绝，写入仅允许本次任务目录；120 秒墙钟/90 秒 CPU（Windows 以墙钟与任务终止等价约束）/32MiB 输出限制，取消终止整个进程组。子进程输出为纯 ASCII JSON 规避 Windows GBK stdout；无系统沙箱的平台不再拒绝文件解释，但绝不退回父进程不受限 pickle。超时、无效输出和不支持组合均交付 reason_code 行。
- 单条解释只读已有输入，可缓存但不修改 prediction；批量文件运行不要求数据库存在。

## 7. 验收

fixtures 为 `backend/tests/test_explain_core.py`、`test_explain_run.py` 内联合成的 AI 生成未审核数据，可脱离 predict/localize 服务运行；不冒称人工验收完成。

- **正常**：只上传模型包与特征文件、不提供 predictions，在 SHAP 与 LIME 下均得到同构解释，排序、方向、原始值与版本完整；多技术长表与 manifest checksum 通过。另验可选 predictions 的版本与范围核对。
- **边界**：top_n 大于特征数、缓存命中/失效、比较开关关闭、部分提交不支持均逐行说明，概率与标签不变。
- **非法**：未知技术、不支持组合、缺特征行、checksum/版本/列宽不符、公式注入均返回 40001 或 §3.7 reason_code 行，绝不静默空数组。
- 默认 XAI 重启恢复；异步 job 重启置 failed；CLI/API 同 fixture 数值与结构一致。

## 8. 边界

explain 通过 §3.3 模型包与 §3.1/§3.2 特征文件独立运行；§3.4 predict 文件仅作可选核对，并向 localization 提供可选 §3.7 文件。依赖是 schema 与版本兼容，不是上游服务、既有预测文件或数据库数据前置；predict 不得反向调用 explain。
