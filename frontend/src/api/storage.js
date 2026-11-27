import request, { SYNC_TIMEOUT, fetchBinary, storageOptions } from './request'

export function importStorageFiles(files, config = {}) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/storage/import', form, { ...storageOptions, timeout: SYNC_TIMEOUT })
}

export function exportStorageTable(params) {
  return request.get('/storage/export', { ...storageOptions, params, timeout: SYNC_TIMEOUT })
}

export function getStorageLineage(params = {}) {
  return request.get('/storage/lineage', { ...storageOptions, params })
}

export function deleteStorageChain(chainId) {
  return request.delete(`/storage/chains/${encodeURIComponent(chainId)}`, {
    ...storageOptions, params: { confirm: true }
  })
}

export function fetchStorageOutput(jobId, name) {
  return fetchBinary(`/api/storage/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`)
}
