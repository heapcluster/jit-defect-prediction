# 公开数据来源探测

探测日期：2026-11-22T08:52:45.101007Z。未获取满足 commit/time/label 契约的公开数据集，不做文献性能对照。

| 候选 | 许可 | 本次结果 |
|---|---|---|
| https://zenodo.org/records/3910003 | CC-BY-4.0 | curl 30 秒超时，仅接收 634956 / 1521377 字节；实际表头缺 committed_at，不能用 age 替代提交时间 |
| https://zenodo.org/records/5994499 | Other (Open)，未确认明确许可 | 页面报告包大于 64MiB，本次未下载；不能把许可未确认说成可交付 |

Trac 实际接收到的表头：

```text
commit,lines_of_code_added,lines_of_code_deleted,files_churned,line_of_code_old,modified_subsystems,modified_subdirectories,entropy,experience,rexp,number_of_authors,age,number_unique_changes,purpose,defective
```

降级自验仅读取现有 `data_model/data/commits.csv` 的前 20 条时间序记录，关联 `data_model/data/commit_labels_szz.csv`；它是 Camel 历史文件的本次加载自验，不是公开 benchmark，不是新全量采集、SZZ 或模型性能实测。

本次机器可读证据及原始报告保存在输出批次 `j-3cb520af83a3474e9631f82adfc5dac9`；Camel 加载自验批次为 `j-4afd647fb42c49a3a9aa02c48bae0c4c`。此归档不覆盖已有输出批次，不修改 openspec 或冻结课程证据。
