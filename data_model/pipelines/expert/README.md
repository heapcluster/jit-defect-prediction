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
python -m pipelines.expert.train                    # 训练口径 8 个模型（[models] 仍只列 lr/rf/xgb）
python -m pipelines.expert.train --delivery-models lr,rf,xgb   # 显式指定交付清单
python -m pipelines.expert.train --no-export        # 只出指标，不覆盖 .pkl
python -m pipelines.expert.train --from-saved --models lr,rf,xgb   # 不训练：用已有 pkl 复算指标 + 重写报告 + 出图
python -m pipelines.expert.matrix                   # 覆盖矩阵（原 08）
python -m pipelines.expert.predict                  # 全量推理（原 07）
python -m pipelines.expert.calibrate                # 校准与阈值（原 09）
python -m pipelines.expert.significance             # 显著性检验（原 16）
python -m pipelines.verify_all_weights --check      # 权重交付校验：md5 + 类路径 + 特征宽度
```

## 产物

| 路径 | 内容 | 入库 |
|---|---|---|
| `models/*_v1.pkl` | 模型权重（joblib；数量以训练口径 `config.DEFAULT_MODELS` 为准，当前 8 个） | 否（`*.pkl` 全局忽略） |
| `models/feature_order.txt` | 交付清单（契约二第三节的副本）：`[models]` 交付集 3 个、`[evaluated]` 评估集 5 个 | 是 |
| `models/manifest.txt` | 8 个权重的 md5 / 类路径 / 特征宽度清单（`verify_all_weights --write-manifest` 生成） | 是 |
| `reports/model_metrics.md` | 两类指标 + SHAP 实测 | 是 |
| `reports/figs/*.png` | ROC / effort 曲线 / 柱状图 | 是 |

## 权重投放与联调自检（MVP：只交付 expert 线）

`.pkl` 按约定**不入库**，干净 clone 的 `models/` 里只有 `feature_order.txt`。联调/演示前按下面四步把权重摆到后端能读到的位置：

1. **取权重**：由模型线把 `models/` 打包分发（本机已有 8 个，`et_v1.pkl` 546MB、`rf_v1.pkl` 279MB，走网盘/拷贝，不进 git）。**当前有效包是 `data/expert_models_20261024.zip`**（8 个 pkl + `feature_order.txt` + `manifest.txt`）；`expert_models_20261021.zip` 已作废但保留作分叉证据 —— 包内 `tabnet_v1.pkl` 是 `__main__` 导出，加载必失败。
2. **指位置**：在 `backend/.env` 设 `MODEL_DIR=<解压后的目录>`；不设则默认指向本包 `models/`（`backend/app/config.py` 的默认值）。
3. **自检清单内 3/3 可加载** —— 在线模型集的唯一来源是 `feature_order.txt` 的 **`[models]` 段**（已合并的 #96 定义），当前声明 `lr_v1` / `rf_v1` / `xgb_v1`：

   ```bash
   cd backend && python -c "from app import model_registry; model_registry.load_models(); print(sorted(model_registry._REGISTRY))"
   # 期望：['lr_v1', 'rf_v1', 'xgb_v1']   ← 即 [models] 段声明的三个
   ```

   两条容易踩的坑：

   - **`sys.path` 不用手工插** —— #99 已让 `load_models()` 自动把 `<repo>/data_model` 的绝对路径插入 `sys.path`（幂等、不接受请求参数或 `MODEL_DIR` 传入）。命令里漏了 `sys.path.insert` 也不会失败。
   - **另外 5 个权重不会出现在列表里** —— `lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1` 登记在 `[evaluated]` 段（本 PR 引入），只进评估不进交付，按冻结规格 `openspec/specs/model-coverage` R6「新增模型 MUST NOT 进入后端加载清单」不参与在线加载。它们加载不上**不算**联调缺陷，不要拿 8 个来验收这一条。

4. **灌预测结果**：`data/prediction_result.csv`（83,943 行，`xgb_v1`，`feature_version=v1`）随包分发，后端用 `python -m app.ingest predictions <该文件>` 灌入 `prediction` 表。

已知待办（不在本包改）：

- 后端 `sys.path` 那半个问题已由 **#99** 修掉（自动插入 `<repo>/data_model`）。`tabnet_v1` 的类路径问题**已核到根因并修掉（2026-10-24）**：工作目录那份内层是 `pipelines.expert.model.TabNetWithEarlyStop`（可加载，md5 `201a002b78c61a9589bec9b14496533c`），出问题的是 **10/21 打包时用的另一版导出**（`__main__.TabNetWithEarlyStop`，300,421 B）。交付包已重打为 `20261024` 版并复核包内 md5 与磁盘逐字节一致，旧包留档。教训是权重以 **md5** 对齐而非文件名对齐 —— `models/*.pkl` 不入库，同名不同版是真事。
- **交付范围已裁定（2026-10-24）**：在线交付 **3 个**（`lr/rf/xgb`，即 `[models]` 段），8 个权重是「**评估可用**」而非「在线可切换」—— 依据 `docs/backend/acceptance.md` §三端联调第 3 条 + `specs/model-coverage` R6 + 契约三。要扩清单须另立「模型切换」change 并升版契约三与 `docs/backend/api-spec.md`；扩清单的代价是后端引入 torch/pytorch_tabnet、`mlp_deep/tabnet/svm` 无精确 SHAP 解释器（KernelSHAP 会冲击 p95<500ms）。
- 「8 个全部可用」的**可核验**方式（不是靠「本地已验证」）：模型线离线校验脚本（随 **#88** 引入）`cd data_model && python -m pipelines.verify_all_weights --check` —— 逐个回读、记录 md5 / 顶层类 / Pipeline 内层类路径 / 特征宽度，与 `models/manifest.txt` 漂移即退出码 2。它**不进后端运行时、不改加载清单**，故不违反 R6。

## 注意事项

- **不要再跑 lite 就覆盖主图**：`--report .../model_metrics_szz_lite.md` 时图表仍写进同一个
  `reports/figs/`，会把 8 模型主图盖成 3 模型 lite 图；补 lite 报告请加 `--no-charts`。
- **不要在包内重切分**：任何「随机切一下看看」的想法都会让四线对比失效。
- **特征口径改不得**：`config.FEATURE_FIELDS` 是契约副本，契约升版必须同步改这里。
- **SHAP 是实测耗时**，连跑两次会变；核对可复现时只比指标表。
- **交付模型仍是 `lr/rf/xgb`**（`feature_order.txt` 的 `[models]` 段），扩展模型只进评估。
- **权重以 md5 对齐，不以文件名对齐**：`models/*.pkl` 不入库、只靠打包含转发，同名不同版是真事
  （2026-10-24 两份 `tabnet_v1.pkl` 分叉在类路径：`pipelines.expert.model` vs `__main__`）。
  收包先跑 `python -m pipelines.verify_all_weights --check`，清单不一致就是另一版导出。
- **`tabnet` 必须模块化训练后再存盘**：以 `python -m pipelines.expert.train` 运行，类路径才是
  `pipelines.expert.model.TabNetWithEarlyStop`；直接 `python 06_train_model.py` 会落成
  `__main__.*`，`sys.path` 再对也加载不了。`--check` 会当场报出来。
- 训练/检验正样本比例差（约 25% vs 14%）是时间序切分的固有现象，不是 bug。
