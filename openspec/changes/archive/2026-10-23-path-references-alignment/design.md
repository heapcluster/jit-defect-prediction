# Design — path-references-alignment

## 决策一：archive 不改，只改活跃 specs 与进行中 change

archive/ 下 4 个已归档 change 的 tasks / specs / proposal 共 40+ 处旧路径引用**保持原样**。
理由：archive 是历史快照，记录的是「该 change 当时的真实路径与交付状态」；答辩与回溯时
它的价值恰在于如实反映历史。改写它等于篡改留痕，比保留旧引用危害更大。活跃规格
（`openspec/specs/`）是当前契约，必须与代码一致——所以只改活跃的。

## 决策二：只换路径，不换语义

每个 MODIFIED delta 只替换路径片段；Requirement 的判定条件、阈值、交付边界逐字保留。
验证方式：`git diff` 中每个 spec 的变更行必须只含路径字符串差异。

## 路径对照表（本 change 的唯一事实来源）

| 旧路径 | 新路径 | 归属 |
|---|---|---|
| `data_model/01_extract_commits.py` … `05_split_dataset.py` | `data_model/preparation/0X_*.py` | 共享数据流水线 |
| `data_model/reports/{commit_extract,szz_labeling,feature,dataset,split}_*stats.md`、`labeling_review_sample.md` | `data_model/preparation/reports/` | 01–05 统计 |
| `data_model/06_train_model.py` | `python -m pipelines.expert.train` | expert 线 |
| `data_model/07_predict_all.py` | `python -m pipelines.expert.predict` | expert 线 |
| `data_model/08_model_matrix.py` | `python -m pipelines.expert.matrix` | expert 线 |
| `data_model/09_calibration_threshold.py` | `python -m pipelines.expert.calibrate` | expert 线 |
| `data_model/16_statistical_test.py` | `python -m pipelines.expert.significance` | expert 线 |
| `data_model/reports/{model_metrics,model_matrix,prediction_stats,calibration_threshold,statistical_test}*.md` | `data_model/pipelines/expert/reports/` | expert 线证据 |
| `data_model/models/feature_order.txt` | `data_model/pipelines/expert/models/feature_order.txt` | 交付清单 |
