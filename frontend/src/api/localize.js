import request, { SYNC_TIMEOUT, fetchBinary } from './request'

export function getSourceTree(params) {
  return request.get('/source/tree', { params })
}

export function getSourceFile(params) {
  return request.get('/source/file', { params })
}

export function runLocalize(config, files = []) {
  const form = new FormData()
  for (const file of files) form.append('files[]', file, file.name)
  form.append('config', JSON.stringify(config))
  return request.post('/localize/run', form, { timeout: SYNC_TIMEOUT })
}

export function fetchLocalizeOutput(jobId, name) {
  return fetchBinary(`/api/localize/outputs/${encodeURIComponent(jobId)}/${encodeURIComponent(name)}`, {
    label: '定位下载',
    serverError: '定位下载服务异常'
  })
}
