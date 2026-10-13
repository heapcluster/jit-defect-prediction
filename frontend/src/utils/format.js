// 纯格式化函数（不依赖 element-plus，可在 node 环境直接单测）。
// 口径见 docs/frontend/pages.md §1–§5、docs/model/feature-columns.md 第三节。
// 阈值从 constants.js 引入，**不在此处硬编码**（pages.md §5：只定义一处）。

import { RISK_HIGH, RISK_MID } from '../constants'

// 概率 0~1 → 百分比字符串，保留一位（pages.md §2：前端 ×100 转百分比）
export function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(Number(value) * 100).toFixed(1)}%`
}

// 风险等级 → CSS class（阈值见 constants.js：≥RISK_HIGH 高 / ≥RISK_MID 中 / 其余常规）
export function riskClass(value) {
  if (value === null || value === undefined) return 'none'
  if (value >= RISK_HIGH) return 'high'
  if (value >= RISK_MID) return 'mid'
  return 'low'
}

// 40 位哈希 → 显前 8 位（pages.md §2）
export function shortHash(hash) {
  if (!hash) return '—'
  return hash.length > 8 ? hash.slice(0, 8) : hash
}

// ISO 8601 带时区 → 本地时间（pages.md §1.3）
export function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 特征值展示：0 照常显示，缺失显示「—」（pages.md §3：缺失要可见）
export function formatFeature(value) {
  if (value === null || value === undefined) return '—'
  return String(value)
}
