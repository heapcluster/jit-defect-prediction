# rf_v1

**随机森林 · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=rf_v1` 返回指标与图集 |
| 定位 | expert 线**装袋树基线**，参数按 SHAP 可算性收敛（见 `model.py` 注释） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 超参 | `n_estimators=300`、`min_samples_leaf=100`、`max_depth=15`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/rf_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8169** ｜ AP 0.4274 ｜ F1 0.3659 ｜ P 0.5321 ｜ R 0.2789 ｜ Acc 0.8610

## 局限

- 为压 SHAP 计算量把 `min_samples_leaf` 放大到 100、`max_depth` 限到 15，拟合能力弱于 `xgb_v1`/`lgbm_v1`
- 召回偏低（0.28），固定 0.5 阈值下漏报较多

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核

## 训练配置与工件登记（重构契约）

`实现状态：部分` `期次：一期`（现有卡片内容 = 已实现的离线训练与评估；在线工件登记 / 热加载 / 超参数配置化 = 未实现）

> 本节为重构期追加的目标契约，需求输入 `TODO/00`、`TODO/01`、`TODO/04`；代码引用均为仓库根相对路径（已逐一核实）。上文原有指标数字、结论与基线（`afdee84`）引用全部保留，不因本节改写。

- **所属线与算法**：`line=expert`、`algo=rf`，对应 [algorithm 表](../../database/algorithm.md)默认登记清单 expert 行（enabled=1）；family=`tree`（按该表族词表映射，供解释兼容矩阵复用）。模型名 `rf_v1`，版本键 `v1`。
- **训练超参数摘要**（现实现核实）：`RandomForestClassifier(n_estimators=300, min_samples_leaf=100, max_depth=15, n_jobs=-1, random_state=seed)`（`data_model/pipelines/expert/model.py:143-145`），为 SHAP 可算性收敛的 D-14 版。**已登记偏差**：semantic / fused 线 rf 沿用 `min_samples_leaf=2`、不限深度（`data_model/tests/test_model_registry_parity.py:105-109` `RF_DOCUMENTED_DEVIATION`），跨线对比 rf 行同时差「特征模态」与「模型容量」两个变量。默认训练口径为 8 分类器（`expert/config.py:48`）；重构后超参数 schema 登记进 `algorithm` 表（未实现）。
- **随机种子与决策阈值**：`SEED=42`（`data_model/pipelines/expert/config.py:42`，`--seed` 默认值见 `expert/train.py:45`）；`DECISION_THRESHOLD=0.5`（`expert/config.py:43`）。新契约下阈值降级为出厂默认值，唯一权威是 `user_config.decision_threshold`（[database/README.md §6](../../database/README.md)，未实现）。
- **训练/检验划分**：共享时间序切分 `data_model/data/split_szz_train.csv` / `split_szz_test.csv`（`expert/config.py:18-19`），按 `committed_at` 升序前 70% / 后 30%（`data_model/preparation/05_split_dataset.py:39` `DEFAULT_RATIO=0.70`），禁止随机切分；比例为可配置默认参数（[database/README.md §4](../../database/README.md)）。
- **数据集版本**：默认 = Apache Camel tag `camel-4.23.0` 快照（`EXPECTED_HEAD` 校验，`data_model/preparation/01_extract_commits.py:41`），登记为 `dataset` 表默认数据集版本（[database/README.md §1](../../database/README.md)）。
- **工件登记目标**（[model_artifact 表](../../database/model_artifact.md)，未实现）：`weight_path=data_model/pipelines/expert/models/rf_v1.pkl`；`checksum_sha256` / `size_bytes` / `status`（available / load_failed / retired）/ `train_job_id` 由训练服务产出并登记，`model` 表行由登记派生，`model_registry` 只读登记结果并校验文件。现状仍为 manifest 扫描 + DB 双真相源（database/README.md §0）。
- **交付方式**：离线 `joblib.dump` 导出 `.pkl`（`data_model/pipelines/expert/train.py:299`），在线 `joblib.load`；交付清单 `feature_order.txt` 由 `write_feature_order` 生成（`expert/train.py:188-229`），过渡期保留（database/model_artifact.md「过渡期」）。
- **旧表述废止注记**（仅注记，不改上文）：
  - 卡片「注册 = `feature_order.txt` 的 `[models]` 之一，后端启动按清单加载」为旧口径：新契约唯一登记源是 `model_artifact`，清单只是过渡期交付产物。旧表述废止，见 [database/README.md](../../database/README.md)。
  - 卡片「判定 = `risk_score ≥ 0.5` 高风险、`≥ 0.2` 中风险」为旧口径：判定阈值与展示阈值的唯一权威是 `user_config`（[database/user_config.md](../../database/user_config.md)、README §6）。旧表述废止，见 database/README.md；现状实现仍为常量（未实现配置化）。
