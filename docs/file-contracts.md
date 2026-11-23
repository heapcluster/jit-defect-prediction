# 模块间文件契约（交换文件单一权威）

实现状态：部分　期次：一期

W2 已实现通用 CSV/XLSX、ZIP 安全校验及输出登记；W3 已实现 collect 产物、仓库快照、各基础产物同名 manifest 与 checksum 下载；W4 已实现 clean 的 cleaned 双格式、逐步统计、特征统计与分布图及同名 manifest；W5 已实现 train 的逐算法 §3.3 模型包、§3.6 指标长表、比较 JSON、ROC/PR/混淆/柱状图与同名 manifest，指标公式单源落在 `data_model/evaluation/metrics.py`。W6 已实现 predict 的 §3.4 predictions 双格式、summary 与同名 manifest，以及 models 工件校验热加载。W7 已实现 evaluate 的 §3.6 指标长表/混淆双格式、比较 JSON、ROC/PR/校准/两类 effort 图、报告与同名 manifest，指标注册表与 ap 并入 `data_model/evaluation/metrics.py` 单源。W8 已实现 explain 的带符号 SHAP/LIME §3.7 长表（固定增加 reason_code 列）、comparison/summary/贡献图及同名 manifest，predict 不再计算或返回 explanation。业务模块产物继续随对应波次实现。

> **产品主叙事**：八个功能点是八个可独立验收 / 测试 / 运行的工具，不是一条连贯流水线。判据 = 在任一功能点上传它该吃的输入文件，即可拿到它该吐的输出；上下游模块在不在场都无所谓。连贯端到端预测仅为可选演示编排，不是契约主干。
>
> 本文定义模块间交换文件的列 schema、编码、manifest 与命名，是比表契约更前置的单一权威。各功能点 / API / 页面文档的文件输入输出 MUST 引用本文，MUST NOT 各自另定义列名。

## 1 总则

- **文件为主路径**：每个模块的验收与独立运行以「上传输入文件 → 产出输出文件」为准；输入可直接上传，也可从产物库选择上一步已交付文件。产物库选择经鉴权下载文件及其已登记 manifest，再以 `files[]` 提交，流程见 [API 公共契约](api/README.md#产物库选择与上传等价)。`dataset_id` 仅是已导入数据集的额外便利输入，不等同于产物库，也不能成为运行前置。
- **双格式输入**：所有表格类输入同时接受 CSV 与 XLSX（课程功能②点名两者）；解析后归一为同一内部记录结构。
- **输出格式**：表格类输出默认 CSV，`format=xlsx` 可选；机器可读 **JSON manifest 必伴**；图 / 报告 / 工件按各自类型产出。
- **编码**：CSV 为 UTF-8 带 BOM（Excel 中文不乱码）；XLSX 单 sheet 为主表、manifest 不入 sheet；列名 ASCII snake_case；时间 ISO 8601 UTC（`Z`）。
- **空值语义**：未打标 `is_bug_inducing` 为空串（CSV）/ 空单元格（XLSX），MUST NOT 写 0；缺预测行留空，MUST NOT 填 0。
- **安全**：上传校验大小上限 / 扩展名与魔数 / 列 schema；CSV 公式注入防护（以 `= + - @` 开头的单元格转义）；路径限定允许根目录；MUST NOT 把文件名拼进 shell。
- **可复现**：manifest 记录 schema_version、来源模块与 job、配置快照、输入文件 checksum、输出 checksum、代码版本；相同输入 + 相同配置 MUST 产一致输出。
- **fixtures**：每模块独立验收用标准输入文件存 `tests/fixtures/files/<module>/`（后端 `backend/tests/fixtures/files/`、模型线 `data_model/tests/fixtures/files/`），含正常 / 边界 / 非法三类；验收断言输出 schema 与数值，不要求上游先跑或库里有数据。

## 2 命名约定

`<module>_<artifact>_<job_id>.<ext>`，如 `train_model_j-8f21.zip`、`evaluate_metrics_j-91ac.csv`；manifest 同名 `.manifest.json`。下载端点按 job + artifact 名取文件（见各 API 文档）。

## 3 交换文件 schema

### 3.1 commits.csv（collect 输出 / clean 输入 / train 可选输入）

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

W2 的 commits/cleaned 导入不自创特征版本列：读取已验证 companion manifest 的 `config.feature_version`；缺失版本明确拒绝。label_method 不在当前展示表中保存，交换导出留空并标注不可恢复，不伪造历史方法。

### 3.2 cleaned.csv（clean 输出 / train 输入）

列同 3.1；另必伴 `steps_stats.json`（每步 rows_before/after/removed/label_dist/elapsed_ms/excluded_samples）与特征前后分布图 png。处理链配置快照入 manifest。

### 3.3 model_package.zip（train 输出 / predict、explain 输入）

zip 内含：权重文件（expert/semantic/fused 为 `.pkl`；e2e 为 safetensors 目录）、`feature_order.txt`、`model_meta.json`（model_name/line/algo/version_key/feature_version/trained_at/超参快照/划分/种子）、`checksum.sha256`。predict/explain MUST 校验 checksum 与特征列宽后再加载。

### 3.4 predictions.csv（predict 输出 / evaluate、localization 输入）

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

### 3.5 labels.csv（evaluate 可选第二输入）

`commit_hash,is_bug_inducing,labeled_at`；与 predictions 按 hash join；冲突时以 labels 为准并登记冲突数入 manifest。predictions 已含标签列时可省略。

### 3.6 metrics.csv / confusion.csv / report（evaluate 输出）

metrics：`model_name,line,metric,value,threshold,n,pos_rate,dataset_version,model_version,computed_at`（长表，逐模型逐指标一行）；confusion：`model_name,threshold,tp,fp,fn,tn`；report md/html 含指标表 + 混淆 + 图引用 + 不可用原因清单。图 png：roc/pr/confusion/calibration/effort/feat_importance（effort 两类课程硬要求）。

### 3.7 explanations.csv（explain 输出 / localization 可选输入）

`commit_hash,model_name,technique,feature,raw_value,contribution,direction,rank,label,model_version,feature_version`；不支持组合产 `reason_code` 行（feature 空、contribution 空、reason_code 非空），MUST NOT 静默缺行。

### 3.8 localization.csv / suggestions.md / patch_preview.diff（localization 输出）

localization：`commit_hash,file_path,line_number,suspicion,rank,evidence_json,level(line|commit)`；suggestions.md 四段式（问题说明/建议修改/风险提示/参考依据）引用具体文件行；patch_preview.diff 仅预览不应用。

### 3.9 manifest.json（所有输出必伴）

```json
{
  "schema_version": "1.0",
  "module": "train",
  "job_id": "j-8f21",
  "inputs": [{"name": "cleaned.csv", "sha256": "…", "rows": 25183}],
  "config": {"algos": ["rf", "xgb"], "seed": 42, "split_ratio": 0.7},
  "outputs": [{"name": "model_package.zip", "sha256": "…"}],
  "code_version": "3e72854",
  "created_at": "2026-11-21T12:00:00Z"
}
```

## 4 与数据库的关系

- `storage` 提供可选导入：把任一模块输出文件导入 12 表供 Web 展示页（风险列表/趋势/详情）读取；导入幂等按自然键 upsert。
- 配置（`user_config` 全局键 + 模块命名空间键）与任务状态（`job` 六类五态）仍落库，重启恢复（功能①硬要求）；文件化只针对模块间数据 handoff。
- 表契约见 [`database/README.md`](database/README.md)；表是展示与持久化层，不是模块间总线。

## 5 验收总则

- 每模块：fixtures 输入 → CLI 与 API 各跑一次 → 输出文件 schema 逐列断言 + 关键数值断言 + manifest 完整性断言；非法输入（缺列/错类型/公式注入/超大小）返回明确错误码且不产半成品。
- 跨模块一致性：clean(commits.csv) 与 train(cleaned.csv) 等相邻链用同一 fixture 串联跑一次，验证列 schema 兼容（这是兼容性测试，不是独立性前提）。
- 在线演示编排（可选）：Web 一键串跑八模块，产物与独立跑一致；该路径不作为任何模块的验收前提。