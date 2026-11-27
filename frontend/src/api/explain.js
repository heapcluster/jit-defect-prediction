import request, { SYNC_TIMEOUT, fetchBinary } from './request'

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

export function fetchExplainOutput(jobId, name) {
  return fetchBinary(`/api/explain/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`, {
    label: '解释下载',
    serverError: '解释下载服务异常'
  })
}
