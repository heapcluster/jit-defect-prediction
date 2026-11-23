// === AI 辅助说明 ===
// 本文件共 3 条测试用例
// [AI生成]：0 条
// [AI生成-人工修改]：3 条（AI 生成骨架，人工补充核心断言）
// [手写]：0 条
// 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
// 提示词见：docs/test/unit_test/prompts/README.md

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { FEATURE_FIELDS, featureLabel } from '../src/utils/features'

// T-FE-02 组件级字段映射：前端 14 项特征字段与契约/交付清单逐字、逐序一致
describe('14 项特征字段映射（T-FE-02）', () => {
  it('FEATURE_FIELDS 恰为 14 项，且顺序与 feature_order.txt [feature_order] 段一致', () => {
    const p = resolve(process.cwd(), '../data_model/pipelines/expert/models/feature_order.txt')
    const txt = readFileSync(p, 'utf-8')
    const section = txt.split('[feature_order]')[1].split('[')[0]
    const fields = section
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => /^\d+\.\s/.test(l))
      .map((l) => l.replace(/^\d+\.\s*/, '').trim())
    expect(FEATURE_FIELDS).toEqual(fields)
    expect(FEATURE_FIELDS.length).toBe(14)
  })

  it('featureLabel 已知特征 → 中文名', () => {
    expect(featureLabel('ns')).toBe('变更子系统多')
    expect(featureLabel('sexp')).toBe('作者子系统经验')
  })

  it('featureLabel 未知特征 → 回退原名，不报错不返回空', () => {
    expect(featureLabel('not_a_feature')).toBe('not_a_feature')
    expect(featureLabel('')).toBe('')
  })
})
