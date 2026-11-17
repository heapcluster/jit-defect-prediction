// 同步进度全局状态（Bug 修复：刷新是异步任务，切路由组件卸载后进度不能丢）。
//
// 轮询循环挂在模块级，不随组件销毁：离开风险列表页再回来仍能看到进度；
// 进页时若本地没在轮询但服务端 running=true（如整页刷新过），resumeIfRunning 会接上。
// startSync 同时返回「完成信号」，挂载中的页面可 await 它做结束提示与重查。
import { reactive } from 'vue'
import { postSync, getSyncStatus } from '../api'

export const syncProgress = reactive({
  running: false,
  phase: null,
  msg: '',
  lastError: null,
  done: 0,
  total: 0
})

let pollTimer = null
let completionResolvers = []

function stopTimer() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

function fmtElapsed(seconds) {
  const total = Math.max(0, Math.floor(seconds))
  if (total < 60) return `${total} 秒`
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`
}

export function formatSyncMessage(s) {
  if (!s.running) return ''
  const started = s.started_at ? Date.parse(s.started_at) : NaN
  const elapsed = Number.isFinite(started) ? (Date.now() - started) / 1000 : 0
  const suffix = elapsed >= 1 ? `（已 ${fmtElapsed(elapsed)}）` : ''
  if (s.phase === 'fetch') return `正在拉取源仓库…${suffix}`
  if (s.phase === 'plan') return `正在计算待补提交…${suffix}`
  if (s.phase === 'extract') {
    return `正在批量抽取特征${s.total ? `（${s.total} 条）` : ''}…${suffix}`
  }
  if (s.phase === 'predict') return `同步中 ${s.done}/${s.total}${suffix}`
  return s.total ? `同步中 ${s.done}/${s.total}${suffix}` : `同步中…${suffix}`
}

function applyStatus(s) {
  syncProgress.running = !!s.running
  syncProgress.phase = s.phase || null
  syncProgress.done = s.done || 0
  syncProgress.total = s.total || 0
  syncProgress.lastError = s.last_error || null
  syncProgress.msg = formatSyncMessage(s)
}

function finish() {
  stopTimer()
  const snapshot = { ...syncProgress }
  const resolvers = completionResolvers
  completionResolvers = []
  resolvers.forEach((resolve) => resolve(snapshot))
}

async function poll() {
  try {
    const s = await getSyncStatus()
    applyStatus(s)
    if (!s.running) {
      finish()
      return
    }
  } catch {
    // 轮询失败不判完成：网络抖动后再试，避免误报「已完成」
  }
  pollTimer = setTimeout(poll, 1500)
}

// 启动一次刷新：POST /api/sync 后由全局轮询接管，直到 running=false。
// 返回完成快照（{lastError,total,done}）；已有一个在跑时返回 null。
export async function startSync(params) {
  if (syncProgress.running) return null
  syncProgress.running = true
  syncProgress.phase = null
  syncProgress.msg = '正在提交同步请求…'
  syncProgress.done = 0
  syncProgress.total = 0
  syncProgress.lastError = null
  try {
    await postSync(params)
  } catch (e) {
    syncProgress.running = false
    syncProgress.msg = ''
    // 已有同步在跑：后端返回 40001「同步进行中」，接上轮询而不是报服务异常
    if (e?.code === 40001 && /同步进行中/.test(e?.detail || e?.message || '')) {
      await resumeIfRunning()
      return null
    }
    throw e
  }
  stopTimer()
  return new Promise((resolve) => {
    completionResolvers.push(resolve)
    poll()
  })
}

// 进页恢复：本地没轮询、但服务端在跑 → 接上轮询循环（无完成信号，靠全局状态显示）。
export async function resumeIfRunning() {
  if (syncProgress.running || pollTimer) return
  try {
    const s = await getSyncStatus()
    if (s.running) {
      applyStatus(s)
      poll()
    }
  } catch {
    // 忽略：恢复失败不影响正常查询
  }
}
