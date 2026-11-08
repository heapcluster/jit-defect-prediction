import { describe, it, expect } from 'vitest'
import { riskColor, riskTag, riskLabel, riskLevel } from '../src/utils/risk'

// 闭环 D-10：高风险阈值固定 0.5、中等 0.2（与后端 config 的 HIGH/MID_RISK_THRESHOLD 默认值一致）
describe('风险阈值（D-10 口径，docs/web_page/README.md）', () => {
  it('risk_score >= 0.5 → 高风险（红 / danger）', () => {
    expect(riskLabel(0.5)).toBe('高风险')
    expect(riskColor(0.5)).toBe('#d9484a')
    expect(riskTag(0.5)).toBe('danger')
  })

  it('risk_score >= 0.2 → 中等风险（黄 / warning）', () => {
    expect(riskLabel(0.2)).toBe('中等风险')
    expect(riskColor(0.2)).toBe('#d98a2b')
    expect(riskTag(0.2)).toBe('warning')
  })

  it('其余 → 常规（绿 / success）', () => {
    expect(riskLabel(0.19)).toBe('常规')
    expect(riskColor(0.19)).toBe('#4e9b68')
    expect(riskTag(0.19)).toBe('success')
  })

  it('边界值归入上一档：0.5 是高不是中，0.2 是中不是常规', () => {
    expect(riskLabel(0.5)).toBe('高风险')
    expect(riskLabel(0.2)).toBe('中等风险')
    expect(riskLabel(0.1999)).toBe('常规')
  })

  it('riskLevel 返回单字（后端 level 口径：高/中/低）', () => {
    expect(riskLevel(0.5)).toBe('高')
    expect(riskLevel(0.2)).toBe('中')
    expect(riskLevel(0.19)).toBe('低')
  })

  it('score 为空 → 未预测态（灰 / info / 未预测 / null）', () => {
    expect(riskLabel(null)).toBe('未预测')
    expect(riskLabel(undefined)).toBe('未预测')
    expect(riskColor(null)).toBe('#9aa1ab')
    expect(riskTag(null)).toBe('info')
    expect(riskLevel(null)).toBe(null)
  })

  it('可传入自定义阈值（与默认常量同形的配置注入）', () => {
    const t = { high: 0.8, mid: 0.5 }
    expect(riskLabel(0.7, t)).toBe('中等风险')
    expect(riskLabel(0.3, t)).toBe('常规')
    expect(riskColor(0.9, t)).toBe('#d9484a')
    expect(riskTag(0.9, t)).toBe('danger')
    expect(riskLevel(0.4, t)).toBe('低')
  })
})
