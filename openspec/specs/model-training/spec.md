# model-training Specification

## Purpose
把带标签样本集训练成可用的 JIT 缺陷预测模型：按 `committed_at` 时间序切分，训练 2–3 个经典模型，产出 Effort-unaware 与 Effort-aware 两类评估指标，全部结果可复现。

## Requirements

### Requirement: 训练集与检验集 MUST 按 committed_at 时间序切分

样本 MUST 按 `committed_at` 升序排列后切分：前 70% 为训练集、后 30% 为检验集。MUST 禁止随机切分、分层抽样切分或任何打乱时间顺序的切分方式。训练脚本 MUST 内置断言：检验集最早 `committed_at` > 训练集最晚 `committed_at`，断言失败 MUST 以非零退出码终止且不产出任何模型文件。

#### Scenario: 正常切分
- **WHEN** 对 **10,893 条可训练样本**（`szz` 打标成功数）执行时间序切分
- **THEN** 训练集约 **7,625** 条、检验集约 **3,268** 条，检验集最早 `committed_at` 晚于训练集最晚 `committed_at`

> **分母是 10,893 不是 11,050**：11,050 是提交清单／特征表行数，可训练样本集是 10,893 行（差 157 条为回溯未命中、被 D5 排除的提交，见 `reports/dataset_stats.md`）。`szz_lite` 对应 10,880 行。切分前必须先读样本集实际行数，不要拿特征表行数当分母。

#### Scenario: 切分断言拦截（边界场景）
- **WHEN** 切分实现存在缺陷（如排序列写错）导致时间序被破坏
- **THEN** 断言失败，脚本以非零退出码退出，控制台报「时间序被破坏」，不产出模型文件

### Requirement: 主训练标签 MUST 使用 szz

主模型训练 MUST 使用 `label_method = szz` 的标签（自研标准行级 SZZ，与 Kamei 原文口径可比）；`szz_lite` 仅作对照分析，MUST NOT 进入主模型训练或主指标报告。

#### Scenario: 指定标签训练
- **WHEN** 训练脚本读取样本集
- **THEN** 仅加载 `szz` 标签列训练，报告中标注「主标签 szz」

#### Scenario: 样本集缺 szz 标签（边界场景）
- **WHEN** 样本集中不存在 `szz` 标签列（例如只产出了 `szz_lite`）
- **THEN** 训练以非零退出码终止并提示缺列；MUST NOT 静默回退用 `szz_lite` 训练主模型

### Requirement: MUST 训练 2–3 个经典模型

MUST 训练 2–3 个经典机器学习模型（如逻辑回归 / 随机森林 / XGBoost）。前提：课程「至少 2 类不少于 8 种」的要求按 MVP 分期执行，口径待老师确认（飞书周报任务 12）。

#### Scenario: 模型数量达标
- **WHEN** 训练流程完成
- **THEN** 产出 2–3 个模型文件，每个模型有独立 `model_name` 与评估指标

#### Scenario: 时间不足时的取舍（边界场景）
- **WHEN** 时间预算只够训 1 个模型
- **THEN** MUST NOT 以「不足 2 个」交付 —— 规格下限是 2：宁可选更轻的算法把第二个凑出来，也不交付单模型

### Requirement: MUST 产出两类评估指标

评估 MUST 同时包含 Effort-unaware 指标（AUC、F1、精确率、召回率）与 Effort-aware 指标（按审查精力衡量性价比，如 Kamei 原文 P_opt 或同类 IFA/EPA 口径），全部在检验集上计算，落 `data_model/reports/`。

#### Scenario: 指标报告完整
- **WHEN** 任一模型训练完成
- **THEN** `reports/` 下指标表同时含两类指标，并注明检验集时间范围与样本数

#### Scenario: 缺检验集不得出指标（边界场景）
- **WHEN** 检验集为空或时间序断言未通过
- **THEN** 脚本终止，`reports/` 下不产生任何评估指标

### Requirement: 训练结果 MUST 可复现

相同输入（样本集、标签、特征版本、超参）重复训练 MUST 得到相同评估结果（随机过程 MUST 显式固定随机种子）。

#### Scenario: 连跑两次结果一致
- **WHEN** 以相同命令与参数连续执行两次训练
- **THEN** 两份评估指标逐项一致

#### Scenario: 未显式传种子（边界场景）
- **WHEN** 命令行未传随机种子参数
- **THEN** 使用代码内的默认种子值，并在报告中登记实际取值；MUST NOT 依赖系统时间一类不可复现的随机源
