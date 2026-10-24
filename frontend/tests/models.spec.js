import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MODELS } from '../src/utils/models'

// 交付模型清单一致性：前端下拉与数据线 feature_order.txt 的 [models] 段必须一致，
// 否则加交付模型时前端会静默少一项
describe('交付模型清单一致性', () => {
  it('前端 MODELS 与 feature_order.txt [models] 段一致', () => {
    const p = resolve(process.cwd(), '../data_model/pipelines/expert/models/feature_order.txt')
    const txt = readFileSync(p, 'utf-8')
    // 取 [models] 段（到下一个 [ 段之前）
    const section = txt.split('[models]')[1].split('[')[0]
    const names = section
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.includes('.pkl'))
      .map((l) => l.split('\t')[0].replace('.pkl', ''))
    expect(MODELS).toEqual(names)
    expect(MODELS.length).toBeGreaterThan(0)
  })
})
