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
