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

// 14 项特征中文名：**逐字对齐**后端 `app/explain.py::FEATURE_LABELS`（仅展示用）。
// 后端已在解释项里带 label；这里只用于「14 项特征」明细区（该区展示全部 14 项）。
export const FEATURE_LABELS = {
  ns: '变更子系统多',
  nd: '变更目录多',
  nf: '改动文件多',
  entropy: '改动分散',
  la: '代码改动量大',
  ld: '删除代码多',
  lt: '测试改动少',
  fix: '历史修复标记',
  ndev: '涉及开发者多',
  age: '文件陈旧',
  nuc: '近期改动频繁',
  exp: '作者历史经验低',
  rexp: '作者项目经验低',
  sexp: '作者近期经验低'
}

export function featureLabel(name) {
  return FEATURE_LABELS[name] || name
}
