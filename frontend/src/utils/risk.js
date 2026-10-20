// 风险阈值（docs/frontend/pages.md 第 5 节，只定义这一处；D-10 口径）
// 阈值固定 0.5（高风险）/ 0.3（中等），不开放参数；与后端 config.HIGH_RISK_THRESHOLD 一致

export function riskColor(score) {
  if (score >= 0.5) return '#d9484a'
  if (score >= 0.3) return '#d98a2b'
  return '#4e9b68'
}

export function riskTag(score) {
  if (score >= 0.5) return 'danger'
  if (score >= 0.3) return 'warning'
  return 'success'
}

export function riskLabel(score) {
  if (score >= 0.5) return '高风险'
  if (score >= 0.3) return '中等风险'
  return '常规'
}
