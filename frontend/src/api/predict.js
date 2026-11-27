import request, { SYNC_TIMEOUT, fetchBinary } from './request'

// 在线预测：POST /api/predict（commit_hash 必填，model_name 可选；opts 可传 decision_threshold/force_recompute）
export function postPredict(commitHash, modelName, opts = {}) {
  return request.post('/predict', {
    commit_hash: commitHash,
    model_name: modelName || undefined,
    ...(opts.decision_threshold != null ? { decision_threshold: opts.decision_threshold } : {}),
    ...(opts.force_recompute ? { force_recompute: true } : {})
  })
}

export function runPredict(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/predict/run', form, { timeout: SYNC_TIMEOUT })
}

export function getPredictPreview(jobId, params = {}) {
  return request.get(`/predict/preview/${encodeURIComponent(jobId)}`, { params })
}

export function fetchPredictOutput(jobId, name) {
  return fetchBinary(`/api/predict/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`)
}
