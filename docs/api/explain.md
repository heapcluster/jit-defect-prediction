# 预测结果解释 API（explain）

一句话：对单个提交或一批提交给出特征贡献（SHAP / LIME），交付解释表、对比、摘要与贡献图；不做预测、不训练、不定位。

实现状态：已实现　期次：一期

特征 schema 见 collected_commits 列契约、clean_dataset 列契约；解释文件见 explanations 列契约；功能点职责见 [`../function_point/explain.md`](../function_point/explain.md)。

## 1. 职责与不负责范围

- 负责技术目录与兼容性、单条解释、批量解释、贡献排序与图。
- 负责读取已存特征/预测，或在请求中携带特征表与模型文件。
- 不训练模型、不重算预测风险、不生成修复建议或定位。

## 2. 端点契约

### GET /api/explain/techniques

| 参数 | 必填 | 契约 |
|---|---|---|
| `line` | 否 | `expert` / `semantic`，其他 40001 |
| `model_name` | 否 | 用于过滤兼容性 |

响应：

```json
{
  "techniques": [{"key": "shap", "name": "...", "description": "...", "params_schema": [{"name": "background_size", "type": "int", "default": 32, "min": 1, "max": 128}]}],
  "compatibility": [{"family": "tree", "technique": "shap", "supported": true, "reason_code": null}],
  "default_technique": "shap",
  "compare_enabled": true
}
```

技术仅 `shap`、`lime`；family ∈ `tree|linear|tabular|text`。

### POST /api/explain

JSON body（`extra="forbid"`，strict）：

| 字段 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 40 位十六进制 |
| `model_name` | 是 | 显式指定 |
| `technique` | 否 | `shap` / `lime`，缺省取配置 `default_xai` |
| `params` | 否 | 技术参数对象 |

响应 `data`：

```text
commit_hash, technique, items[{feature, raw_value, contribution, direction(increase|decrease|neutral), rank, output_space, label}],
reason_code, message, base_value, output_space, model_name, model_version, feature_version
```

特征或已存预测缺失返回 40400；多技术比较关闭时指定多技术返回 40001。

### POST /api/explain/run

`multipart/form-data`：

| part | 必填 | 契约 |
|---|---|---|
| `config` | 是 | `model_name, dataset_id, techniques, params, top_n, cache_ttl, format, commit_hashes` |
| `files[]` | 否 | ≤6 个，合计 ≤64MiB；必须恰有 1 个特征表，≤1 个模型文件（`.pkl` 或 `.zip`），≤1 个 predictions 核对表 |

响应：同步（≤20 行）返回 `{job_id,status,outputs,summary,error_log}`；异步返回 `{job_id,status}`。

`summary`：`input_rows, success_count, techniques[], reason_counts{}, cache_hits`。

### GET /api/explain/outputs/{job_id}/{name}

产物：

```text
explain_explanations_<job_id>.csv / .xlsx
explain_summary_<job_id>.json
explain_comparison_<job_id>.json
explain_contributions_<job_id>.png
<stem>.manifest.json
```

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 参数/技术/维度非法、模型未加载、多技术比较关闭、上传文件数或结构不符 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 特征/预测/模型/输出批次不存在 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 单条解释：会话内已存特征 + 预测；缺一即 40400。
- 批量解释：特征表列须符合 collected_commits 列契约/clean_dataset 列契约；模型文件可为训练产物 `.pkl` + 侧车 meta，或外部交付 ZIP（含 `model_meta.json`、`feature_order.txt`、`checksum.sha256`）。
- 特征维度必须与模型线一致（14 / 768）。

## 4. 输出契约

- `items` 按 `rank` 升序，`contribution` 与 `direction` 描述该特征对当前预测的影响方向与强度。
- 输出空间由技术决定（`probability` / `log_odds` 等），不混用。
- 批量产物只含成功行，失败原因写入 `reason_counts`；不写回预测表。

## 5. 可配置项

`default_xai`、`explain_top_n`、`compare_enabled`、`cache_ttl` 来自配置中心；技术与参数由请求指定。

## 6. 状态持久化

- 批量任务 `kind=explain`，同步阈值 20 行，`job.total = 行数`。
- 输入快照落 `temp/explain_inputs/<hash>/request.json`；解释结果可缓存，缓存键含模型与特征版本。
- 单条解释不建 job、不写产物文件。

## 7. 验收

- shap / lime 在兼容 family 上可用，不兼容返回明确 reason_code。
- 单条与批量同技术结果一致（缓存命中不改变数值）。
- 贡献排序与方向稳定，top_n 截断符合契约。
- 特征/预测缺失、维度不符、非法技术被拒绝。

## 8. 边界

解释是对既有预测的事后归因，不改变预测标签与阈值判定；解释结果不参与评估指标，也不作为定位的输入前置。



