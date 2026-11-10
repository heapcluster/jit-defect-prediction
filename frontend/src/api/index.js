import request, { SYNC_TIMEOUT } from './request'

// 风险列表：GET /api/commits（with_features / is_test 可选）
export function getCommits(params) {
  return request.get('/commits', { params })
}

// 提交详情：GET /api/commits/{commit_hash}（model_name 可选：与列表所选模型对齐）
export function getCommitDetail(hash, modelName) {
  return request.get(`/commits/${hash}`, {
    params: modelName ? { model_name: modelName } : undefined
  })
}

// 缺陷引入趋势：GET /api/trends
export function getTrends(params) {
  return request.get('/trends', { params })
}

// 在线预测：POST /api/predict（commit_hash 必填，model_name 可选）
export function postPredict(commitHash, modelName) {
  return request.post('/predict', {
    commit_hash: commitHash,
    model_name: modelName || undefined
  })
}

// 架构 → 模型层级：GET /api/models（级联选择器唯一数据源，前端不写死）
export function getModels(line) {
  return request.get('/models', { params: line ? { line } : undefined })
}

// 模型性能图 + 指标：GET /api/figures?model_name=
export function getFigures(modelName) {
  return request.get('/figures', { params: { model_name: modelName } })
}

// 数据同步：POST /api/sync（异步，提交即返回，靠 GET /api/sync/status 轮进度）
// 现算一条实测 P50 ≈ 108 秒，前端 MUST NOT 同步等结果
export function postSync({ line, modelName, startTime, endTime } = {}) {
  return request.post('/sync', null, {
    params: {
      line: line || undefined,
      model_name: modelName || undefined,
      start_time: startTime || undefined,
      end_time: endTime || undefined
    },
    timeout: SYNC_TIMEOUT
  })
}

// 同步状态快照：GET /api/sync/status
export function getSyncStatus() {
  return request.get('/sync/status')
}

// 健康检查与运行状态：GET /api/health（model_names = 已加载在线模型清单，供级联标注离线模型）
export function getHealth() {
  return request.get('/health')
}

// 带鉴权头取图（<img> 带不了 X-API-Key）：fetch 二进制转 ObjectURL（docs/api/figures.md）
export async function fetchFigureBlob(filePath) {
  const token = import.meta.env.VITE_API_KEY
  const resp = await fetch(filePath, { headers: { 'X-API-Key': token } })
  if (!resp.ok) throw new Error(`图片加载失败：${resp.status}`)
  const blob = await resp.blob()
  return URL.createObjectURL(blob)
}
