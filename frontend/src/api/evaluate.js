import http from './http'

export const importFile = (file, label) => {
  const form = new FormData()
  form.append('file', file)
  if (label) form.append('label', label)
  return http.post('/evaluate/import', form)
}

export const precheck = (datasetId) => http.post('/evaluate/precheck', { dataset_id: datasetId })

export const run = (payload) => http.post('/evaluate/run', payload)

export const getResult = (jobId) => http.get(`/evaluate/results/${jobId}`)

export const exportResult = (jobId, params) =>
  http.get(`/evaluate/results/${jobId}/export`, { params, responseType: 'blob' })

export const figureUrl = (jobId, type) => `/api/evaluate/results/${jobId}/figures/${type}`

export const figureBlob = (jobId, type) =>
  http.get(`/evaluate/results/${jobId}/figures/${type}`, { responseType: 'blob' })

export const saveHistory = (jobId, name) => http.post('/evaluate/save', { job_id: jobId, name })

export const listHistory = (params) => http.get('/evaluate/history', { params })

export const getHistory = (id) => http.get(`/evaluate/history/${id}`)

export const historyFigureUrl = (id, type) => `/api/evaluate/history/${id}/figures/${type}`

export const historyFigureBlob = (id, type) =>
  http.get(`/evaluate/history/${id}/figures/${type}`, { responseType: 'blob' })

export const exportHistory = (id, params) =>
  http.get(`/evaluate/history/${id}/export`, { params, responseType: 'blob' })

export const deleteHistory = (id) => http.delete(`/evaluate/history/${id}`)
