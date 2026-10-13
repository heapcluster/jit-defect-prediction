import { describe, expect, it } from 'vitest'
import {
  DEFAULT_PAGE_SIZE,
  FEATURE_GROUPS,
  MAX_EXPLANATION,
  MODEL_OPTIONS,
  RISK_HIGH,
  RISK_MID
} from '../constants'
import { formatFeature, formatPct, formatTime, riskClass, shortHash } from '../utils/format'

// 前端单测（T-FE-01/02/03）：只覆盖**纯口径函数**，不依赖 DOM 与 element-plus。
// 口径来源：docs/frontend/pages.md、docs/model/feature-columns.md、docs/backend/api-spec.md。
// 跑法：cd frontend && npm run test:unit

describe('风险阈值与百分比（T-FE-01，pages.md §5 一处定义）', () => {
  it('≥0.5 判高', () => {
    expect(riskClass(0.5)).toBe('high')
    expect(riskClass(0.83)).toBe('high')
  })

  it('≥0.3 且 <0.5 判中', () => {
    expect(riskClass(0.3)).toBe('mid')
    expect(riskClass(0.49)).toBe('mid')
  })

  it('其余常规；null/undefined 不是数值，不得当 0 处理', () => {
    expect(riskClass(0.29)).toBe('low')
    expect(riskClass(null)).toBe('none')
    expect(riskClass(undefined)).toBe('none')
  })

  it('概率 0~1 转百分比保留一位', () => {
    expect(formatPct(0.8345)).toBe('83.5%')
    expect(formatPct(0)).toBe('0.0%')
    expect(formatPct(null)).toBe('—')
  })

  it('阈值常量与文档一致', () => {
    expect(RISK_HIGH).toBe(0.5)
    expect(RISK_MID).toBe(0.3)
  })
})

describe('模型下拉清单（T-FE-02，pages.md §6 静态清单）', () => {
  it('共 8 个，覆盖 2 类', () => {
    expect(MODEL_OPTIONS).toHaveLength(8)
    const classic = ['lr_v1', 'rf_v1', 'xgb_v1', 'nb_v1', 'dt_v1', 'knn_v1']
    const neural = ['mlp_v1', 'mlp_deep_v1']
    classic.forEach((m) => expect(MODEL_OPTIONS).toContain(m))
    neural.forEach((m) => expect(MODEL_OPTIONS).toContain(m))
  })

  it('无重复项', () => {
    expect(new Set(MODEL_OPTIONS).size).toBe(MODEL_OPTIONS.length)
  })
})

describe('特征五维度分组（T-FE-02，feature-columns.md 第三节）', () => {
  it('恰好 14 项、无重复、分组齐', () => {
    const keys = FEATURE_GROUPS.flatMap((g) => g.keys)
    expect(keys).toHaveLength(14)
    expect(new Set(keys).size).toBe(14)
    expect(FEATURE_GROUPS.map((g) => g.name)).toEqual([
      '代码分布',
      '规模',
      '目的',
      '历史',
      '开发者经验'
    ])
  })

  it('解释条上限为 8（pages.md §3）', () => {
    expect(MAX_EXPLANATION).toBe(8)
  })
})

describe('字段展示（T-FE-03，缺失要可见）', () => {
  it('哈希显前 8 位', () => {
    expect(shortHash('a'.repeat(40))).toBe('a'.repeat(8))
    expect(shortHash('short')).toBe('short')
    expect(shortHash(null)).toBe('—')
  })

  it('特征值 0 照常显示，缺失显示 —', () => {
    expect(formatFeature(0)).toBe('0')
    expect(formatFeature(-8.7612)).toBe('-8.7612')
    expect(formatFeature(null)).toBe('—')
  })

  it('ISO 8601 转本地时间；非法值原样返回不静默吞掉', () => {
    expect(formatTime('2026-09-16T08:30:00Z')).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    expect(formatTime('not-a-date')).toBe('not-a-date')
    expect(formatTime(null)).toBe('—')
  })
})

describe('分页口径（api-spec.md §一）', () => {
  it('默认 20', () => {
    expect(DEFAULT_PAGE_SIZE).toBe(20)
  })
})
