import { getModels, getHealth } from '../api'

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

// 已加载（在线有权重）的模型名集合：来源 /api/health.model_names。
// 级联下拉据此把 semantic/fused/e2e 等仅离线评估的模型标注「（离线）」。
let onlineCache = null
let onlineInflight = null

export function loadOnlineModels(force = false) {
  if (onlineCache && !force) return Promise.resolve(onlineCache)
  if (!onlineInflight) {
    onlineInflight = getHealth()
      .then((data) => {
        onlineCache = new Set((data && data.model_names) || [])
        return onlineCache
      })
      .catch(() => {
        // 未知态（null）：加载失败时不得把在线模型误标成「（离线）」
        onlineCache = null
        return onlineCache
      })
      .finally(() => {
        onlineInflight = null
      })
  }
  return onlineInflight
}
