// 风险等级口径（docs 各页面「风险标签」；只定义这一处）。
// 阈值**是常量**（utils/thresholds.js），与后端 .env 的 HIGH_RISK_THRESHOLD / MID_RISK_THRESHOLD
// 同值；runtime_setting 与 /api/config 已下线，高/中/低由前端按 score 判定。

import { thresholds } from './thresholds'

const MUTED = '#9aa1ab'
const DANGER = '#d9484a'
const WARNING = '#d98a2b'
const SAFE = '#4e9b68'

export function riskColor(score, t = thresholds) {
  if (score == null) return MUTED
  if (score >= t.high) return DANGER
  if (score >= t.mid) return WARNING
  return SAFE
}

export function riskTag(score, t = thresholds) {
  if (score == null) return 'info'
  if (score >= t.high) return 'danger'
  if (score >= t.mid) return 'warning'
  return 'success'
}

export function riskLabel(score, t = thresholds) {
  if (score == null) return '未预测'
  if (score >= t.high) return '高风险'
  if (score >= t.mid) return '中等风险'
  return '常规'
}

// 后端返回的 level 是单字（高/中/低）；缺省时按当前阈值推导
export function riskLevel(score, t = thresholds) {
  if (score == null) return null
  if (score >= t.high) return '高'
  if (score >= t.mid) return '中'
  return '低'
}
