import http from './http'

export const getJob = (jobId) => http.get(`/jobs/${jobId}`)

export const cancelJob = (jobId) => http.post(`/jobs/${jobId}/cancel`)
