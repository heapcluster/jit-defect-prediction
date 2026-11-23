# et_semantic_v1

**极端随机树（Extra Trees） · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=et_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线**精确率最高**（0.4150），但当前在线推理受限（见局限） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 超参 | `n_estimators=300`、`min_samples_leaf=2`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/et_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7564** ｜ AP 0.2863 ｜ F1 0.0726 ｜ P 0.4150 ｜ R 0.0398 ｜ Acc 0.8538

## 局限

- **在线推理当前返回 40001**（`该提交暂无预计算语义向量`）：语义向量产物未按现行 pipelines 布局生成，见 [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)
- 召回仅 0.040，F1 0.073，指标上不适合单独使用

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核

## 训练配置与工件登记（重构契约）

`实现状态：部分` `期次：一期`（现有卡片内容 = 已实现的离线训练与评估；在线工件登记 / 热加载 / 超参数配置化 = 未实现）

> 本节为重构期追加的目标契约，需求输入 `TODO/00`、`TODO/01`、`TODO/04`；代码引用均为仓库根相对路径（已逐一核实）。上文原有指标数字、结论与基线（`afdee84`）引用全部保留，不因本节改写。

- **所属线与算法**：`line=semantic`、`algo=et`，对应 [algorithm 表](../../database/algorithm.md)默认登记清单 semantic 行（enabled=1，768 维输入）；family=`tree`（按该表族词表映射，供解释兼容矩阵复用）。模型名 `et_semantic_v1`，版本键 `v1`。
- **输入与编码器**（现实现核实）：768 维预计算语义向量；冻结编码器 `microsoft/codebert-base`（只前向不训练），`MAX_LEN=512`、mean-pool、`ENCODE_BATCH=32`（`data_model/pipelines/semantic/config.py:13-16`）；编码缓存 `semantic/data/semantic_embeddings.npz`（`semantic/config.py:21`）。在线增量兜底契约见 [database/README.md §5](../../database/README.md)（标记已实现）；卡片「局限」记录的 #217 在线 40001 现象为历史实测，保留不动，是否消除以现场复测为准。
- **训练超参数摘要**（现实现核实）：`ExtraTreesClassifier(n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=seed)`（`data_model/pipelines/semantic/model.py:94-96`）。默认训练口径为 8 分类器（`semantic/config.py:35`）；重构后超参数 schema 登记进 `algorithm` 表（未实现）。
- **随机种子与决策阈值**：`SEED=42`（`data_model/pipelines/semantic/config.py:31`，`--seed` 默认值见 `semantic/train.py:49`）；`DECISION_THRESHOLD=0.5`（`semantic/config.py:32`）。新契约下阈值降级为出厂默认值，唯一权威是 `user_config.decision_threshold`（[database/README.md §6](../../database/README.md)，未实现）。
- **训练/检验划分**：与 expert 共享时间序切分 `data_model/data/split_szz_train.csv` / `split_szz_test.csv`（`semantic/config.py:25-26`），按 `committed_at` 升序前 70% / 后 30%（`data_model/preparation/05_split_dataset.py:39` `DEFAULT_RATIO=0.70`），禁止随机切分；比例为可配置默认参数（database/README.md §4）。
- **数据集版本**：默认 = Apache Camel tag `camel-4.23.0` 快照（`EXPECTED_HEAD` 校验，`data_model/preparation/01_extract_commits.py:41`），登记为 `dataset` 表默认数据集版本（[database/README.md §1](../../database/README.md)）。
- **工件登记目标**（[model_artifact 表](../../database/model_artifact.md)，未实现）：`weight_path=data_model/pipelines/semantic/models/et_semantic_v1.pkl`；`checksum_sha256` / `size_bytes` / `status`（available / load_failed / retired）/ `train_job_id` 由训练服务产出并登记，`model` 表行由登记派生，`model_registry` 只读登记结果并校验文件。现状仍为 manifest 扫描 + DB 双真相源（database/README.md §0）。
- **交付方式**：离线 `joblib.dump` 导出 `.pkl`（`data_model/pipelines/semantic/train.py:127`），在线 `joblib.load`；交付清单随训练写入 `feature_order.txt`（`semantic/train.py:138`），过渡期保留（database/model_artifact.md「过渡期」）。
- **旧表述废止注记**（仅注记，不改上文）：
  - 卡片「注册 = `feature_order.txt` 的 `[models]` 之一，后端启动按清单加载」为旧口径：新契约唯一登记源是 `model_artifact`，清单只是过渡期交付产物。旧表述废止，见 [database/README.md](../../database/README.md)。
  - 卡片「判定 = `risk_score ≥ 0.5` 高风险、`≥ 0.2` 中风险」为旧口径：判定阈值与展示阈值的唯一权威是 `user_config`（[database/user_config.md](../../database/user_config.md)、README §6）。旧表述废止，见 database/README.md；现状实现仍为常量（未实现配置化）。
