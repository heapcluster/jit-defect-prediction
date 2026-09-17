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

#### Scenario: 出现契约未定义的列名（边界场景）
- **WHEN** 特征表校验时发现契约二第二、三节未定义的列名，或缺列、改名
- **THEN** 校验判定失败，必须先改契约再重跑，MUST NOT 带着未定义列名进入模型训练

### Requirement: 历史类特征 MUST 使用完整历史

`ndev` / `age` / `nuc` / `exp` / `rexp` / `sexp` 等历史类特征 MUST 基于窗口之前的完整提交历史计算；`--since` 参数只决定「给哪些提交算特征」，MUST NOT 截断历史。

#### Scenario: 窗口运行不缩水历史
- **WHEN** 以 `--since 2023-01-01` 只给 2023 年后的提交算特征
- **THEN** 历史类特征的输入仍覆盖 2005 年起的全部提交，与全量运行时同一条提交的特征值一致

#### Scenario: 窗口越界或非法（边界场景）
- **WHEN** `--since` 取值早于仓库首个提交（2005-12-12），或传入无法解析的日期字符串
- **THEN** 按全量处理或显式报错退出；MUST NOT 因窗口越界而产出空特征表或半截结果

### Requirement: 全量产物与统计报告 MUST 可入库可复现

特征表落 `data_model/data/`（不入库）；统计报告落 `data_model/reports/feature_stats.md`（可入库），报告 MUST 含 14 项特征的取值外沿与契约缺口登记结论。

#### Scenario: 干净环境复现
- **WHEN** 在干净 clone 上按 `docs/data-pipeline.md` 第 5 节命令重跑特征计算
- **THEN** 特征表与既有产物逐值一致（版本已固定，允许 ±0）

#### Scenario: 上游产物缺失（边界场景）
- **WHEN** 干净 clone 后 `data_model/data/` 内尚无 01 / 02 的中间产物，就直接执行 03
- **THEN** 流程以非零退出码终止并提示先跑上游步骤，MUST NOT 产出零行特征表冒充完成

### Requirement: 无法计算特征的提交 MUST 显式排除并计数

对无法定位历史（如根提交无先前记录导致某历史类特征无定义）的提交，MUST 按固定规则 **记 0** 并写入报告，MUST NOT 静默跳过、也 MUST NOT 中途改规则。

> **为什么钉死「记 0」而不是「排除」**：已产出的特征表是 **11,050 行 = 提交清单全量**，说明实现走的是「记 0」；若走「排除」，行数会少于全量。原文同时允许两种互斥规则、又不指定哪一种，与本节「干净环境复现、逐值一致」直接冲突 —— 选不同规则行数就不同。**口径钉死为「记 0」**，与 `03_extract_features.py` 的 `log_v1`（非 0 取 `ln(x)`、0 值记 0）一致。

#### Scenario: 边界提交处理透明
- **WHEN** 存在历史类特征无定义的提交
- **THEN** 报告列出处理规则与受影响条数，规则在全量运行中一致应用
