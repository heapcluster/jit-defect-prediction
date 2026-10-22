# semantic / fused / e2e 配置说明与输出规范

> 适用范围：`pipelines/` 下**除 `expert/` 外**的三条对照线。
> 本文是三条线的**配置契约**与**产物契约**——改 `config.py` 默认值、改产物路径或字段、
> 改报告表结构，都必须同步本文与该包 `README.md`。单条命令的用法见各包 README。

## 0. 三线共同约定

| 项 | 约定 | 强制手段 |
|---|---|---|
| 切分 | 训练/检验行一律取自 `data_model/data/split_szz_{train,test}.csv` 的 `commit_hash`（时间序 70/30） | 各包 `config.py` 的 `TRAIN_CSV` / `TEST_CSV` |
| 指标口径 | 与 `expert/` 逐字一致：Effort-unaware（AUC/F1/Precision/Recall/Accuracy）+ Effort-aware（LOC 为工作量代理，P_norm / Recall@20% / Recall@50%） | 各包 `metrics.py` |
| 随机基线 | 200 次抽样，种子 0 | `RANDOM_BASELINE_REPEATS` / `RANDOM_BASELINE_SEED` |
| 判定阈值 | 0.5（仅用于统计正例数，不参与 AUC / P_norm 计算） | `DECISION_THRESHOLD` |
| 分类器族 | 12 个：`lr` `rf` `xgb` `lgbm` `et` `svm` `nb` `dt` `knn` `mlp` `mlp_deep` `tabnet`；三线 `MODEL_NAMES` / `build_model` 超参必须逐字相同 | `data_model/tests/test_model_registry_parity.py` |
| 模型命名 | 落盘文件与报告内 `model_name` 统一带线别后缀：`<name>_semantic_v1` / `<name>_fused_v1` / `codebert_e2e_v1` | 各包 `train.py` |
| 入库规则 | `data/`、`models/` **不入库**；`reports/`（Markdown + `figs/*.png`）**入库**，作为横向对比证据 | `.gitignore` |
| 包间衔接 | 只通过**数据文件**衔接，禁止跨包 `import` | 各包 `data.py` |
| 跑序 | `semantic` → `fused`；`e2e` 独立（文本由其 `build_text_dataset.py` 自建，格式与 `semantic` 互通） | — |

三条线都**不进交付链**，产物仅用于评估与横向对照。交付清单以 `expert/models/feature_order.txt` 的 `[models]` 为准（`lr_v1` + `rf_v1` + `xgb_v1`，与后端 `model_registry.load_models()` 对 `MODEL_DIR` 下全部 `*.pkl` 的加载范围一致），见 `data_model/ENVIRONMENT.md` §7。

---

## 1. semantic 线（冻结 CodeBERT 768 维 → 12 分类器）

### 1.1 配置说明（`semantic/config.py`）

| 参数 | 默认值 | 作用 | 调整约束 |
|---|---|---|---|
| `TEXT_MODEL` | `microsoft/codebert-base` | 冻结编码器 | 换底座即换特征空间，报告须登记；跨线对比失效 |
| `MAX_LEN` | `512` | token 上限 | CodeBERT 硬上限 512，不可上调 |
| `POOLING` | `mean` | 末层 hidden 按 attention_mask 做均值池化 | 改动即改变特征定义，需重编码 |
| `ENCODE_BATCH` | `32` | 编码批量 | 显存不足时下调，不影响结果 |
| `ENCODE_DEVICE` | `auto` | 有 CUDA 用 CUDA，否则 CPU | 全量编码建议 CUDA（CPU 约 50–150ms/条） |
| `MAX_CHARS` | `4000` | 单条提交文本字符上限 | 512 token ≈ 2000 字符，4000 为留余量；截断须在报告登记 |
| `SEED` | `42` | 分类器随机种子 | 三线一致，用于跨线可比 |
| `DEFAULT_MODELS` | 12 个（见 §0） | 默认训练的模型子集 | 用 `--models` 覆盖；报告只列实际训练的 |
| `DECISION_THRESHOLD` | `0.5` | 阈值 | 仅统计用 |
| `RANDOM_BASELINE_REPEATS` / `_SEED` | `200` / `0` | Effort-aware 随机基线 | 改动会破坏与 expert 的可比性 |

路径常量：`TEXT_CSV`=`semantic/data/commit_text.csv`、`EMBEDDINGS_NPZ`=`semantic/data/semantic_embeddings.npz`、`TRAIN_CSV` / `TEST_CSV` / `FEATURES_RAW_CSV` / `DATASET_CSV` 指向共享上游 `data_model/data/`。

### 1.2 CLI 覆盖（`python -m pipelines.semantic.train`）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--text-csv` | `semantic/data/commit_text.csv` | 复用 e2e 已建文本时指向 `pipelines/e2e/data/commit_text.csv` |
| `--repo` | 无 | 传仓库路径则本包自建文本（需 `--text-csv` 不存在或配合 `--force-encode`） |
| `--embeddings` | `semantic/data/semantic_embeddings.npz` | 编码缓存位置 |
| `--force-encode` | 关 | 忽略缓存重新编码 |
| `--train` / `--test` / `--features-raw` | 共享切分与原始特征 | 正常不应改 |
| `--models` | 12 个 | 逗号分隔子集，如 `lr,xgb` |
| `--seed` / `--model-dir` / `--report` | 见 `config.py` | 产物落点 |
| `--no-export` / `--no-charts` | 关 | 只出报告 / 不出图 |

### 1.3 输入契约

**文本 CSV**（`commit_text.csv`，本包自建或复用 e2e 的同名文件）

| 列 | 类型 | 说明 |
|---|---|---|
| `commit_hash` | str | 与共享切分的 `commit_hash` 对齐键 |
| `text` | str | 提交 diff 文本，≤ `MAX_CHARS` |
| `label` | 0/1 | `is_bug_inducing` |
| `feature_version` | str | 文本构造口径标识 |

写盘用 `QUOTE_ALL`（`text` 含换行/逗号）。

**编码缓存**（`semantic_embeddings.npz`，`np.load(..., allow_pickle=False)` 可读）

| 键 | 形状 / 类型 | 说明 |
|---|---|---|
| `commit_hash` | `U*` 定宽字符串 | 对齐键（定宽 dtype，避免被 pickle） |
| `embeddings` | `(N, 768)` `float32` | 冻结编码结果 |
| `labels` | `(N,)` int | 标签副本 |
| `feature_version` | `U*` 去重集合 | 口径标识 |

### 1.4 输出规范

| 产物 | 路径 | 格式 | 入库 |
|---|---|---|---|
| 编码缓存 | `semantic/data/semantic_embeddings.npz` | npz（见 §1.3） | 否 |
| 分类器 | `semantic/models/<name>_semantic_v1.pkl` ×N | joblib | 否 |
| 模型清单 | `semantic/models/manifest.txt` | `[encoder]` 编码器与维度 / `[models]` 每行 `pkl<TAB>中文名` / `[split]` 切分来源；**只列本次实际训练的模型** | 是 |
| 指标报告 | `semantic/reports/model_metrics.md` | 见下 | 是 |
| 图表 | `semantic/reports/figs/{roc_curves,effort_curves_loc,metric_bars}.png` | 150 dpi | 是 |

`model_metrics.md` 固定结构：

1. 标题 `# semantic 线模型评估指标（冻结 CodeBERT 768 维 → 12 分类器）`
2. `## 数据与参数`：编码器 / 向量维度 / 训练与检验条数 / 检验集正样本比例 / 随机种子 / 判定阈值
3. `## 一、Effort-unaware 指标（检验集）`：`模型 | AUC | F1 | Precision | Recall | Accuracy`，一行一个模型，模型列写成 `` `lr_semantic_v1`（逻辑回归） ``
4. `## 二、Effort-aware 指标（检验集，LOC 工作量代理）`：`排序方式 | 模型 | 曲线下面积 | P_norm | Recall@20% | Recall@50%`；每个模型两行（**模型排序** + 对照：密度排序），末尾追加 `上界：真实密度` 与 `基线：随机（200 次均值）`
5. `## 与 baseline 对照（读法）`：与 `pipelines/expert/reports/model_metrics.md` 并排解读
6. `## 图表`：引用 `figs/*.png`

### 1.5 校验与失败语义

- 文本为空 → 退出码 1（`data.py` 打印 `0 条有效文本` 后 `SystemExit(1)`）。
- 文本与编码缓存都缺、且未给 `--repo` → 退出码 **1**（`train.py` 用带字符串的 `SystemExit`）。
- 缓存**文件**不存在（`data.py::load_embeddings`）→ 退出码 **2**。
- 缓存存在但覆盖不全（`train.py` 打印缺多少条）→ 退出码 **1**。
- 语义指标不优于 baseline 时**如实登记**（样本量、文本构造、模型容量），不得只报更好的一组。
- 产物仅评估，不进交付链。

---

## 2. fused 线（Kamei 14 ⊕ 语义 768 = 782 维 → 12 分类器）

### 2.1 配置说明（`fused/config.py`）

| 参数 | 默认值 | 作用 | 调整约束 |
|---|---|---|---|
| `FEATURE_FIELDS` | 14 列（`ns nd nf entropy la ld lt fix ndev age nuc exp rexp sexp`） | 与 expert 同序（契约二第三节副本） | 顺序即特征语义，改动须同步 `expert` 与契约 |
| `LABEL_COL` | `is_bug_inducing` | 标签列 | — |
| `EXPECTED_DIM` | `len(FEATURE_FIELDS) + 768` = **782** | 拼接维度 | 由前两项推导，不手写 |
| `EMBEDDINGS_NPZ` | `semantic/data/semantic_embeddings.npz` | 模态 B 来源 | 包间唯一数据衔接，路径不可指向副本 |
| `SEED` / `DECISION_THRESHOLD` / 随机基线 | 同 §0 | 与 expert 一致 | 见 §0 |
| `DEFAULT_MODELS` | 12 个 | 同 semantic | 用 `--models` 覆盖 |

### 2.2 CLI 覆盖（`python -m pipelines.fused.train`）

`--train` `--test` `--features-raw` `--embeddings` `--models` `--seed` `--model-dir` `--report` `--no-export` `--no-charts`，默认值均取自 `config.py`。

### 2.3 输入契约

- 模态 A：`data/split_szz_{train,test}.csv` 自带的 14 列。
- 模态 B：`semantic/data/semantic_embeddings.npz`（键与 §1.3 相同，维度必须 `(N, 768)`，否则退出码 2）。
- 工作量代理：`data/commit_features_raw.csv` 的 `la + ld`。

### 2.4 输出规范

| 产物 | 路径 | 格式 | 入库 |
|---|---|---|---|
| 分类器 | `fused/models/<name>_fused_v1.pkl` ×N | joblib | 否 |
| 模型清单 | `fused/models/manifest.txt` | `[input]` 拼接口径（`Kamei 14 ⊕ 冻结语义 768 = 782 维` + 缓存路径）/ `[models]` 每行 `pkl<TAB>中文名`；只列本次训练的模型 | 是 |
| 指标报告 | `fused/reports/model_metrics.md` | 结构同 §1.4，差异见下 | 是 |
| 图表 | `fused/reports/figs/{roc_curves,effort_curves_loc,metric_bars}.png` | 150 dpi | 是 |

与 semantic 报告的差异：标题为 `# fused 线模型评估指标（Kamei14 ⊕ 语义 768 = 782 维 → 12 分类器）`；`## 数据与参数` 含 `输入维度 782（Kamei 14 + 语义 768）`、`语义缓存` 路径、`训练/检验条数（共享切分，内连接对齐）`、`语义覆盖率`（训练/检验内连接后的保留比例，由 `train.py` 计算后经 `report.render(coverage=...)` 写入）。

### 2.5 校验与失败语义

| 断言 | 触发条件 | 行为 |
|---|---|---|
| 语义覆盖率 | 内连接后 `coverage < 99%` | 退出码 2，打印缺失条数，拒绝训练 |
| 覆盖率不足 100% | `99% ≤ coverage < 100%` | 控制台警告 + 丢弃缺失行；训练/检验覆盖率写入报告 `## 数据与参数` 的「语义覆盖率」行 |
| 拼接维度 | `X.shape[1] != EXPECTED_DIM` | 退出码 2 |
| 缓存维度 | `emb.shape[1] != 768` | 退出码 2 |
| 原始特征缺行 | `commit_features_raw.csv` 缺检验集 hash | 退出码 2 |

- 782 维中 768 维来自冻结编码器，量纲与 Kamei 特征不同：`lr` / `knn` 的 `StandardScaler` 必须保留。
- fused 不优于 expert 时如实登记（语义无增量）并讨论原因。

---

## 3. e2e 线（CodeBERT 端到端微调）

### 3.1 配置说明（`e2e/config.py`）

| 参数 | 默认值 | 作用 | 调整约束 |
|---|---|---|---|
| `TEXT_MODEL` | `microsoft/codebert-base` | 骨干 | 换骨干需同步 `MODEL_DIR` 命名与报告 |
| `MAX_LEN` | `512` | token 上限 | 硬上限 |
| `EPOCHS` | `4` | 微调轮数 | 冒烟用 `--epochs 1` |
| `BATCH_SIZE` | `16` | 单卡批量 | 8GB 显存 OOM 时降到 8（有效批量由累积步补足） |
| `LEARNING_RATE` | `2e-5` | 学习率 | 微调常规区间，勿与分类器线混用 |
| `WEIGHT_DECAY` | `0.01` | 权重衰减 | — |
| `GRAD_ACCUM_TARGET` | `32` | 目标有效批量（`batch_size × 累积步`） | 改 `BATCH_SIZE` 时保持 32 |
| `EVAL_FRAC` | `0.1` | 共享切分缺失时的时间序尾部验证比例 | 仅在缺切分文件时生效，报告须标注 |
| `SEED` / `DECISION_THRESHOLD` | `42` / `0.5` | 同 §0 | — |
| `MODEL_NAME` | `codebert_e2e_v1` | HF 产物目录名与预测 CSV 的 `model_name` | **后端不加载该目录**：`MODEL_DIR` 只 `glob("*.pkl")`，本编号仅作评估标识；要上线须另立契约或导出可 joblib 加载的 pkl |
| `FEATURE_VERSION` | `codebert` | 模态标识 | 后端加载前须登记该版本 |
| `MODEL_DIR` / `REPORT` | `e2e/models/codebert_e2e_v1` / `e2e/reports/model_metrics.md` | 产物落点 | — |

### 3.2 CLI 覆盖

| 入口 | 参数 |
|---|---|
| `build_text_dataset.py` | `--dataset`（默认 `data/dataset_szz.csv`）`--repo` `--out`（默认 `e2e/data/commit_text.csv`）`--max-chars`（默认 4000）`--limit`（默认 0=全量） |
| `train.py` | `--text-csv` `--train` `--test` `--features-raw` `--text-model` `--model-dir` `--report` `--max-len` `--epochs` `--batch-size` `--lr` `--weight-decay` `--seed` `--eval-frac` `--no-charts` |
| `predict.py` | `--model-dir` `--text-csv` `--dataset` `--repo` `--out` `--report` `--max-len` `--model-name` `--feature-version` `--predicted-at` |

### 3.3 输入契约

- 文本 CSV：列同 §1.3（`commit_hash` / `text` / `label` / `feature_version`），由 `build_text_dataset.py` 产出，超大 diff 按 `MAX_CHARS` 截断、合并提交取第一父提交 diff。
- 切分与工作量代理同 §0 / §2.3。
- 首次运行需联网下载 `microsoft/codebert-base`（~500MB）；离线先落缓存再设 `HF_HUB_OFFLINE=1`。

### 3.4 输出规范

| 产物 | 路径 | 格式 | 入库 |
|---|---|---|---|
| 文本数据集 | `e2e/data/commit_text.csv` | CSV（`QUOTE_ALL`） | 否 |
| 微调权重 | `e2e/models/codebert_e2e_v1/` | HF 格式（`config.json` + 权重 + tokenizer + `checkpoints/`，仅保留 1 个） | 否 |
| 指标报告 | `e2e/reports/model_metrics.md` | 见下 | 是 |
| 图表 | `e2e/reports/figs/{roc_curves,effort_curves_loc}.png` | 150 dpi | 是 |
| 全量预测 | `e2e/data/prediction_result.csv` | 契约一表三，字段顺序固定 | 否 |
| 预测统计 | `e2e/reports/prediction_stats.md` | Markdown | 是 |

`model_metrics.md` 固定结构：`## 数据与参数`（骨干 / `feature_version` / 训练-验证-检验条数 / 最大长度-轮数-学习率 / 有效 batch / 种子 / 阈值 / 正样本比例 / 设备）→ `## 一、Effort-unaware`（单模型一行）→ `## 二、Effort-aware`（模型排序 / 密度排序 / 真实密度上界 / 随机基线；缺 `commit_features_raw.csv` 时整节替换为告警）→ `## 与 baseline 对照（读法）` → `## 图表`。

**`prediction_result.csv` 字段规范（与 `data_model/07_predict_all.py` 逐字一致，不多不少、顺序固定）**

| 顺序 | 字段 | 取值 |
|---|---|---|
| 1 | `commit_hash` | 全量提交（含检验集）的 hash |
| 2 | `model_name` | `codebert_e2e_v1`（`--model-name` 可覆盖） |
| 3 | `risk_score` | `softmax(logits)[:,1]`，格式 `%.5f`（0–1 字符串） |
| 4 | `predicted_at` | UTC `YYYY-MM-DD HH:MM:SS`（`--predicted-at` 可覆盖） |
| 5 | `feature_version` | `codebert`（`--feature-version` 可覆盖） |

写出后脚本会自校验：表头必须与上述 5 字段顺序完全一致（多/缺字段 → 退出码 1）；同时扫描自身源码，命中数据库驱动 import（`sqlalchemy` / `pymysql` / `mysql.connector` / `sqlite3` / `psycopg2`）→ 退出码 1。

`prediction_stats.md` 记录：模型、推理条数（全量，含检验集）、`feature_version`、`predicted_at`、输出文件名、以及 `risk_score ≥ 0.5` 的条数。

### 3.5 校验与失败语义

- 模型目录不存在 → 退出码 2（提示先跑 `train.py`）。
- 文本为空 → 退出码 1，不产出 CSV。
- 显存不足：先降 `--batch-size`（有效批量由 `GRAD_ACCUM_TARGET` 补足），不要改有效批量。
- GPU 非确定性算子会带来极小抖动，报告须登记设备与耗时。

---

## 4. 三线横向对照

| 项 | semantic | fused | e2e |
|---|---|---|---|
| 输入 | diff 文本 → 冻结 768 维 | Kamei 14 ⊕ 语义 768 = 782 | diff 文本 → 端到端微调 |
| 训练对象 | 12 个 sklearn/xgb 分类器 | 同左 | CodeBERT + 二分类头 |
| 算力 | 编码建议 GPU（CPU 仅够 `--limit` 冒烟） | CPU | **必须 GPU**（8GB 显存可跑） |
| 主要产物 | `*_semantic_v1.pkl` + `manifest.txt` + 报告 + 3 图 | `*_fused_v1.pkl` + `manifest.txt` + 报告 + 3 图 | `codebert_e2e_v1/` + 报告 + 2 图 + `prediction_result.csv` + `prediction_stats.md` |
| 前置 | 文本（自建或复用 e2e） | 先跑 semantic | 先跑 `build_text_dataset.py` |
| 交付链 | 否 | 否 | 否（是否进前端 switch 由后续契约变更决定） |

## 5. 改动流程

改任一线的配置或产物，必须同时更新：

1. 该包 `config.py`（默认值唯一来源）；
2. 该包 `README.md` 的「使用方法 / 产物」；
3. 本文对应的配置表与输出表；
4. 若涉及模型名单或超参，跑 `data_model/tests/test_model_registry_parity.py` 确认三线一致。
