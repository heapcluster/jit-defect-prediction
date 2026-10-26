// 时间展示：**只定义一处**。后端序列化的 naive UTC 统一按浏览器本地时区展示
// （契约：库内存 naive UTC，序列化补 Z；前端一律转本地时区，不直接显示 ISO 原串）。
//
// 2026-10-25 修复要点：此前 RiskList / CommitDetail 各写一份 toLocaleString，
// 而 PrList / PrDetail 直接渲染 ISO 原串（`2026-10-25T08:31:00Z`），口径不一致。

// 完整时间：2026-10-25 16:31:00
export function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString('zh-CN', { hour12: false })
}

// 精确到分：2026-10-25 16:31
export function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
