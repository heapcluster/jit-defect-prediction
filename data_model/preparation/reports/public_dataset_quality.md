# 公开数据治理工具的 Camel 文件加载自验

本次未获取合规公开数据集。以下数值仅来自现有 Camel 提交/标签文件的 20 条记录加载，不是公开 benchmark、不是重新全量 SZZ、也不代表训练或预测性能。

来源批次：`j-4afd647fb42c49a3a9aa02c48bae0c4c`。输入选择与来源限制见同目录 public_dataset_probe.md。

标签粒度：二值，无缺陷类型。输入记录未提供语言字段，语种统计为 unknown，不根据仓库名补造 Java 占比。

| 语言 | 提交数 | 占比 |
|---|---:|---:|
| unknown | 20 | 1.000000 |

```json
{
  "rows": 20,
  "label_granularity": "二值，无缺陷类型",
  "defect_types": {},
  "languages": {"unknown": {"count": 20, "ratio": 1.0}},
  "missing_rates": {"commit_hash": 0.0, "committed_at": 0.0, "is_bug_inducing": 0.0, "repo_name": 0.0},
  "duplicate_count": 0,
  "duplicate_rate": 0.0,
  "label_conflicts": [],
  "invalid_time_rows": [],
  "time_order_rows": [],
  "out_of_range_rows": [],
  "invalid_label_rows": []
}
```

治理建议：获取并核验明确来源、许可和提交时间后再处理公开数据；补充可靠语言字段，逐记录处理标签冲突及时间异常，不静默删除或补零。本次不做 DeepJIT/CC2Vec 或 SOTA 指标对照。
