// === AI 辅助说明 ===
// 本文件共 2 条测试用例
// [AI生成]：0 条
// [AI生成-人工修改]：2 条（AI 生成骨架，人工补充核心断言）
// [手写]：0 条
// 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
// 提示词见：docs/test/unit_test/prompts/README.md

import { describe, it, expect, vi } from 'vitest'
import { LINE_LABELS, LINE_ORDER, loadModelLines } from '../src/utils/models'
import { getModels } from '../src/api'

vi.mock('../src/api', () => ({
  getModels: vi.fn()
}))

// 模型层级（架构 → 模型）唯一数据源是 GET /api/models，前端不写死清单
describe('模型层级（架构 → 模型）', () => {
  it('四个架构固定顺序 + 中文名', () => {
    expect(LINE_ORDER).toEqual(['expert', 'semantic', 'fused', 'e2e'])
    expect(LINE_LABELS.expert).toBe('专家特征')
    expect(LINE_LABELS.semantic).toBe('语义')
    expect(LINE_LABELS.fused).toBe('融合')
    expect(LINE_LABELS.e2e).toBe('端到端')
  })

  it('loadModelLines 走 GET /api/models 并缓存结果', async () => {
    getModels.mockResolvedValue({
      lines: [{ line: 'expert', label: '专家特征', models: ['lr_v1', 'rf_v1'] }]
    })
    const lines = await loadModelLines(true)
    expect(lines).toEqual([{ line: 'expert', label: '专家特征', models: ['lr_v1', 'rf_v1'] }])
    expect(getModels).toHaveBeenCalledTimes(1)

    await loadModelLines() // 命中缓存，不再发请求
    expect(getModels).toHaveBeenCalledTimes(1)
  })
})
