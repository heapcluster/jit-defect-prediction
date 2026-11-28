export const SOURCE_TYPE = {
  git_repo: '原始',
  upload: '导入清洗',
  clean: '清洗',
  split: '测试集',
  prediction: '预测结果'
}

export const LINE = {
  expert: '专家特征',
  semantic: '语义向量'
}

export const STATUS = {
  ready: '可用',
  failed: '异常',
  available: '可用',
  missing: '文件缺失'
}

export const JOB_STATUS = {
  queued: '排队中',
  running: '运行中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消'
}

export const METRIC_LABEL = {
  accuracy: 'Accuracy',
  precision: 'Precision',
  recall: 'Recall',
  f1: 'F1',
  auc: 'AUC',
  ap: 'AP',
  mcc: 'MCC'
}

export const FIGURE_LABEL = {
  roc: 'ROC 曲线',
  pr: 'PR 曲线',
  confusion: '混淆矩阵',
  bar: '指标柱状图'
}

export function statusType(status) {
  if (status === 'available' || status === 'ready' || status === 'success') return 'success'
  if (status === 'failed' || status === 'missing') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

export function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (Number.isNaN(number)) return '—'
  return `${(number * 100).toFixed(digits)}%`
}

export function formatNumber(value, digits = 4) {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (Number.isNaN(number)) return '—'
  return String(Number(number.toFixed(digits)))
}

export function maskHash(hash, head = 8) {
  if (!hash) return '—'
  return hash.length > head + 4 ? `${hash.slice(0, head)}…` : hash
}

export function shortId(value) {
  if (!value) return '—'
  return String(value).replace(/^[a-z]+_/, '').slice(0, 8)
}

export function errorDetailText(error) {
  const detail = error?.detail
  if (!detail) return ''
  if (detail.mismatch) {
    const item = detail.mismatch
    return `第 ${item.column_index} 列期望 ${item.expected ?? '—'}，实际 ${item.actual ?? '无'}`
  }
  if (Array.isArray(detail.invalid_rows) && detail.invalid_rows.length) {
    return `非法行号：${detail.invalid_rows.join('、')}`
  }
  if (detail.duplicate_commit_id) {
    return `重复提交：${detail.duplicate_commit_id}`
  }
  if (Array.isArray(detail.projects) && detail.projects.length) {
    return `检测到多个 project：${detail.projects.join('、')}`
  }
  return ''
}

export function humanError(error) {
  const extra = errorDetailText(error)
  if (!extra) return error?.message || '请求失败'
  return `${error.message}（${extra}）`
}

