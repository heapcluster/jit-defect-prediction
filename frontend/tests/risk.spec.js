import { describe, it, expect } from 'vitest'
import { riskColor, riskTag, riskLabel } from '../src/utils/risk'

// 闭环 D-10：高风险阈值固定 0.5（中等 0.3），前端着色/标签/文案三处口径一致
describe('风险阈值（D-10 口径，docs/frontend/pages.md 第 5 节）', () => {
  it('risk_score >= 0.5 → 高风险（红 / danger）', () => {
    expect(riskLabel(0.5)).toBe('高风险')
    expect(riskColor(0.5)).toBe('#d9484a')
    expect(riskTag(0.5)).toBe('danger')
  })

  it('risk_score >= 0.3 → 中等风险（黄 / warning）', () => {
    expect(riskLabel(0.3)).toBe('中等风险')
    expect(riskColor(0.3)).toBe('#d98a2b')
    expect(riskTag(0.3)).toBe('warning')
  })

  it('其余 → 常规（绿 / success）', () => {
    expect(riskLabel(0.29)).toBe('常规')
    expect(riskColor(0.29)).toBe('#4e9b68')
    expect(riskTag(0.29)).toBe('success')
  })

  it('边界值归入上一档：0.5 是高不是中，0.3 是中不是常规', () => {
    expect(riskLabel(0.5)).toBe('高风险')
    expect(riskLabel(0.3)).toBe('中等风险')
    expect(riskLabel(0.2999)).toBe('常规')
  })
})
