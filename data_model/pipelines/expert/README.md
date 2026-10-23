# expert 线（Kamei 14 特征 baseline）

> 定位：四条线的**对照基准**。其余三线（semantic / fused / e2e）的指标都和本线比。
> 本包取代原根目录 `06–09_*.py` / `16_statistical_test.py`：训练（06）、覆盖矩阵（08）、
> 全量推理（07）、校准阈值（09）、显著性检验（16）全部收进包内；01–05 数据流水线迁至
> `data_model/preparation/`（四线共享上游）。

## 设计思路

1. **任务目标**：提交级二分类（是否 bug-inducing），表格型 14 维 Kamei 特征、
   训练集约 5.9 万条、正样本约 1/4 —— 树模型与线性模型是主力，经典 ML 6 种 +
   神经网络 2 种覆盖课程「2 类 ≥ 8 种」。
2. **两类指标缺一不可**：Effort-unaware（预测对不对）+ Effort-aware（评审预算下
   能抓多少缺陷）。P_norm 以随机基线为 0、真实密度上界为 1 归一，随机基线本身
   就是面积算法的自我校验。
3. **时间序切分**：切分只属于 `05_split_dataset.py`，本包**不重切** —— 用
   `commit_hash` 对齐 `data/split_szz_{train,test}.csv`，四条线共用同一切分。

## 目录与文件

| 文件 | 内容 |
|---|---|
| `config.py` | 路径、14 项特征列序、种子 42、阈值 0.5、SHAP/基线参数 —— 改口径只改这里 |
| `data.py` | 切分加载 + 列校验 + 工作量表对齐（LOC = la+ld，文件数 = nf，取自 03 原始表） |
| `model.py` | 12 个模型定义（`MODEL_NAMES` / `MODEL_CLASS` 是覆盖名单的唯一来源） |
| `metrics.py` | 两类指标（与 06 同口径：随机基线种子 0 / 200 次抽样） |
| `train.py` | 训练入口：fit → 指标 → SHAP 实测 → 导出 .pkl + feature_order.txt → 报告 + 图表 |
| `predict.py` | 全量推理（原 07）：`prediction_result.csv`（契约一表三）+ 三条断言 |
| `matrix.py` | 覆盖矩阵（原 08）：8 模型 × 2 类达标自证 + 与基线报告逐项比对 |
| `calibrate.py` | 校准与阈值（原 09）：Brier/ECE/MCE + 阈值表 + 配额对照表 |
| `significance.py` | 显著性检验（原 16）：Bootstrap CI + 二项检验 + Wilcoxon 配对 |
| `report.py` | Markdown 报告 + `figs/` 三张图（ROC / effort 曲线 / AUC-F1 柱状） |

## 使用方法

```bash
cd data_model
python -m pipelines.expert.train                    # 全部 12 个模型（[models] 仍只列 lr/rf/xgb）
python -m pipelines.expert.train --delivery-models lr,rf,xgb   # 显式指定交付清单
python -m pipelines.expert.train --no-export        # 只出指标，不覆盖 .pkl
python -m pipelines.expert.train --from-saved --models lr,rf,xgb   # 不训练：用已有 pkl 复算指标 + 重写报告 + 出图
python -m pipelines.expert.matrix                   # 覆盖矩阵（原 08）
python -m pipelines.expert.predict                  # 全量推理（原 07）
python -m pipelines.expert.calibrate                # 校准与阈值（原 09）
python -m pipelines.expert.significance             # 显著性检验（原 16）
```

## 产物

| 路径 | 内容 | 入库 |
|---|---|---|
| `models/*_v1.pkl` | 模型权重（joblib；数量以 `config.DEFAULT_MODELS` 为准，当前 12 个） | 否（`*.pkl` 全局忽略） |
| `models/feature_order.txt` | 交付清单（契约二第三节的副本） | 是 |
| `reports/model_metrics.md` | 两类指标 + SHAP 实测 | 是 |
| `reports/figs/*.png` | ROC / effort 曲线 / 柱状图 | 是 |

## 注意事项

- **不要在包内重切分**：任何「随机切一下看看」的想法都会让四线对比失效。
- **特征口径改不得**：`config.FEATURE_FIELDS` 是契约副本，契约升版必须同步改这里。
- **SHAP 是实测耗时**，连跑两次会变；核对可复现时只比指标表。
- **交付模型仍是 `lr/rf/xgb`**（`feature_order.txt` 的 `[models]` 段），扩展模型只进评估。
- 训练/检验正样本比例差（约 25% vs 14%）是时间序切分的固有现象，不是 bug。
