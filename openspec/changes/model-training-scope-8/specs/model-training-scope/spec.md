# model-training-scope

## ADDED Requirements

### Requirement: 训练口径固定为 8 个分类器

三条分类器线（`expert` / `semantic` / `fused`）的默认训练集合 MUST 为 `lr`、`rf`、`xgb`、`lgbm`、`et`、`svm`、`mlp_deep`、`tabnet` 共 8 个，且三处 `config.DEFAULT_MODELS` MUST 逐字相同。

`model.py::MODEL_NAMES` MAY 保留 12 个注册项（含 `nb` / `dt` / `knn` / `mlp`）以兼容旧产物，但这些模型 MUST NOT 进入默认训练、MUST NOT 计入四线对比。

#### Scenario: 不带 --models 直接训练

- **WHEN** 在干净环境执行 `python -m pipelines.fused.train`
- **THEN** 只训练 8 个模型，报告表格为 8 行
- **AND** 报告标题显示「8 分类器」
- **AND** `models/manifest.txt` 的 `[models]` 段行数等于 8

#### Scenario: 默认集合被改回 12 个

- **WHEN** 有人把任一线的 `DEFAULT_MODELS` 改回 12 个并提交
- **THEN** `tests/test_model_registry_parity.py::test_all_three_lines_share_the_same_default_model_set` 必须失败
- **AND** CI 阻断合入

### Requirement: 预算感知 effort 口径按单位配置评审下限

effort-aware 的 `budget` 对照口径 MUST 使用与 effort 代理单位一致的下限：LOC 口径为行数（`MIN_REVIEW_LOC`），`nf` 口径为文件数（`MIN_REVIEW_FILES`）。`budget_order` MUST 由调用方传入 `floor`，MUST NOT 在函数内假设固定值。

未提供下限时，`effort_aware_metrics` MUST NOT 产出 `budget` 项。

#### Scenario: nf 口径误用 LOC 的下限

- **WHEN** 对 `nf` 口径传入 `floor=10`
- **THEN** 所有提交都被判为「不可单独评审」，排序退化为按分数降序
- **AND** `tests/test_effort_scope_and_narrative.py::test_floor_unit_follows_effort_unit` 覆盖该退化行为

#### Scenario: 报告中的预算感知列

- **WHEN** 用完整 8 模型跑 `train.py`
- **THEN** 报告 §2 每个模型有 3 行（模型排序 / 预算感知 / 无下限密度）
- **AND** 「20% 预算审到的条数」列有值，且预算感知行的条数显著小于无下限密度行

### Requirement: 报告结论必须由本轮结果计算

报告中的定性结论（负 `P_norm` 的模型数、最差模型名、规模相关系数区间、预算覆盖条数、中位 LOC）MUST 全部由本轮 `results` 计算得出，MUST NOT 硬编码具体模型名或固定数量。

#### Scenario: 子集训练

- **WHEN** 执行 `--models lr`
- **THEN** 报告只包含 `lr_v1` 一行
- **AND** 结论段不出现其他模型名

#### Scenario: 结果非负

- **WHEN** 本轮所有模型的 `P_norm` 均不小于 0
- **THEN** 报告 MUST NOT 出现「全为负」措辞
- **AND** 仍给出 ρ 区间与成本对照

### Requirement: 权威指标只由重训产出

`model_metrics.md` MUST 由在本轮切分上重新训练的模型生成。`--from-saved`（旧权重复算）MUST 默认写入 `model_metrics_from_saved.md`，并在文首标注「探索性、非权威指标」，MUST NOT 覆盖 `model_metrics.md`。

训练入口 MUST 校验训练集与检验集的 `commit_hash` 无交集，有交集时拒绝产出报告。

#### Scenario: 切分重叠

- **WHEN** `split_szz_train.csv` 与 `split_szz_test.csv` 存在相同 `commit_hash`
- **THEN** `train.py` 打印重叠条数并返回退出码 2
- **AND** 不写出任何报告文件
