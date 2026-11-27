import request from './request'

// 配置元数据与生效值：选项、类型、来源均由后端提供。
export function getConfig(keys) {
  return request.get('/config', {
    params: keys ? { keys: Array.isArray(keys) ? keys.join(',') : keys } : undefined
  })
}

export function putConfig(items) {
  return request.put('/config', { items })
}

export function putConfigKey(key, value) {
  return request.put(`/config/${encodeURIComponent(key)}`, { value })
}

export function deleteConfigKey(key) {
  return request.delete(`/config/${encodeURIComponent(key)}`)
}
