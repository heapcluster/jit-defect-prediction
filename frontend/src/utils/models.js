import { getModels } from '../api'

// 架构中文显示名：后端 /api/models 返回 label；本地兜底与后端常量映射同值（docs/api/models.md）
export const LINE_LABELS = {
  expert: '专家特征',
  semantic: '语义',
  fused: '融合',
  e2e: '端到端'
}

export const LINE_ORDER = ['expert', 'semantic', 'fused', 'e2e']

let cache = null
let inflight = null

// 模型层级（架构 → 模型）的唯一前端数据源：GET /api/models，前端不写死清单。
// 返回 [{ line, label, models: [] }]，固定顺序 expert → semantic → fused → e2e。
export function loadModelLines(force = false) {
  if (cache && !force) return Promise.resolve(cache)
  if (!inflight) {
    inflight = getModels()
      .then((data) => {
        cache = (data && data.lines) || []
        return cache
      })
      .finally(() => {
        inflight = null
      })
  }
  return inflight
}
