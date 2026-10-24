// 特征五维分组（docs/frontend/pages.md 第 3 节；键名与 docs/model/feature-columns.md 14 项一致）
export const FEATURE_GROUPS = [
  { title: '代码分布', fields: ['ns', 'nd', 'nf', 'entropy'] },
  { title: '规模', fields: ['la', 'ld', 'lt'] },
  { title: '目的', fields: ['fix'] },
  { title: '历史', fields: ['ndev', 'age', 'nuc'] },
  { title: '开发者经验', fields: ['exp', 'rexp', 'sexp'] }
]

// 展平后的 14 项字段顺序（与 feature_order.txt [feature_order] 段一致）
export const FEATURE_FIELDS = FEATURE_GROUPS.flatMap((g) => g.fields)
