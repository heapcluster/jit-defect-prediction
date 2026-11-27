import request, { SYNC_TIMEOUT, fetchBinary } from './request'

export function getAlgorithms(params) {
  return request.get('/algorithms', { params })
}

export function runTrain(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/train/run', form, { timeout: SYNC_TIMEOUT })
}

export function getTrainCompare(jobId) {
  return request.get('/train/compare', { params: { job_id: jobId } })
}

export function fetchTrainOutput(jobId, name) {
  return fetchBinary(`/api/train/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`)
}
