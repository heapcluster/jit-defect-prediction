import http from './http'

export const importFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/clean/import', form)
}

export const run = (payload) => http.post('/clean/run', payload)

export const getSteps = (jobId) => http.get(`/clean/results/${jobId}/steps`)

export const getRows = (jobId, params) => http.get(`/clean/results/${jobId}/rows`, { params })

export const exportResult = (jobId, params) =>
  http.get(`/clean/results/${jobId}/export`, { params, responseType: 'blob' })
