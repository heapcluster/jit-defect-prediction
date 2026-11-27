import request, { SYNC_TIMEOUT, fetchBinary } from './request'

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

export function getCollectPreview(jobId, params = {}) {
  return request.get(`/collect/preview/${encodeURIComponent(jobId)}`, { params })
}

export function fetchCollectOutput(jobId, name) {
  return fetchBinary(`/api/collect/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`)
}
