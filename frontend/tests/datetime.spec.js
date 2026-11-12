// [AI生成] 本文件用例由 AI 编写，核心断言经人工复核。
import { describe, it, expect } from 'vitest'
import { formatTime, formatDateTime } from '../src/utils/datetime'

// 时间展示只定义一处（utils/datetime.js）：空值给占位符、非法值回退原串、有效值按本地时区格式化
describe('时间展示（utils/datetime.js）', () => {
  it('formatTime 空值 → 占位符', () => {
    expect(formatTime('')).toBe('—')
    expect(formatTime(null)).toBe('—')
    expect(formatTime(undefined)).toBe('—')
  })

  it('formatDateTime 空值 → 占位符', () => {
    expect(formatDateTime('')).toBe('—')
    expect(formatDateTime(null)).toBe('—')
  })

  it('非法时间串 → 原样返回，不抛错也不吞成占位符', () => {
    expect(formatTime('not-a-date')).toBe('not-a-date')
    expect(formatDateTime('2026-13-45')).toBe('2026-13-45')
  })

  it('formatTime 有效 ISO → 本地化字符串（非原串、非占位符）', () => {
    const out = formatTime('2026-10-25T08:31:00Z')
    expect(typeof out).toBe('string')
    expect(out).not.toBe('—')
    expect(out).not.toBe('2026-10-25T08:31:00Z')
  })

  it('formatDateTime 有效 ISO → YYYY-MM-DD HH:mm，月/日/时/分两位补零', () => {
    const iso = '2026-01-05T08:31:00Z'
    const out = formatDateTime(iso)
    // 形状断言锁死补零（单数月份/日期/小时/分钟都必须两位）
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    // 值断言：与 Date 本地字段的补零结果一致（不校验时区换算本身）
    const d = new Date(iso)
    const pad = (n) => String(n).padStart(2, '0')
    expect(out).toBe(
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
    )
  })
})
