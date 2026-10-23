import request from './request'

// 风险列表：GET /api/commits
export function getCommits(params) {
  return request.get('/commits', { params })
}

// 提交详情：GET /api/commits/{commit_hash}
export function getCommitDetail(hash) {
  return request.get(`/commits/${hash}`)
}

// 缺陷引入趋势：GET /api/trends
export function getTrends(params) {
  return request.get('/trends', { params })
}

// 在线预测：POST /api/predict（commit_hash 必填，model_name 可选）
export function postPredict(commitHash, modelName) {
  return request.post('/predict', {
    commit_hash: commitHash,
    model_name: modelName || undefined
  })
}
