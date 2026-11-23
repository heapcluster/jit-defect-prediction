# 模型预测 API（predict）

一句话：独立加载模型包或已加载模型，对单提交或表格批次输出风险概率、判定标签和版本信息，并交付统一 `predictions.csv`，不在预测服务内生成解释或定位。

实现状态：已实现　期次：一期

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.2、§3.3、§3.4、§3.9；模型管理见 [models.md](models.md)。

## 1. 职责与不负责范围

- 负责模型包校验、特征列宽校验、单条即时预测、文件批量预测、阈值判定、结果幂等和预测文件交付。
- 单条详情可选择沿用库中结果或立即重新计算；批量文件运行不依赖库中已有预测。
- 不负责训练、性能评估、XAI 或行级定位。响应不包含 `explanation`，预测服务禁止调用解释或定位服务；详情页可并行编排 `/api/explain` 与 `/api/localize/run`。
- 不隐式把批量文件结果导入展示表；需要时由调用方另调 storage。

> W8 已移除单条预测的 explanation 和预测内部的 SHAP 调用，详情页经 `/api/explain` 单独读取解释；features/summary 仍为现有详情展示字段。prediction 已落 `model_version / feature_version` 两可空列：单条沿用库中结果时按行内版本与当前模型/特征版本对比返回真实 `stale`，历史 NULL 版本行视为过期，`force_recompute` 重算并刷新版本。批量 run 已交付 §3.4 文件 + summary + manifest，并支持 semantic/fused/e2e 线（见 §3）；模型管理 status/load/unload/reload/default 见 [models.md](models.md)。

## 2. 端点契约

### POST /api/predict

单条 JSON 请求，供提交详情编排：

| 字段 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 40 位 hex，归一化为小写 |
| `model_name` | 否 | 缺省读 `user_config.default_model`；未配置时回退已加载 expert 中 version_key 最大者 |
| `decision_threshold` | 否 | 开区间 (0,1)，缺省读全局配置 |
| `force_recompute` | 否 | 默认 `false`：同模型与特征版本有可用库中结果则沿用；`true` 立即重新计算 |

响应 `data`：

| 字段 | 含义 |
|---|---|
| `commit_hash` / `model_name` | 提交与实际模型 |
| `risk_score` | [0,1] 概率 |
| `predicted_label` | 按本次 decision_threshold 得到的 0/1 |
| `decision_threshold` | 实际判定阈值 |
| `risk_level` | 按 risk_high_threshold / risk_mid_threshold 得到的 high/mid/low |
| `model_version` / `feature_version` | 版本追溯 |
| `predicted_at` | 本次结果时间，UTC `Z` |
| `result_source` | `stored` / `computed`，明确沿用或重算 |
| `stale` | 模型或特征版本变化导致旧结果过期时为 true |

请求禁止多余字段。无 `explanation`、定位、修复建议字段；库中沿用也不得伪装成新计算时间。

### POST /api/predict/run

`multipart/form-data`：`files[]` 接收一个 commits/cleaned 表格，以及可选一个 `model_package.zip`；`config` JSON part。小文件同步，大文件创建 `kind=predict_batch` job。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 已导入输入表的便利选择；与上传表格二选一 |
| `model_name` | 否 | 使用已加载或已登记模型；上传模型包时可省略 |
| `decision_threshold` | 否 | 缺省读 `user_config.decision_threshold` |
| `batch_size` | 否 | 正整数，缺省读 `predict.batch_size` |
| `force_recompute` | 否 | 默认 true（文件运行始终按输入计算）；false 仅对可选库输入允许复用同版本结果 |
| `format` | 否 | `csv` / `xlsx`，默认 `csv` |

模型解析顺序：显式上传模型包 → 显式 model_name → `user_config.default_model` → 已加载 expert 中 version_key 最大者。同步响应 `{job_id,status:"success",outputs[],summary}`；异步 `{job_id,status:"queued"}`。summary 含总数、成功数、失败数、实际模型与阈值；逐行失败不得被写成风险 0。

### GET /api/predict/outputs/{job_id}/{name}

下载 predictions 或 manifest；鉴权与文件名限制同公共契约。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 多余字段、非法阈值、模型/特征不兼容、checksum 失败、输入 schema 非法、空目标、同 kind 冲突 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 提交、模型、可选 dataset、job 或输出不存在 |
| 50000 | 500 | 未预期服务错误；批量运行期失败写脱敏 job 日志 |

## 3. 输入契约

模型包逐字采用 §3.3：

> zip 内含：权重文件（expert/semantic/fused 为 `.pkl`；e2e 为 safetensors 目录）、`feature_order.txt`、`model_meta.json`（model_name/line/algo/version_key/feature_version/trained_at/超参快照/划分/种子）、`checksum.sha256`。predict/explain MUST 校验 checksum 与特征列宽后再加载。

表格采用 §3.1 commits 或 §3.2 cleaned。§3.1 列契约逐字如下：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40 hex) | 是 | 提交标识（小写） |
| repo_name | string | 是 | 来源仓库名 |
| author_name / author_email | string | 是 / 否 | 作者 |
| committed_at | datetime | 是 | 提交时间 UTC |
| message | string | 是 | 提交信息 |
| parent_hash | string(40) | 否 | 父提交 |
| ns…sexp（14 列） | float | 是 | Kamei 14 维 log 变换值（`fix` 为 0/1），列序固定 |
| is_bug_inducing | int 空可 | 否 | SZZ 真标签 1/0/空 |
| labeled_at | datetime | 否 | 打标时间 |
| is_test | int 0/1 | 是 | 时间序划分标记 |
| label_method | string | 否 | szz / szz_lite |

§3.2 为“列同 3.1”，不新增预测输入列。ZIP 还须校验路径穿越、文件数量和解压大小；表格执行大小、扩展名魔数、schema、公式注入校验。任何文件名不得拼接 shell。特征顺序严格按包内 `feature_order.txt`，禁止按字典序猜测。

按模型线的批量输入口径：

- **expert**：一个 §3.1/§3.2 特征表（或 `dataset_id`），取 Kamei 14 维；不接受文本表。
- **semantic / fused**：一个 §3.1/§3.2 特征表提供提交哈希、Kamei 特征与真标签；语义向量按 `commit_hash` 取模型线预计算 embedding（`semantic_embeddings.npz`），缺失时若本机有冻结 CodeBERT 编码器则在线编码，仍不可用该行明确失败（不编造向量）。fused = Kamei 14 ⊕ embedding 768 = 782 维。可选附一个 `commit_hash,text` 文本表为缺预计算的提交提供在线编码文本。
- **e2e**：使用已登记 `codebert_e2e_v1`（本地 safetensors 目录），接收 §3.1/§3.2 特征表（按哈希取预计算/在线构造文本）或 `commit_hash,text` 文本表（直接前向）；**不接受上传 e2e 模型包**（返回 40001）。
- 辅助文本表 schema 固定为 `commit_hash,text`（UTF-8 BOM CSV / 单 sheet XLSX），仅 predict 批量消费，不入展示库；与特征表合计最多两个表格 + 一个模型包。
- CLI `predict run` 与 API 同源：`--model-package` 或 `--model` 二选一，`--input` 特征表、`--text` 文本表按线可选；semantic/fused/e2e 同样按上述口径取向量/文本，缺输入明确报错。

## 4. 输出契约

主文件 `predict_predictions_<job_id>.csv`（或 `.xlsx`），manifest `predict_predictions_<job_id>.manifest.json`。主表逐字采用 §3.4：

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

概率与标签分离，阈值不改变 risk_score；输入真标签原样透传，未打标留空。CSV UTF-8 BOM，XLSX 单 sheet；manifest 严格符合 §3.9，记录模型包 checksum、特征版本、阈值、输入与输出 checksum。

单条端点只返回 JSON 并幂等写 prediction，不额外产生交换文件；批量 run 必须产生上述文件与 manifest。

## 5. 可配置项

- 全局：`default_model`、`decision_threshold`、`risk_high_threshold`、`risk_mid_threshold`。
- 命名空间：`predict.batch_size`、`predict.cache_ttl`、`predict.retry_max`，均落 `user_config` 并重启恢复。
- 单次运行可指定模型包/模型、阈值、批量大小和输出格式；显式阈值进入 manifest，不从模型包猜测。
- `.env` 仅提供出厂默认；模型重载是 models 管理动作，不由预测请求隐式触发。

## 6. 状态持久化

- 批量 run 同步写终态，异步 kind=`predict_batch` 写五态；同 kind 条件更新互斥，重启遗留 running 置 failed，可 retry/cancel。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore），job 登记输出和成功/失败计数。
- 单条预测按 `(commit_hash,model_name)` 幂等更新，记录模型/特征版本；沿用结果返回 stored，重算返回 computed。
- 批量文件产物是否导入 prediction 由 storage 决定，预测计算本身不要求数据库或 explain/localize 可用。

## 7. 验收

fixtures：`tests/fixtures/files/predict/`，可只凭上传表格与模型包运行。

- **正常**：单条 computed/stored 两种路径与批量 CSV/XLSX 均返回正确概率、标签、阈值和版本；§3.4 风险分 5 位小数，manifest checksum 可验。
- **边界**：默认模型未配置、阈值接近 0/1、空真标签、重复提交、部分行失败、缓存过期均不填造 0，不改变概率语义。
- **非法**：多余单条字段、损坏 ZIP、checksum 或特征列宽不符、路径穿越、缺列、公式注入、非法阈值均返回 40001；无解释字段且预测服务无解释/定位调用。
- 同提交同模型写库幂等；大文件 job 重启置 failed；CLI/API 同 fixture 输出一致。

## 8. 边界

predict 与 train 通过 §3.3、与 clean 通过 §3.1/§3.2、与 evaluate/explain/localize 通过 §3.4 文件兼容。`dataset_id` 只便利选择输入；explain/localize 消费预测产物，反向调用禁止。
