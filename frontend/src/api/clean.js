import request, { SYNC_TIMEOUT, fetchBinary } from './request'

export function getCleanOperations() {
  return request.get('/clean/operations')
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

export function fetchCleanOutput(jobId, name, format = 'csv') {
  return fetchBinary(`/api/clean/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}?format=${encodeURIComponent(format)}`)
}
