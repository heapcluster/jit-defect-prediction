# 仅专家（基线）pipeline 包 · 产出归属

> 负责人：蒋励 ｜ 线名 `expert` ｜ 状态：**✅ 已跑通（Camel 数据待重跑）**
> 方案与口径：`docs/model/pipelines/expert-only.md`（权威，本文不重复其内容）

## 1. 这个包是干什么的

承载**仅专家（基线）**这一条 pipeline 的训练与产出：Kamei 14 专家特征 → 时间序切分 →
8 个分类器 → 两类指标报告 + 模型文件。它是四条 pipeline 中**唯一进入在线交付链**的一条
（交付模型 `lr` / `rf` / `xgb`），也是其余三条线的数据上游。

## 2. 目录结构与产出归属

```
data_model/pipelines/expert/
├── __init__.py     线名与产出路径常量（LINE / DATA_DIR / MODELS_DIR / REPORTS_DIR）
├── train.py        训练入口（驱动 06 / 08，产出全部落到本包）
├── README.md       本文件
├── data/           本线私有中间结果（当前为空，见 §4 约定 2）
├── models/         本线模型文件（*.pkl 不入库；feature_order.txt 入库）
└── reports/        本线报告（可入库当证据）
```

| 产物 | 路径 | 归属 | 入库？ |
|---|---|---|---|
| 8 个模型文件 | `models/{lr,rf,xgb,lgbm,et,svm,mlp_deep,tabnet}_v1.pkl` | **仅本线** | ❌ |
| 交付清单 | `models/feature_order.txt`（`[models]` 段只列 `lr`/`rf`/`xgb`） | **仅本线** | ✅ |
| 训练指标报告 | `reports/model_metrics.md`（⑥，两类指标齐全） | **仅本线** | ✅ |
| 覆盖矩阵 | `reports/model_matrix.md`（⑧，与 `model_metrics.md` 逐项自证差异 0） | **仅本线** | ✅ |
| 切分统计 | `reports/split_stats{tag}.md`（⑤ 如在本包产出） | **仅本线** | ✅ |
| 校准与阈值 | `reports/calibration_threshold.md`（⑨） | **仅本线** | ✅ |
| 全量预测统计 | `reports/prediction_stats.md`（⑦） | **仅本线** | ✅ |
| 仓库副本、提交清单、标签、特征表、切分下标 | `data_model/data/…` | **四线共享** | ❌ |

## 3. 怎么跑

```bash
conda activate jit-defect-prediction
cd data_model
python -m pipelines.expert.train                 # 8 模型 + 指标报告 + 覆盖矩阵
python -m pipelines.expert.train --models lr,rf,xgb   # 只训交付三件套
python -m pipelines.expert.train --skip-matrix   # 跳过 ⑧（省一半训练时间）
```

前置：共享上游产物必须已在 `data_model/data/` 就位（`split_szz_{train,test}.csv`、
`commit_features_raw.csv`），否则入口直接报错退出并提示先跑 ①–⑤。

## 4. 三条约定（改动前先读）

1. **本包产物只归本线**：报告名一律带本线口径（`model_metrics.md` 等归 expert 线），
   其余三条线的报告一律带 `_semantic` / `_fused` / `e2e` 后缀，**四线不得同名**。
2. **共享上游产物不按线分**：样本集与切分下标四线共用且必须同一份，故放
   `data_model/data/`；分到四个包只会得到四份重复数据并破坏 Gate G3（同切分下标）。
3. **训练实现不复制**：`06_train_model.py` / `08_model_matrix.py` 是唯一权威
   （超参、口径、指标定义都在那里），本包只做驱动与产出归属。

## 5. 与其他包的关系

| 包 | 关系 |
|---|---|
| `semantic/` `fused/` `e2e/` | 消费本线的共享上游产物（提交清单、标签、特征表、切分下标）；**不读**本包的 `models/` 与 `reports/` |
| 后端线 | 只收交付三件套的 `.pkl` + `feature_order.txt` + `prediction_result.csv`；按 `--delivery-models` 列出的模型加载 |

## 6. 变更日志

| 日期 | 变更 |
|---|---|
| 2026-10-14 | 建包：把仅专家线的训练与产出从 `data_model/{models,reports}/` 隔离到本包；新增 `train.py` 驱动入口；`06_train_model.py` 增加 `--delivery-models`（训练 8 个而清单只列 3 个交付模型） |
