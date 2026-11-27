import request, { SYNC_TIMEOUT } from './request'

// 数据同步：POST /api/sync（异步，提交即返回，靠 GET /api/sync/status 轮进度）
// 现算一条实测 P50 ≈ 108 秒，前端 MUST NOT 同步等结果
export function postSync({ line, modelName, startTime, endTime } = {}) {
  return request.post('/sync', null, {
    params: {
      line: line || undefined,
      model_name: modelName || undefined,
      start_time: startTime || undefined,
      end_time: endTime || undefined
    },
    timeout: SYNC_TIMEOUT
  })
}

// 同步状态快照：GET /api/sync/status
export function getSyncStatus() {
  return request.get('/sync/status')
}
