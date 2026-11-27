import request from './request'

export function getJobs(params) {
  return request.get('/jobs', { params })
}

export function getJob(jobId) {
  return request.get(`/jobs/${encodeURIComponent(jobId)}`)
}

export function retryJob(jobId) {
  return request.post(`/jobs/${encodeURIComponent(jobId)}/retry`)
}

export function cancelJob(jobId) {
  return request.post(`/jobs/${encodeURIComponent(jobId)}/cancel`)
}
