// 交付模型清单（与 data_model/pipelines/expert/models/feature_order.txt 的 [models] 段一致）
// 加交付模型时：数据线更新 feature_order.txt 后，这里必须同步，否则前端下拉会静默少一项
// 2026-10-25 组长裁定（Issue #139）：8 模型全部上线；svm_v1/mlp_deep_v1/tabnet_v1 归因降级为空
// （核/深度模型无高效精确 SHAP 解释器，契约三 §4 允许，详情页对这三个显示「无归因」）
export const MODELS = ['lr_v1', 'rf_v1', 'xgb_v1', 'lgbm_v1', 'et_v1', 'svm_v1', 'mlp_deep_v1', 'tabnet_v1']
