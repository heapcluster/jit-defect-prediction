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

// 同步状态快照：GET /api/sync/status
export function getSyncStatus() {
  return request.get('/sync/status')
}

// 已预测时间覆盖：GET /api/commits/coverage（每个 model_name 的起止 committed_at）
export function getCommitsCoverage() {
  return request.get('/commits/coverage')
}

// 补齐到最新：POST /api/sync/catchup（无日期参数，补齐 DB→HEAD 缺口，不触发历史区间预测）
export function postSyncCatchup() {
  return request.post('/sync/catchup', null, { timeout: SYNC_TIMEOUT })
}

// 人工反馈：PUT /api/commits/{commit_hash}/label（标记 / 撤销「是否真的引入缺陷」）
export function putCommitLabel(hash, isDefect) {
  return request.put(`/commits/${hash}/label`, { is_defect: isDefect })
}

// 健康检查与运行状态：GET /api/health（observability）
export function getHealth() {
  return request.get('/health')
}

// SSE 订阅同步进度（fetch streaming，便于带 X-API-Key 鉴权；EventSource 不支持自定义头）
export function subscribeSyncProgress(onUpdate) {
  const token = import.meta.env.VITE_API_KEY
  const ctrl = new AbortController()
  ;(async () => {
    try {
      const resp = await fetch('/api/sync/stream', {
        headers: { 'X-API-Key': token },
        signal: ctrl.signal,
      })
      if (!resp.ok || !resp.body) return
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop() || ''
        for (const part of parts) {
          const line = part.trim()
          if (line.startsWith('data: ')) {
            try {
              onUpdate(JSON.parse(line.slice(6)))
            } catch {
              // 忽略坏帧
            }
          }
        }
      }
    } catch {
      // 终止或网络错误：静默
    }
  })()
  return ctrl
}
