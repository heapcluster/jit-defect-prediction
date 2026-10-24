## ADDED Requirements

### Requirement: 八模型交付清单与在线选择

在八模型切换通过验收后，`POST /api/predict` SHALL 接受交付清单中的 `lr_v1`、`rf_v1`、`xgb_v1`、`lgbm_v1`、`et_v1`、`svm_v1`、`mlp_deep_v1`、`tabnet_v1` 作为可选 `model_name`，并从实际已加载的同名模型实时推理。前端三个页面的可选模型 SHALL 与同一清单一致；无权重或加载失败时仍遵守既有模型不可用错误与服务端日志规则，MUST NOT 返回伪造分数。验收时 MUST 证明八项全部成功加载，且各模型的 `POST /api/predict` n=100 压测 p95 < 500ms；运行时允许个别失败降级，但不等于八模型交付通过。

#### Scenario: 八模型逐一选择

- **WHEN** 八项权重均按有效清单成功加载，客户端逐一以其 `model_name` 调用 `POST /api/predict`
- **THEN** 每次响应回显所选模型名与真实风险分数，启动日志列出八个已加载模型，前端下拉与清单一致

#### Scenario: 不支持 SHAP 的在线模型

- **WHEN** `svm_v1`、`mlp_deep_v1` 或 `tabnet_v1` 已加载但没有适用的现行解释器
- **THEN** 沿用现行 `SHAP 解释` 的边界规则，正常返回 `risk_score` 且 `explanation=[]`；前端显示“该模型未提供特征解释”，MUST NOT 为填满解释而阻塞在线预测

#### Scenario: 清单外或未加载模型（边界场景）

- **WHEN** 请求的 `model_name` 不在交付清单，或虽在清单但权重缺失/加载失败
- **THEN** 前者按现有非法模型名规则返回 40001，后者按既有模型不可用规则返回 50000；响应 MUST NOT 泄露服务端权重路径

#### Scenario: 单模型性能未达标（边界场景）

- **WHEN** 某个已列模型的 100 次真实权重在线预测 p95 ≥ 500ms
- **THEN** 八模型交付验收 MUST 判为未完成并登记该模型与环境证据，MUST NOT 口头放宽契约三的统一靶子
