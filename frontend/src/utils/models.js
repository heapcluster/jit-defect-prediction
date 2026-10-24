// 交付模型清单（与 data_model/pipelines/expert/models/feature_order.txt 的 [models] 段一致）
// 加交付模型时：数据线更新 feature_order.txt 后，这里必须同步，否则前端下拉会静默少一项
export const MODELS = ['lr_v1', 'rf_v1', 'xgb_v1']
