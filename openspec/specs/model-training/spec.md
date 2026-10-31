# model-training Specification

## Purpose
把带标签样本集训练成可用的 JIT 缺陷预测模型：按 `committed_at` 时间序切分，expert、semantic、fused 三条分类器线各训练同一组 8 个分类器，产出 Effort-unaware 与 Effort-aware 两类评估指标，全部结果可复现。e2e 为单独的端到端方案。

## Requirements

### Requirement: 训练集与检验集 MUST 按 committed_at 时间序切分

样本 MUST 按 `committed_at` 升序排列后切分：前 70% 为训练集、后 30% 为检验集。MUST 禁止随机切分、分层抽样切分或任何打乱时间顺序的切分方式。训练脚本 MUST 内置断言：检验集最早 `committed_at` > 训练集最晚 `committed_at`，断言失败 MUST 以非零退出码终止且不产出任何模型文件。

#### Scenario: 正常切分
- **WHEN** 对可训练样本集（`szz` 打标成功、剔除回溯未命中）执行时间序切分
- **THEN** 训练集取**前 70%**、检验集取**后 30%**（按 `committed_at` 升序），且检验集最早的 `committed_at` 晚于训练集最晚的 `committed_at`。切分后的具体条数以 `reports/split_stats_szz.md` 实测登记为准（**Apache Camel 待回填**）

> **分母不等于特征表行数**：提交清单／特征表的行数 **≠** 可训练样本集行数（差额为回溯未命中、被 D5 排除的提交，见 `reports/dataset_stats.md`）；`szz` 与 `szz_lite` 两套标签的行数也不同。切分前必须先读样本集实际行数，不要拿特征表行数当分母。
>
> **待实测回填（Apache Camel，2026-10-14 换库）**：换库前登记的具体行数已随换库失效，须在 Camel 全量跑完后重新登记。

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

### Requirement: MUST 训练 8 个分类器

expert、semantic、fused 三条分类器线 MUST 各训练相同的 8 个分类器：`lr`、`rf`、`xgb`、`lgbm`、`et`、`svm`、`mlp_deep`、`tabnet`。模型集合 MUST 同时覆盖经典机器学习与神经网络两类；e2e 作为单独的端到端方案，不计入此处每条线的 8 个分类器。

#### Scenario: 模型数量达标
- **WHEN** 训练流程完成
- **THEN** 每条分类器线产出上述 8 个模型的独立结果，每个模型有独立 `model_name` 与评估指标；三线默认集合逐字一致

#### Scenario: 任一分类器线回退为子集（边界场景）
- **WHEN** 任一分类器线的默认训练集合少于上述 8 个，或三线集合不一致
- **THEN** 判定训练覆盖未达标，MUST NOT 将子集标为本 Requirement 的完整交付

### Requirement: MUST 产出两类评估指标

评估 MUST 同时包含 Effort-unaware 指标（AUC、F1、精确率、召回率）与 Effort-aware 指标（按审查精力衡量性价比，如 Kamei 原文 P_opt 或同类 IFA/EPA 口径），全部在检验集上计算，落 `data_model/pipelines/expert/reports/`。

#### Scenario: 指标报告完整

- **WHEN** 任一模型训练完成
- **THEN** 报告目录下指标表同时含两类指标，并注明检验集时间范围与样本数

#### Scenario: 缺检验集不得出指标（边界场景）

- **WHEN** 检验集为空或时间序断言未通过
- **THEN** 脚本终止，报告目录下不产生任何评估指标

### Requirement: 训练结果 MUST 可复现

相同输入（样本集、标签、特征版本、超参）重复训练 MUST 得到相同评估结果（随机过程 MUST 显式固定随机种子）。

#### Scenario: 连跑两次结果一致
- **WHEN** 以相同命令与参数连续执行两次训练
- **THEN** 两份评估指标逐项一致

#### Scenario: 未显式传种子（边界场景）
- **WHEN** 命令行未传随机种子参数
- **THEN** 使用代码内的默认种子值，并在报告中登记实际取值；MUST NOT 依赖系统时间一类不可复现的随机源
