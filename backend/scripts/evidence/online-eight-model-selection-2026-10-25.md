# 八模型上线实测证据（change `online-eight-model-selection` / Issue #139）

> 执行：蒋励（模型线）｜ 日期：2026-10-25 ｜ 环境：Windows 11，MySQL 8.0.46，conda `jit-defect-prediction`
> （Python 3.12.14 / scikit-learn 1.9.1 / xgboost 3.4.1 / lightgbm 4.6.0 / torch 2.14.1+cpu / pytorch_tabnet / shap 0.52.0）
> 权重：`expert_models_20261024.zip` 解包（包级 md5 `57520463da2b94592842707874ab8c0d`，`rf_v1.pkl` = 12,715,033 B 收敛版）

## 1. 加载（启动口径，真实清单 8 项）

`model_registry.load_models()`（`feature_order.txt` `[models]` 段 8 项）：

```
loaded models: ['et_v1', 'lgbm_v1', 'lr_v1', 'mlp_deep_v1', 'rf_v1', 'svm_v1', 'tabnet_v1', 'xgb_v1']
```

- **8/8 加载成功，failed models 为空**；总耗时 9.8s（含 `et_v1.pkl` 546MB）。
- 特征宽度自检：8 个模型均通过（14 项；tabnet/svm/mlp 的 Pipeline 内层宽度经反序列化校验）。

## 2. 逐模型预测 + 归因（同一 14 维输入向量）

| 模型 | 形态 | `predict_proba` 延迟 | 归因项数 | 归因首查耗时 | 结论 |
|---|---|---|---|---|---|
| `lr_v1` | Pipeline(StandardScaler→LogisticRegression) | 35ms | 14 | 2.0s | 非空 |
| `rf_v1` | RandomForestClassifier | 92ms | 14 | 0.08s | 非空 |
| `xgb_v1` | XGBClassifier（默认模型） | 5ms | 14 | 0.29s | 非空 |
| `lgbm_v1` | LGBMClassifier | 5ms | 14 | 0.48s | 非空（修复 `_is_tree_family` 前为降级空） |
| `et_v1` | ExtraTreesClassifier | 86ms | 14 | 3.6s | 非空 |
| `svm_v1` | Pipeline(scaler→SVC RBF) | 3ms | 0 | — | 设计内降级（契约三 §4 允许空） |
| `mlp_deep_v1` | Pipeline(scaler→MLPClassifier) | 2ms | 0 | — | 设计内降级 |
| `tabnet_v1` | Pipeline(scaler→TabNetClassifier) | 10ms | 0 | — | 设计内降级 |

同一向量各模型风险分示例：lr 0.538 / rf 0.439 / xgb 0.614 / lgbm 0.644 / et 0.618 / svm 0.492 / mlp 0.415 / tabnet 0.700。

## 3. 修复记录

- **`model_registry._is_tree_family` 补 lightgbm 识别**：`LGBMClassifier` 模块为 `lightgbm.sklearn`、类名无 Tree/Forest/Boost 字样，原实现漏判 → 掉进 LinearExplainer 分支报 `InvalidModelError` → lgbm 归因被降级为空。修复后 lgbm 走 TreeExplainer，归因 14 项非空。回归测试：`test_is_tree_family_covers_lightgbm`、`test_explain_lightgbm_uses_tree_explainer`。
- **核/深度模型降级行为钉测试**：`test_explain_kernel_model_degrades_to_empty_without_raising`（SVC RBF：预测正常、归因为空数组、不抛异常）。

## 4. 性能口径

- 8 个模型 `predict_proba` 全部 < 130ms —— 契约三 §四「`POST /api/predict` 95% < 500ms」的**推理路径**对 8 模型全部成立。
- 归因首查耗时（et 3.6s / lr 2.0s）为 SHAP 解释器构造，不计入该靶子；契约三 §4 已写明此口径。
- 每模型 n=100 压测（`perf_loop.py` 逐模型隔离 `MODEL_DIR`）归后端线（吕建江）按 tasks 4.2 执行后补录。

## 5. 测试

- `backend/tests/test_model_registry.py`：新增 3 条（树族识别 / lgbm TreeExplainer / 核模型降级），全量通过；
- `data_model/tests/test_feature_contract.py`：`test_delivered_models_are_exactly_three` → `_eight`（清单 8 项断言），通过；
- `frontend/tests/models.spec.js`：动态比对 `[models]` 段，8 项一致，19/19 通过。
