import request, { SYNC_TIMEOUT } from './request'

// 提交列表：GET /api/commits（模型性能页等；with_features 可选；model_name 必填）
export function getCommits(params) {
  return request.get('/commits', { params })
}

// 提交详情：GET /api/commits/{commit_hash}（model_name 可选：与列表所选模型对齐）
export function getCommitDetail(hash, modelName) {
  return request.get(`/commits/${hash}`, {
    params: modelName ? { model_name: modelName } : undefined
  })
}

// 在线预测：POST /api/predict（commit_hash 必填，model_name 可选；opts 可传 decision_threshold/force_recompute）
export function postPredict(commitHash, modelName, opts = {}) {
  return request.post('/predict', {
    commit_hash: commitHash,
    model_name: modelName || undefined,
    ...(opts.decision_threshold != null ? { decision_threshold: opts.decision_threshold } : {}),
    ...(opts.force_recompute ? { force_recompute: true } : {})
  })
}

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

export function runPredict(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/predict/run', form, { timeout: SYNC_TIMEOUT })
}

export async function fetchPredictOutput(jobId, name) {
  const path = `/api/predict/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    throw Object.assign(new Error(response.status >= 500 ? '下载服务异常，请稍后重试' : payload?.message || '下载失败'), { code })
  }
  return response.blob()
}

// 模型性能图 + 指标：GET /api/figures?model_name=&job_id=
// 兼容旧调用 getFigures('model')；新调用传对象以按评估批次取图。
export function getFigures(target, jobId) {
  const params = typeof target === 'string'
    ? { model_name: target, job_id: jobId || undefined }
    : target
  return request.get('/figures', { params })
}

export function getPredictPreview(jobId, params = {}) {
  return request.get(`/predict/preview/${encodeURIComponent(jobId)}`, { params })
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

// 带鉴权头取图（<img> 带不了 X-API-Key）：fetch 二进制转 ObjectURL（docs/api/figures.md）
export async function fetchFigureBlob(filePath) {
  const token = import.meta.env.VITE_API_KEY
  const resp = await fetch(filePath, { headers: { 'X-API-Key': token } })
  if (!resp.ok) throw new Error(`图片加载失败：${resp.status}`)
  const blob = await resp.blob()
  return URL.createObjectURL(blob)
}

// 配置元数据与生效值：选项、类型、来源均由后端提供。
export function getConfig(keys) {
  return request.get('/config', {
    params: keys ? { keys: Array.isArray(keys) ? keys.join(',') : keys } : undefined
  })
}

export function putConfig(items) {
  return request.put('/config', { items })
}

export function putConfigKey(key, value) {
  return request.put(`/config/${encodeURIComponent(key)}`, { value })
}

export function deleteConfigKey(key) {
  return request.delete(`/config/${encodeURIComponent(key)}`)
}

// Storage-only error normalization preserves structured safe validation detail without
// changing the W1 response interceptor or sending binary files through it.
const storageOptions = {
  transformResponse: [...request.defaults.transformResponse, data => {
    const detail = data?.error?.detail
    if (data?.code === 40001 && typeof detail === 'string') return { ...data, message: detail }
    return data
  }]
}

export function importStorageFiles(files, config = {}) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/storage/import', form, { ...storageOptions, timeout: SYNC_TIMEOUT })
}

export function exportStorageTable(params) {
  return request.get('/storage/export', { ...storageOptions, params, timeout: SYNC_TIMEOUT })
}

export function getDatasets(params) {
  return request.get('/datasets', { ...storageOptions, params })
}

export function getDatasetCommits(id, params) {
  return request.get(`/datasets/${encodeURIComponent(id)}/commits`, { ...storageOptions, params })
}

export function exportDataset(id, params = {}) {
  return request.get(`/datasets/${encodeURIComponent(id)}/export`, { ...storageOptions, params, timeout: SYNC_TIMEOUT })
}

export function deleteDataset(id) {
  return request.delete(`/datasets/${encodeURIComponent(id)}`)
}

export function runCollect(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/collect/run', form, { timeout: SYNC_TIMEOUT })
}

export function getCollectBranches(repoSource) {
  return request.get('/collect/branches', { params: { repo_source: repoSource } })
}

export function getCollectSourceColumns(sourceUrl) {
  return request.post('/collect/source-columns', { source_url: sourceUrl })
}

export function resaveCollect(jobId) {
  return request.post(`/collect/resave/${encodeURIComponent(jobId)}`)
}

export function getStorageLineage(params = {}) {
  return request.get('/storage/lineage', { ...storageOptions, params })
}

export function deleteStorageChain(chainId) {
  return request.delete(`/storage/chains/${encodeURIComponent(chainId)}`, {
    ...storageOptions, params: { confirm: true }
  })
}

export function getCleanOperations() {
  return request.get('/clean/operations')
}

export function getAlgorithms(params) {
  return request.get('/algorithms', { params })
}

export function getSourceTree(params) {
  return request.get('/source/tree', { params })
}

export function getSourceFile(params) {
  return request.get('/source/file', { params })
}

export function runLocalize(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/localize/run', form, { timeout: SYNC_TIMEOUT })
}

export async function fetchLocalizeOutput(jobId, name) {
  const response = await fetch(`/api/localize/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`, {
    headers: { 'X-API-Key': import.meta.env.VITE_API_KEY }
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    throw Object.assign(new Error(response.status >= 500 ? '定位下载服务异常' : payload?.message || '下载失败'), { code })
  }
  return response.blob()
}

export function getExplainTechniques(params) {
  return request.get('/explain/techniques', { params })
}

export function postExplain(commitHash, modelName, technique, params = {}) {
  return request.post('/explain', { commit_hash: commitHash, model_name: modelName, technique, params }, { timeout: SYNC_TIMEOUT })
}

export function runExplain(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/explain/run', form, { timeout: SYNC_TIMEOUT })
}

export async function fetchExplainOutput(jobId, name) {
  const response = await fetch(`/api/explain/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`, {
    headers: { 'X-API-Key': import.meta.env.VITE_API_KEY }
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    throw Object.assign(new Error(response.status >= 500 ? '解释下载服务异常' : payload?.message || '下载失败'), { code })
  }
  return response.blob()
}

export function getEvaluateMetrics() {
  return request.get('/evaluate/metrics')
}

export function runEvaluate(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/evaluate/run', form, { timeout: SYNC_TIMEOUT })
}

export async function fetchEvaluateOutput(jobId, name) {
  const path = `/api/evaluate/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    throw Object.assign(new Error(response.status >= 500 ? '下载服务异常，请稍后重试' : payload?.message || '下载失败'), { code })
  }
  return response.blob()
}

export function runTrain(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/train/run', form, { timeout: SYNC_TIMEOUT })
}

export async function fetchTrainOutput(jobId, name) {
  const path = `/api/train/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    throw Object.assign(new Error(response.status >= 500 ? '下载服务异常，请稍后重试' : payload?.message || '下载失败'), { code })
  }
  return response.blob()
}

export function runClean(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/clean/run', form, { timeout: SYNC_TIMEOUT })
}

export function getCleanPreview(jobId, params = {}) {
  return request.get(`/clean/preview/${encodeURIComponent(jobId)}`, { params })
}

export async function fetchCleanOutput(jobId, name, format = 'csv') {
  const path = `/api/clean/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}?format=${encodeURIComponent(format)}`
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    throw Object.assign(new Error(response.status >= 500 ? '下载服务异常，请稍后重试' : payload?.message || '下载失败'), { code })
  }
  return response.blob()
}

export function getJobs(params) {
  return request.get('/jobs', { params })
}

export function getJob(jobId) {
  return request.get(`/jobs/${encodeURIComponent(jobId)}`)
}

export function retryJob(jobId) {
  return request.post(`/jobs/${encodeURIComponent(jobId)}/retry`)
}

export function cancelJob(jobId) {
  return request.post(`/jobs/${encodeURIComponent(jobId)}/cancel`)
}

export function getCollectPreview(jobId, params = {}) {
  return request.get(`/collect/preview/${encodeURIComponent(jobId)}`, { params })
}

export async function fetchCollectOutput(jobId, name) {
  const path = `/api/collect/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw Object.assign(new Error(response.status >= 500 ? '下载服务异常，请稍后重试' : payload?.message || '下载失败'), { code: payload?.code })
  }
  return response.blob()
}

export async function fetchStorageOutput(jobId, name) {
  const path = `/api/storage/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    let payload
    try { payload = await response.json() } catch { /* Non-JSON errors have no safe detail. */ }
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    const message = code === 40100 ? '登录已失效，请重新登录'
      : code === 50000 || response.status >= 500 ? '下载服务异常，请稍后重试'
        : payload?.error?.detail || payload?.message || `下载失败（HTTP ${response.status}）`
    throw Object.assign(new Error(typeof message === 'string' ? message : '下载失败，请重试'), { code })
  }
  return response.blob()
}
