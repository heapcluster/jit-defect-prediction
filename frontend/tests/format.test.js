import { describe, expect, it } from 'vitest'
import {
  errorDetailText,
  formatNumber,
  formatPercent,
  formatTime,
  humanError,
  maskHash,
  shortId,
  statusType
} from '../src/utils/format'

describe('format helpers', () => {
  it('formats percentages and keeps missing values visible', () => {
    expect(formatPercent(0.8234)).toBe('82.34%')
    expect(formatPercent(null)).toBe('—')
    expect(formatPercent('')).toBe('—')
  })

  it('formats numbers and truncates long hashes', () => {
    expect(formatNumber(1.234567, 4)).toBe('1.2346')
    expect(formatNumber(undefined)).toBe('—')
    expect(maskHash('a'.repeat(40), 8)).toBe('aaaaaaaa…')
  })

  it('shortens ids and timestamps', () => {
    expect(shortId('job_1234567890abcdef')).toBe('12345678')
    expect(shortId(null)).toBe('—')
    expect(formatTime('2026-11-28T10:20:30+08:00')).toMatch(/^2026-11-28 \d{2}:20:30$/)
    expect(formatTime('')).toBe('—')
  })

  it('maps status to element tag types', () => {
    expect(statusType('available')).toBe('success')
    expect(statusType('missing')).toBe('danger')
    expect(statusType('running')).toBe('warning')
    expect(statusType('queued')).toBe('info')
  })
})

describe('error helpers', () => {
  it('describes the first column mismatch', () => {
    const error = {
      message: '表头不符',
      detail: { mismatch: { column_index: 8, expected: 'nd', actual: 'num_dir' } }
    }
    expect(errorDetailText(error)).toBe('第 8 列期望 nd，实际 num_dir')
    expect(humanError(error)).toBe('表头不符（第 8 列期望 nd，实际 num_dir）')
  })

  it('describes invalid rows and falls back to the message', () => {
    expect(errorDetailText({ detail: { invalid_rows: [2, 5] } })).toBe('非法行号：2、5')
    expect(humanError({ message: '请求失败' })).toBe('请求失败')
  })
})
