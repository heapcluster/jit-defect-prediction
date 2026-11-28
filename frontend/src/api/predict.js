import http from './http'

export const importFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/predict/import', form)
}

export const precheck = (datasetId) => http.post('/predict/precheck', { dataset_id: datasetId })

export const importModel = (file, line) => {
  const form = new FormData()
  form.append('file', file)
  form.append('line', line)
  return http.post('/predict/import-model', form)
}

export const saveModel = (payload) => http.post('/predict/save-model', payload)

export const run = (payload) => http.post('/predict/run', payload)

export const getRows = (jobId, params) => http.get(`/predict/results/${jobId}/rows`, { params })

export const exportResult = (jobId, params) =>
  http.get(`/predict/results/${jobId}/export`, { params, responseType: 'blob' })

export const saveResult = (jobId, name) => http.post('/predict/save', { job_id: jobId, name })

export const getDetail = (jobId, commitHash) =>
  http.get(`/predict/results/${jobId}/commits/${commitHash}`)

export const explain = (payload) => http.post('/predict/explain', payload)

export const localize = (payload) => http.post('/predict/localize', payload)
