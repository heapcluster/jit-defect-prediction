# tabnet_fused_v1

**TabNet（深度表格） · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=tabnet_fused_v1` 返回指标与图集 |
| 定位 | fused 线**深度表格**选项，AUC 0.8277 居该线第三 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 结构 | `TabNetWithEarlyStop`（基于 `pytorch_tabnet.TabNetClassifier`，带早停，`seed=42`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/tabnet_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | torch 2.14.1、pytorch_tabnet 4.1.0 |

## 性能（测试集 25,183 条）

AUC **0.8277** ｜ AP 0.4292 ｜ F1 0.4120 ｜ P 0.4738 ｜ R 0.3644 ｜ Acc 0.8504

## 局限

- 依赖最重（torch + pytorch_tabnet）
- 与 expert 线 `tabnet_v1`（0.8294）基本持平，融合无明显收益

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核

## 训练配置与工件登记（重构契约）

`实现状态：部分` `期次：一期`（现有卡片内容 = 已实现的离线训练与评估；在线工件登记 / 热加载 / 超参数配置化 = 未实现）

> 本节为重构期追加的目标契约，需求输入 `TODO/00`、`TODO/01`、`TODO/04`；代码引用均为仓库根相对路径（已逐一核实）。上文原有指标数字、结论与基线（`afdee84`）引用全部保留，不因本节改写。

- **所属线与算法**：`line=fused`、`algo=tabnet`，对应 [algorithm 表](../../database/algorithm.md)默认登记清单 fused 行（enabled=1，782 维输入）；family=`tabnet`（按该表族词表映射，供解释兼容矩阵复用）。模型名 `tabnet_fused_v1`，版本键 `v1`。
- **输入口径**（现实现核实）：782 维 = Kamei 14 维 + 768 维语义向量（`data_model/pipelines/fused/config.py:37` `EXPECTED_DIM`）；语义模态依赖 semantic 线编码缓存 `semantic/data/semantic_embeddings.npz`（`fused/config.py:18`，包间唯一数据衔接）。在线增量兜底契约见 [database/README.md §5](../../database/README.md)（标记已实现）。
- **训练超参数摘要**（现实现核实）：`StandardScaler → TabNetWithEarlyStop`（`data_model/pipelines/fused/model.py:134-140`，包装类复用 expert 线实现）。容量超参 `n_d=8, n_a=8, n_steps=3, gamma=1.3`（`data_model/pipelines/expert/model.py:110`）；早停 `max_epochs=100, patience=15, validation_fraction=0.1`（`expert/model.py:84-94`），验证子集从训练集内部分层切出（`expert/model.py:103-105`）。默认训练口径为 8 分类器（`fused/config.py:44`）；重构后超参数 schema 登记进 `algorithm` 表（未实现）。
- **随机种子与决策阈值**：`SEED=42`（`data_model/pipelines/fused/config.py:40`，`--seed` 默认值见 `fused/train.py:38`）；`DECISION_THRESHOLD=0.5`（`fused/config.py:41`）。新契约下阈值降级为出厂默认值，唯一权威是 `user_config.decision_threshold`（[database/README.md §6](../../database/README.md)，未实现）。
- **训练/检验划分**：与 expert 共享时间序切分 `data_model/data/split_szz_train.csv` / `split_szz_test.csv`（`fused/config.py:14-15`），按 `committed_at` 升序前 70% / 后 30%（`data_model/preparation/05_split_dataset.py:39` `DEFAULT_RATIO=0.70`），禁止随机切分；比例为可配置默认参数（database/README.md §4）。
- **数据集版本**：默认 = Apache Camel tag `camel-4.23.0` 快照（`EXPECTED_HEAD` 校验，`data_model/preparation/01_extract_commits.py:41`），登记为 `dataset` 表默认数据集版本（[database/README.md §1](../../database/README.md)）。
- **工件登记目标**（[model_artifact 表](../../database/model_artifact.md)，未实现）：`weight_path=data_model/pipelines/fused/models/tabnet_fused_v1.pkl`；`checksum_sha256` / `size_bytes` / `status`（available / load_failed / retired）/ `train_job_id` 由训练服务产出并登记，`model` 表行由登记派生，`model_registry` 只读登记结果并校验文件。现状仍为 manifest 扫描 + DB 双真相源（database/README.md §0）。GPU 训练、CPU 加载报 CUDA 反序列化错误时运行 `python data_model/pipelines/reexport_tabnet_cpu.py` 重导出（原文件备份 `*.bak-cuda`，database/README.md §4）。
- **交付方式**：离线 `joblib.dump` 导出 `.pkl`（`data_model/pipelines/fused/train.py:83`），在线 `joblib.load`；交付清单随训练写入 `feature_order.txt`（`fused/train.py:96`），过渡期保留（database/model_artifact.md「过渡期」）。
- **旧表述废止注记**（仅注记，不改上文）：
  - 卡片「注册 = `feature_order.txt` 的 `[models]` 之一，后端启动按清单加载」为旧口径：新契约唯一登记源是 `model_artifact`，清单只是过渡期交付产物。旧表述废止，见 [database/README.md](../../database/README.md)。
  - 卡片「判定 = `risk_score ≥ 0.5` 高风险、`≥ 0.2` 中风险」为旧口径：判定阈值与展示阈值的唯一权威是 `user_config`（[database/user_config.md](../../database/user_config.md)、README §6）。旧表述废止，见 database/README.md；现状实现仍为常量（未实现配置化）。
