import http from './http'

export const getBranches = (repoUrl) => http.get('/collect/branches', { params: { repo_url: repoUrl } })

export const precheck = (repoUrl, branch, mode = 'expert') =>
  http.post('/collect/precheck', { repo_url: repoUrl, branch, mode })

export const run = (payload) => http.post('/collect/run', payload)

export const getRows = (jobId, params) => http.get(`/collect/results/${jobId}/rows`, { params })

export const exportResult = (jobId, params) =>
  http.get(`/collect/results/${jobId}/export`, { params, responseType: 'blob' })
