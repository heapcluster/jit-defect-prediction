# feature-extraction（特征抽取）

## Purpose

把样本集中的每次提交转为 Kamei 14 项特征向量，供模型训练消费。本 capability 登记的是**已实现并全量跑通**的内容（`03_extract_features.py`，产物见 `reports/feature_stats.md`），口径对齐 `docs/contracts/feature-columns.md` v1.0 —— 首个 change 当初把特征计算显式划出，此处补规格欠账。

## ADDED Requirements

### Requirement: 特征列名与取值口径 MUST 遵循契约二 v1.0

特征表 MUST 含契约二第二节全部标识列（`commit_hash` / `committed_at` / `feature_version`）与第三节全部 14 项特征列，列名逐字一致；取值口径 MUST 遵循契约二第四节 v1.0（含 `rexp` 衰减公式 `Σ count(n)/(n+1)`、六项 DECIMAL、`nuc` 按文件计数求和）。产出特征 MUST 标 `feature_version = v1`。

#### Scenario: 列名逐字比对
- **WHEN** 特征表产出后与 `docs/contracts/feature-columns.md` 第三节列名清单逐字比对
- **THEN** 缺列 0、多列 0、改名 0；`feature_version` 列全部为 `v1`

#### Scenario: 口径可复算
- **WHEN** 抽取任一提交按 v1.0 口径手工复算 `rexp` 与 `nuc`
- **THEN** 与特征表落盘值一致（浮点误差按 DECIMAL 精度允许）

### Requirement: 历史类特征 MUST 使用完整历史

`ndev` / `age` / `nuc` / `exp` / `rexp` / `sexp` 等历史类特征 MUST 基于窗口之前的完整提交历史计算；`--since` 参数只决定「给哪些提交算特征」，MUST NOT 截断历史。

#### Scenario: 窗口运行不缩水历史
- **WHEN** 以 `--since 2023-01-01` 只给 2023 年后的提交算特征
- **THEN** 历史类特征的输入仍覆盖 2005 年起的全部提交，与全量运行时同一条提交的特征值一致

### Requirement: 全量产物与统计报告 MUST 可入库可复现

特征表落 `data_model/data/`（不入库）；统计报告落 `data_model/reports/feature_stats.md`（可入库），报告 MUST 含 14 项特征的取值外沿与契约缺口登记结论。

#### Scenario: 干净环境复现
- **WHEN** 在干净 clone 上按 `docs/data-pipeline.md` 第 5 节命令重跑特征计算
- **THEN** 特征表与既有产物逐值一致（版本已固定，允许 ±0）

### Requirement: 无法计算特征的提交 MUST 显式排除并计数

对无法定位历史（如根提交无先前记录导致某历史类特征无定义）的提交，MUST 按固定规则处理（记 0 或排除）并写入报告，MUST NOT 静默跳过。

#### Scenario: 边界提交处理透明
- **WHEN** 存在历史类特征无定义的提交
- **THEN** 报告列出处理规则与受影响条数，规则在全量运行中一致应用
