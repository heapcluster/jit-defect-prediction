# codebert_e2e_v1

**CodeBERT（端到端） · e2e 线 · 在线交付**

直接以提交的代码文本为输入（不做人工特征工程），预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=codebert_e2e_v1` 返回指标与图集 |
| 定位 | 全项目**唯一端到端模型**，用于验证「免特征工程」路线是否可行 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 提交代码文本（CodeBERT 编码，非 14 维结构化特征） |
| 结构 | `build_model(text_model)`，见 `pipelines/e2e/model.py` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/codebert_e2e_v1.pkl`，`joblib.load` 读取 |
| 依赖 | torch 2.14.1、transformers（CodeBERT 权重另行取得，不入库） |

## 性能（测试集 25,183 条）

AUC **0.7553** ｜ AP 0.2722 ｜ F1 0.1125 ｜ P 0.3155 ｜ R 0.0685 ｜ Acc 0.8447

## 局限

- **F1 仅 0.113、召回 0.069**，端到端路线在当前数据规模下明显不如结构化特征（expert 线 0.43 F1）
- 不产出 `feat_importance` 图（无 14 维可解释列），只有 5 张图
- 依赖 CodeBERT 权重与 torch，环境最重

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核

## 训练配置与工件登记（重构契约）

`实现状态：部分` `期次：一期`（现有卡片内容 = 已实现的离线训练与评估；在线工件登记 / 热加载 / 超参数配置化 = 未实现）

> 本节为重构期追加的目标契约，需求输入 `TODO/00`、`TODO/01`、`TODO/04`；代码引用均为仓库根相对路径（已逐一核实）。上文原有指标数字、结论与基线（`afdee84`）引用全部保留，不因本节改写。

- **所属线与算法**：`line=e2e`、`algo=codebert_e2e`，对应 [algorithm 表](../../database/algorithm.md)默认登记清单 e2e 行（enabled=1，超参数为学习率 / epoch / max_len）；family=`transformer`（按该表族词表映射，供解释兼容矩阵复用）。模型名 `codebert_e2e_v1`（`data_model/pipelines/e2e/config.py:33`），版本键 `v1`，模态标识 `FEATURE_VERSION="codebert"`（`e2e/config.py:34`）。
- **训练超参数摘要**（现实现核实）：骨干 `microsoft/codebert-base` + 二分类头 `AutoModelForSequenceClassification(num_labels=2)` 整网微调（`data_model/pipelines/e2e/model.py:16-17`）；`EPOCHS=4`、`BATCH_SIZE=16`、`LEARNING_RATE=2e-5`、`WEIGHT_DECAY=0.01`、`GRAD_ACCUM_TARGET=32`（有效 batch=32）、`MAX_LEN=512`（`e2e/config.py:13-19`，梯度累积换算见 `e2e/train.py:102`）；CUDA 可用时 fp16、`load_best_model_at_end=True`、选优指标 loss（`e2e/train.py:103-121`）。重构后超参数 schema 登记进 `algorithm` 表（未实现）。
- **随机种子与决策阈值**：`SEED=42`（`data_model/pipelines/e2e/config.py:31`；`hf_set_seed / torch.manual_seed / np.random.seed` 三处固定，`e2e/train.py:58-60`）；`DECISION_THRESHOLD=0.5`（`e2e/config.py:32`；`e2e/metrics.py:28` 另有一份同值常量，重构应收敛单源）。新契约下阈值降级为出厂默认值，唯一权威是 `user_config.decision_threshold`（[database/README.md §6](../../database/README.md)，未实现）。
- **训练/检验划分**：优先对齐共享时间序切分 `data_model/data/split_szz_train.csv` / `split_szz_test.csv`（`e2e/config.py:24-25`），按 `committed_at` 升序前 70% / 后 30%（`data_model/preparation/05_split_dataset.py:39` `DEFAULT_RATIO=0.70`），禁止随机切分；共享切分缺失时按时间序尾部 `EVAL_FRAC=0.1` 留验兜底（`e2e/config.py:20`、`e2e/train.py:76-81`）；Trainer 选优验证集取训练尾部时间序 10%，检验集不参与模型选择（`e2e/train.py:87-90`）。
- **数据集版本**：默认 = Apache Camel tag `camel-4.23.0` 快照（`EXPECTED_HEAD` 校验，`data_model/preparation/01_extract_commits.py:41`），登记为 `dataset` 表默认数据集版本（[database/README.md §1](../../database/README.md)）；文本输入 `e2e/data/commit_text.csv` 由 `build_text_dataset.py` 产出（`e2e/config.py:23`）。
- **工件登记目标**（[model_artifact 表](../../database/model_artifact.md)，未实现）：`weight_path=data_model/pipelines/e2e/models/codebert_e2e_v1/`（**目录**，`e2e/config.py:27`）；`checksum_sha256` / `size_bytes` / `status`（available / load_failed / retired）/ `train_job_id` 由训练服务产出并登记，`model` 表行由登记派生，`model_registry` 只读登记结果并校验文件。现状仍为 manifest 扫描 + DB 双真相源（database/README.md §0）。
- **交付方式**：HF `save_pretrained` 目录交付（`model.safetensors` + config / tokenizer 文件，`data_model/pipelines/e2e/train.py:134-135`），**不是 .pkl**；后端按目录加载（`backend/app/model_registry.py:121-124`）。在线增量兜底（新提交现场构造 diff 文本走分类头）契约见 [database/README.md §5](../../database/README.md)（标记已实现）。
- **旧表述废止注记**（仅注记，不改上文）：
  - 卡片「产物 = `models/codebert_e2e_v1.pkl`，`joblib.load` 读取」与现实现不符：训练实际产出 safetensors 目录（`e2e/train.py:134-135`）。旧表述废止，见 [database/README.md](../../database/README.md) 与本节交付方式。
  - 卡片「注册 = `feature_order.txt` 的 `[models]` 之一，后端启动按清单加载」为旧口径：新契约唯一登记源是 `model_artifact`。旧表述废止，见 database/README.md。
  - 卡片「判定 = `risk_score ≥ 0.5` 高风险、`≥ 0.2` 中风险」为旧口径：判定阈值与展示阈值的唯一权威是 `user_config`（[database/user_config.md](../../database/user_config.md)、README §6）。旧表述废止，见 database/README.md；现状实现仍为常量（未实现配置化）。
