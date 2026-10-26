import request, { SYNC_TIMEOUT } from './request'

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

// PR 列表：GET /api/prs（实时拉 Camel 最新 open PR 的聚合风险）
export function getPrs(params) {
  return request.get('/prs', { params })
}

// PR 详情：GET /api/prs/{number}（该 PR 各 commit 的风险分）
export function getPrDetail(number, params) {
  return request.get(`/prs/${number}`, { params })
}

// 实时同步：POST /api/sync-prs（拉最新 open PR 并逐条现算预测入库）
// 长耗时：单条提交 × 8 模型约 4.1s，一条 PR 常有 20+ 提交，另加 GitHub 拉取耗时，
// 默认 10s 超时必挂（2026-10-25 修复）
export function postSyncPrs(limit) {
  return request.post('/sync-prs', null, { params: { limit }, timeout: SYNC_TIMEOUT })
}

// 实时同步：POST /api/sync（同步 Camel 仓库的提交历史并逐条现算预测入库）
// 同样属于长耗时端点，超时口径与 /api/sync-prs 一致
export function postSync(limit) {
  return request.post('/sync', null, { params: { limit }, timeout: SYNC_TIMEOUT })
}
