import request, { SYNC_TIMEOUT, fetchBinary } from './request'

export function getEvaluateMetrics() {
  return request.get('/evaluate/metrics')
}

export function runEvaluate(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/evaluate/run', form, { timeout: SYNC_TIMEOUT })
}

export function fetchEvaluateOutput(jobId, name) {
  return fetchBinary(`/api/evaluate/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`)
}
