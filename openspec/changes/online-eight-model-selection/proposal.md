# 八个已训练模型进入在线可切换清单

> 起草：2026-10-24 ｜ 负责人：苏哲勋（契约与跨线协调）｜ 状态：待非作者评审

## Why

目前 8 个模型已训练，但 `feature_order.txt` 的 `[models]` 仅交付 `lr_v1`、`rf_v1`、`xgb_v1`。后端按该清单加载，前端也仅列这 3 个；对其余 5 个传 `model_name` 会被拒绝。新的 owner 要求是 8 个都能在线切换，不能只改前端选项或把训练权重放进目录就声称完成。

现行 `openspec/specs/model-coverage/spec.md` R6 明确冻结 3 模型交付；`delivery-model-allowlist` change 保证“只加载清单内模型”。本 change 是对 R6 的**显式模型切换提案**，保留“仅按清单加载”的安全边界，将批准后的交付清单扩至 8 个。

## What Changes

- 经评审后把交付清单固定为 `lr_v1`、`rf_v1`、`xgb_v1`、`lgbm_v1`、`et_v1`、`svm_v1`、`mlp_deep_v1`、`tabnet_v1`；同步契约三 `docs/backend/api-spec.md` §三.4、模型交付说明和前端清单。
- 后端只加载清单内且列序正确的权重；启动日志与验收证据必须能证明 8/8 可加载。单个权重失败仍按既有契约允许服务启动，但**不能把部分加载写成 8 模型验收通过**。
- 对 TreeExplainer / LinearExplainer 不适用的模型，提议沿用现有 `predict-api`“不支持的解释器”场景：正常返回风险与 `explanation=[]`，前端显示“该模型未提供特征解释”。此选择需模型、后端、前端负责人共签；不同意时先修订本提案，不先改实现。
- 维持 `POST /api/predict` p95 < 500ms、每模型 n=100 的靶子；8 款分别压测。未达标的模型不得标为已验收，也不得通过口头解释降低靶子。

## Capabilities

### Modified Capabilities

- `model-coverage`：R6 从“三模型保持不变”改为“批准后的八模型清单不得静默改变”。

### Added Capabilities

- `predict-api`：补充八模型交付清单与在线选择的可验收边界；既有 `模型加载`、`SHAP 解释` 的通用规则仍适用。

## Impact

涉及 `docs/backend/api-spec.md`、`data_model/pipelines/expert/models/feature_order.txt`、后端依赖与模型注册表、`frontend/src/utils/models.js`、三线测试和性能证据。按 owner 分包分别实施；本提案 PR 只提交 OpenSpec，不提前修改线上契约、权重或实现。

此变更扩展在线可选模型，但不增加接口、库表或特征列，不改变 `docs/design/sprint0-scope.md` 的建议性预警系统边界。MVP 三模型的现有联调可独立完成；8 模型切换只在跨线验收后宣布交付。

## 不做什么

- 不提交 `.pkl`、数据集或环境密钥，不把 8 个训练结果等同于 8 个在线可加载模型。
- 不采用 KernelSHAP 的 1–3 秒路径，也不按模型放宽 500ms 靶子；如需改性能契约须另开 change。
- 不改 `POST /api/predict` 请求/响应字段、错误码集合、默认模型规则或 14 项特征口径。
- 不代改模型、后端、前端负责人的代码与清单；不在本提案评审前改冻结契约正文。
