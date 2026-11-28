import http from './http'

export const importFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/train/import', form)
}

export const precheck = (datasetId) => http.post('/train/precheck', { dataset_id: datasetId })

export const run = (payload) => http.post('/train/run', payload)

export const getResult = (jobId) => http.get(`/train/results/${jobId}`)

export const downloadOutput = (jobId, name) =>
  http.get(`/train/outputs/${jobId}/${encodeURIComponent(name)}`, { responseType: 'blob' })

export const exportTestSet = (jobId, params) =>
  http.get(`/train/results/${jobId}/test-set/export`, { params, responseType: 'blob' })

export const saveAssets = (payload) => http.post('/train/save', payload)
