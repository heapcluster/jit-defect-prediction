import request, { fetchBinary } from './request'

// 模型性能图 + 指标：GET /api/figures?model_name=&job_id=
// 兼容旧调用 getFigures('model')；新调用传对象以按评估批次取图。
export function getFigures(target, jobId) {
  const params = typeof target === 'string'
    ? { model_name: target, job_id: jobId || undefined }
    : target
  return request.get('/figures', { params })
}

// 带鉴权头取图（<img> 带不了 X-API-Key）：fetch 二进制转 ObjectURL（docs/api/figures.md）
export async function fetchFigureBlob(filePath) {
  const blob = await fetchBinary(filePath, { label: '图片加载', serverError: '图片加载失败', includeStatus: true })
  return URL.createObjectURL(blob)
}
