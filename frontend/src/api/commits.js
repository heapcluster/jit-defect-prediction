import request from './request'

// 提交列表：GET /api/commits（模型性能页等；with_features 可选；model_name 必填）
export function getCommits(params) {
  return request.get('/commits', { params })
}

// 提交详情：GET /api/commits/{commit_hash}（model_name 可选：与列表所选模型对齐）
export function getCommitDetail(hash, modelName) {
  return request.get(`/commits/${hash}`, {
    params: modelName ? { model_name: modelName } : undefined
  })
}
