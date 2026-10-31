## MODIFIED Requirements

### Requirement: 交付模型 MUST 保持不变

本 change 经非作者评审并完成契约三同步后，在线交付清单 `data_model/pipelines/expert/models/feature_order.txt` 的 `[models]` 段 MUST 固定为 `lr_v1`、`rf_v1`、`xgb_v1`、`lgbm_v1`、`et_v1`、`svm_v1`、`mlp_deep_v1`、`tabnet_v1` 八项。清单以外的训练权重 MUST NOT 进入后端注册表；今后新增、移除或替换在线模型 MUST 再走模型切换 change。`python -m pipelines.expert.predict` 的离线产物 `prediction_result.csv` 口径与契约二 14 项列序 MUST 保持不变。

#### Scenario: 八模型交付清单一致

- **WHEN** 本 change 完成 apply 并提交八模型交付验收
- **THEN** `[models]` 恰有上述八项，后端加载清单、前端可选列表与契约三 §三.4 均为同一八项；8/8 加载和各模型预测有可复现证据

#### Scenario: 清单外权重（边界场景）

- **WHEN** 交付目录出现第九个训练权重，但 `[models]` 未声明
- **THEN** 后端 MUST NOT 加载或暴露该权重，前端也 MUST NOT 把它列为可选模型

#### Scenario: 模型未齐或未验收（边界场景）

- **WHEN** 八项中任一权重缺失、无法反序列化或未达到契约三的性能靶子
- **THEN** MUST NOT 宣称“八模型在线交付完成”；按既有运行时降级规则保持服务可用，并登记未通过项与下一步

#### Scenario: 交付清单不变

- **WHEN** 本次八模型切换完成并归档后再次交付权重或发布服务
- **THEN** `[models]` 段 MUST 仍为本 requirement 规定的八项；额外评估模型只在离线报告出现，不自动进入在线清单

#### Scenario: 评估出更优模型（边界场景）

- **WHEN** 后续评估显示第九个模型优于当前在线模型
- **THEN** MUST 另开模型切换 change 并评估后端与契约影响，MUST NOT 在本 change 或权重包中静默替换八项清单
