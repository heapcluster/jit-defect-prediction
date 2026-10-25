## MODIFIED Requirements

### Requirement: MUST 训练 8 个分类器

MUST 训练 8 个分类器（`lr` / `rf` / `xgb` / `lgbm` / `et` / `svm` / `mlp_deep` / `tabnet`），覆盖「经典机器学习」与「神经网络」两类，满足课程「至少 2 类不少于 8 种」；`expert` / `semantic` / `fused` 三线的默认训练集合 MUST 逐字相同，不再按 MVP 分期。

#### Scenario: 模型数量达标

- **WHEN** 训练流程完成
- **THEN** 产出 8 个模型文件，每个模型有独立 `model_name` 与评估指标

#### Scenario: 默认集合被改回子集（边界场景）

- **WHEN** 任一分类器线的默认训练集合被改回少于 8 个（例如只留 `lr` / `rf` / `xgb`）
- **THEN** 三线默认集合一致性测试失败并阻断合入；MUST NOT 以「不足 8 个」交付
