# 数据采集与特征链路

本文只记录当前仓库可核对的技术口径；产品范围见 [`../overview.md`](../overview.md)，表字段见 [`../database/`](../database/)。运行生成的 CSV、报告与模型权重不入库，不能把旧报告条数当成当前实测。

## 1. 固定数据源

离线训练样本源为 Apache Camel：`https://github.com/apache/camel.git`，固定 tag `camel-4.23.0`，对应完整 commit `b2329103df8f5d1edfca2ad262be09e3be95ee68`。默认本地副本在 `data_model/data/camel/`，`01_extract_commits.py` 的 `EXPECTED_HEAD` 会校验版本；窗口参数 `--since` 只限制输出提交，不得截断历史类特征所需的前序提交。在线同步的源由后端 `SOURCE_REPO` 显式配置，取实时提交时不能把它误称为固定训练集。

## 2. 顺序与产物

在 `data_model/` 工作目录、环境与固定 Camel 副本就绪后，按以下顺序运行。`04_build_dataset` 的 `--labels` 是必填项；本例只构建主标签 `szz` 的样本集，`szz_lite` 对照集须另传其标签文件。大规模采集和 SZZ 可能耗时较长。

```powershell
python -m preparation.01_extract_commits
python -m preparation.02_szz_labeling --method szz
python -m preparation.03_extract_features
python -m preparation.04_build_dataset --labels data/commit_labels_szz.csv
python -m preparation.05_split_dataset --dataset data/dataset_szz.csv
```

各脚本的参数以 `--help` 为准；每一步须记录退出码、产物路径、样本数及当前 commit SHA。以上命令已核对参数入口，**不是本次完整采集和训练的通过证据**。

## 3. SZZ 判据与质量自检

`02_szz_labeling.py` 以大小写不敏感的词首边界 `\b(fix|bug|patch)` 识别候选修复提交，并用标准行级 `szz` 与简化版 `szz_lite` 对照。训练主标签为 `szz`；未打标的在线提交在 `commit_feature.is_bug_inducing` 中保持 `NULL`。当前脚本对正样本比例**落在 40%–60% 区间内**给出异常自检提示（常量 `ABNORMAL_LOW=0.40`、`ABNORMAL_HIGH=0.60`），这只是脚本质量检查，具体比例必须用固定数据源重跑报告核实。不要把“落在区间外告警”的旧说法和当前脚本混用。

候选修复提交必须同时含 `CAMEL-<数字>` 和上述修复语义词。词首边界允许 `fixes` 等词形变化，同时避免把 `dispatch`、`debug`、`prefix` 中的子串误收为修复语义。回溯未命中的修复提交既不进入样本，也不记作负样本。`szz` 为本仓库脚本实现的行级回溯，`szz_lite` 为文件级对照；两种方法的结果必须分别报告。

脚本中的候选命中外沿基准来自上游提交 `866b7dc` 对固定 Camel 版本的报告：含缺陷编号 38,716 条，同时命中编号与修复词首语义 7,787 条，同时命中编号与 `fix` 词首语义 6,631 条，完整提交数 84,461。**这些是历史基准，不代表当前机器已重新运行全量采集**。如果数据源、固定版本或过滤条件改变，应先重跑并重新登记基准，再进行外沿自检。

## 4. 特征与训练边界

`03_extract_features.py` 产出 Kamei 14 维；落库含义和 log 变换见 [`../database/commit_feature.md`](../database/commit_feature.md)。在线 expert 权重的列序以 `data_model/pipelines/expert/models/feature_order.txt` 为准。训练/检验按 `committed_at` 前 70% / 后 30% 时间序切分，禁止随机切分。`expert`、`semantic`、`fused` 三线默认各 8 个分类器，`e2e` 另 1 个；训练结果与在线交付权重是两种状态，见 [`../overview.md`](../overview.md)。

## 5. 统计与证据

采集条数、打标比例、特征缺口、切分边界应由本次运行的输出与 `data_model/preparation/reports/`（生成目录，未随仓库分发）记录。若该目录不存在，应写“尚未在本机生成”，不得引用历史数字冒充当前结果。对于报告中“40%–60%”告警，核对 `02_szz_labeling.py` 与 `04_build_dataset.py` 的判定方向一致后，再由负责人解释实际比例。

`04_build_dataset.py` 的七项统计为：过滤合并提交后的总提交数、UTC 时间跨度、打标成功数、正样本数、负样本数、正样本比例、打标方法。正样本比例是正样本数除以打标成功数。报告还须检查标签与提交清单、特征表能否按 `commit_hash` 对齐，并列出被排除的行数；不能用历史报告数字填当前验收结果。
