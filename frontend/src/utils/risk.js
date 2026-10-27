// 风险等级口径（docs/frontend/pages.md 第 5 节，只定义这一处；D-10 口径）
// 阈值**从后端运行时配置读**（utils/thresholds.js → /api/config），前端不再硬编码：
// 质量看板把 high 改成 0.4 后，这里的分级必须同步变化，否则同一分数在不同页面
// 会呈现不同等级。默认参数只是首屏兜底值（与 backend/app/config.py 一致：0.5 / 0.2）。

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
