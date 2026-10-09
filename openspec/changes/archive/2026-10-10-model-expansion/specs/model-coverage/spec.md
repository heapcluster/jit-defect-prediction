## Purpose

把模型组合的覆盖补到课程要求的「至少 2 类不少于 8 种」，并在同一口径下给出概率校准与阈值策略的证据，供契约三提案决策。

## ADDED Requirements

### Requirement: 模型组合 MUST 覆盖不少于 2 类且不少于 8 种

模型组合 MUST 同时满足：**类别数 ≥ 2**（至少含「经典机器学习」与「神经网络（深度学习）」两类的划分）且**模型数 ≥ 8**；每个模型 MUST 登记 `model_name`（`<算法>_v<序号>`）与所属类别，登记结果 MUST 落 `data_model/reports/`。

#### Scenario: 覆盖达标
- **WHEN** 覆盖矩阵报告产出
- **THEN** 报告中出现 8 个模型，每个模型有 `model_name`、所属类别与两类指标，且类别集合含「经典机器学习」与「神经网络（深度学习）」

#### Scenario: 只有一类（边界场景）
- **WHEN** 用经典机器学习族的模型凑到 8 种，但没有任何神经网络模型
- **THEN** 判定为**不达标**（类别数仍为 1），MUST 补神经网络类模型后才算完成

### Requirement: 新增模型 MUST 沿用既有时间序切分与特征口径

新增模型 MUST 复用既有的时间序切分产物与特征列序：训练/检验集 MUST 取自 `data/` 下已产出的切分文件（`split_szz_train.csv` / `split_szz_test.csv`），特征 MUST 为契约二第三节的 14 项且列序一致，随机种子 MUST 显式固定并写进报告。MUST NOT 为本 change 重新切分或改动特征取值口径。

#### Scenario: 同一份切分与同一套特征
- **WHEN** 训练任一新增模型
- **THEN** 使用既有切分文件与 14 项特征列序，报告中登记实际随机种子

#### Scenario: 为提升指标而改口径（边界场景）
- **WHEN** 有人通过改特征口径、改切分方式或改 `feature_version` 来提升某个模型的指标
- **THEN** MUST NOT 接受：口径变更须另开 change；本 change 的模型对比 MUST 在单一口径下完成

### Requirement: 每个模型 MUST 产出两类指标并汇总为矩阵报告

每个模型 MUST 同时产出 Effort-unaware 指标（AUC / F1 / 精确率 / 召回率 / 准确率）与 Effort-aware 指标（曲线下面积、`P_norm`、`Recall@20%`、`Recall@50%`，含 LOC 与改动文件数两种工作量代理），并汇总为矩阵报告，标注类别与**每类最优**。

#### Scenario: 矩阵完整
- **WHEN** 8 个模型训练完成
- **THEN** `reports/model_matrix.md` 含每个模型的两类指标、类别标注与每类最优行

#### Scenario: 缺检验集（边界场景）
- **WHEN** 切分文件缺失或时间序断言未通过
- **THEN** 不产出矩阵报告，脚本以非零退出码终止

### Requirement: 概率校准 MUST 使用时间序交叉验证

概率校准（isotonic / Platt）的折划分 MUST 保持时间先后（`TimeSeriesSplit` 或等价实现）；MUST NOT 使用随机 `KFold` / `ShuffleSplit`。报告 MUST 给出校准前后的 Brier 分数、对数损失与分箱可靠性表，并明确校准是否带来改善。

#### Scenario: 时间序折划分
- **WHEN** 执行概率校准
- **THEN** 每折的训练数据时间全部早于该折的校准数据，报告中写明折划分方式

#### Scenario: 随机折划分（边界场景）
- **WHEN** 实现里使用了随机 `KFold`
- **THEN** 判定为违反红线第 1 条（随机切分等于提前看到未来），本 change 不予接受

### Requirement: 阈值策略对照 MUST 在同一工作量下比较

「固定阈值 0.50」与「配额取前 1% / 5% / 10%」两种策略 MUST 在**同一工作量口径**下对照（同一工作量代理、同一检验集），报告 MUST 给出各自的召回、精确率与代价说明。结论 MUST 以提案（Issue #37 / #38）决策，MUST NOT 在本 change 内修改契约三语义。

#### Scenario: 等工作量对照
- **WHEN** 报告产出
- **THEN** 两种策略使用同一工作量代理（LOC 与改动文件数各一版），并给出等召回下的工作量差或等工作量下的召回差

#### Scenario: 证据指向改契约（边界场景）
- **WHEN** 证据显示配额策略显著更优
- **THEN** MUST 记入提案供决策，MUST NOT 在本 change 内改契约三的排序或阈值语义

### Requirement: 交付模型 MUST 保持不变

本 change MUST NOT 改动后端加载路径：`models/feature_order.txt` 的 `[models]` 段 MUST 保持既有交付模型不变，`07_predict_all.py` 的产物 `prediction_result.csv` 口径不变，新增模型 MUST NOT 进入后端加载清单。

#### Scenario: 交付清单不变
- **WHEN** 本 change 合入
- **THEN** `[models]` 段仍为既有交付模型，报告中新增模型标注为「评估用，不参与交付」

#### Scenario: 评估出更优模型（边界场景）
- **WHEN** 矩阵显示某新增模型在两类指标上均显著优于交付模型
- **THEN** 登记为「模型切换」提案（另开 change，含后端加载与契约影响评估），MUST NOT 在本 change 静默切换交付模型
