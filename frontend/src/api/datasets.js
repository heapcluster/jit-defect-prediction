import request, { SYNC_TIMEOUT, storageOptions } from './request'

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
