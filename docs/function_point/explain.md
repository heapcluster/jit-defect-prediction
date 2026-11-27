# 功能点 7 预测结果解释

一句话：对单个提交或一批提交给出特征贡献排序（SHAP / LIME），交付解释表、对比与贡献图，用于说明模型为什么这样判断。

explanations 列契约；API 见 [`../api/explain.md`](../api/explain.md)；页面见 [`../web_page/predict_detail.md`](../web_page/predict_detail.md)。入口唯一：从预测结果行进入的预测详情页进入，不在预测配置页重复提供按钮。预测详情页在预测详情信息之后提供当前 commit 的“预测结果解释”普通板块，支持选择不同 XAI 技术并展示解释结果；UI 不刻意展示功能编号 ⑦。

## 1 职责

- 提供技术目录与兼容性矩阵（技术 × 模型族）。
- 单条解释与批量解释，输出特征贡献、方向、排序与基准值。
- 支持多技术对比（配置允许时）、结果缓存与贡献图。

## 2 不负责

- 不训练模型、不改预测结果。
- 不生成修复建议、不做可疑行定位。
- 不把不兼容技术包装成可用：不兼容返回明确 `reason_code`。

## 3 输入

| 入口 | 说明 |
|---|---|
| 单条 | `commit_hash` + `model_name` + 可选 `technique`/`params` |
| 批量 | 特征表（collected_commits 列契约/clean_dataset 列契约）+ 可选模型文件（`.pkl` / `.zip`）+ 可选 predictions 核对表 |
| 模型 | 已登记/已加载模型，或上传的模型文件 |

`config`：`model_name`、`dataset_id`、`techniques`、`params`、`top_n`、`cache_ttl`、`format`、`commit_hashes`。

## 4 流程

1. 校验模型与技术，读取兼容性；不安全组合直接拒绝。
2. 读取特征与已有预测；缺一即报错。
3. 计算贡献（shap 需要背景样本；lime 需要采样参数）。
4. 按 `top_n` 截断并排序，生成 CSV/XLSX、摘要、对比与贡献图。
5. 发布产物与 manifest；缓存按模型与特征版本隔离。

## 5 输出

```text
explain_explanations_<job_id>.csv / .xlsx
explain_summary_<job_id>.json
explain_comparison_<job_id>.json
explain_contributions_<job_id>.png
<stem>.manifest.json
```

`summary`：`input_rows, success_count, techniques[], reason_counts{}, cache_hits`。

## 6 约束

- 技术仅 `shap`、`lime`；family ∈ `tree|linear|tabular|text`。
- 参数范围由 schema 约束（如 shap `background_size` 1..128；lime `num_samples` 128..5000）。
- 输出空间必须一致，概率与对数几率不得混用。
- 解释不改变原预测标签。

## 7 验收

- 兼容组合可解释，不兼容组合给出原因码。
- 单条与批量同技术结果一致；缓存命中不改变数值。
- 贡献排序稳定、可复现。
- 缺特征/预测、维度不符、非法技术均被拒绝。

## 8 边界

解释是对既有预测的事后归因，可独立于评估与定位运行；它不产生新的预测，也不参与指标计算。

