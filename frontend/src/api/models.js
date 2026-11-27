import request from './request'

// 架构 → 模型层级：GET /api/models（级联选择器唯一数据源，前端不写死）
export function getModels(line) {
  return request.get('/models', { params: line ? { line } : undefined })
}

export function getModelsStatus(params) {
  return request.get('/models/status', { params })
}

export function loadModel(name) {
  return request.post(`/models/${encodeURIComponent(name)}/load`)
}

export function unloadModel(name) {
  return request.post(`/models/${encodeURIComponent(name)}/unload`)
}

export function reloadModel(name) {
  return request.post(`/models/${encodeURIComponent(name)}/reload`)
}

export function setSelectedModel(name) {
  return request.put('/models/selection', { model_name: name })
}
