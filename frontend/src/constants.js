// 三页面共用的常量：**口径只在这一处定义**，页面不各自硬编码。
// 依据：docs/frontend/pages.md §5（阈值/三态）、§6（模型下拉静态清单）、
//       docs/model/feature-columns.md 第三节（14 项特征五维度分组）、
//       docs/backend/api-spec.md §三.1（分页默认 20、上限 100）。

/** 模型下拉静态清单（pages.md §6：MVP 前端维护，不新增接口） */
export const MODEL_OPTIONS = [
  'xgb_v1',
  'rf_v1',
  'lr_v1',
  'lgbm_v1',
  'et_v1',
  'svm_v1',
  'mlp_deep_v1',
  'tabnet_v1'
]

/** 风险着色阈值（pages.md §5：≥0.5 高 / ≥0.3 中 / 其余常规） */
export const RISK_HIGH = 0.5
export const RISK_MID = 0.3

/** 分页（api-spec.md §一：默认 20、上限 100） */
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

/** 解释条最多显示条数（pages.md §3：按 |contribution| 降序，只显前 8） */
export const MAX_EXPLANATION = 8

/** 14 项特征按 Kamei 五维度分组（列名与 feature-columns.md 第三节逐字一致） */
export const FEATURE_GROUPS = [
  { name: '代码分布', keys: ['ns', 'nd', 'nf', 'entropy'] },
  { name: '规模', keys: ['la', 'ld', 'lt'] },
  { name: '目的', keys: ['fix'] },
  { name: '历史', keys: ['ndev', 'age', 'nuc'] },
  { name: '开发者经验', keys: ['exp', 'rexp', 'sexp'] }
]

/** 时间控件转 ISO 8601 带时区（api-spec.md §一） */
export const DATETIME_FORMAT = 'YYYY-MM-DDTHH:mm:ssZ'
