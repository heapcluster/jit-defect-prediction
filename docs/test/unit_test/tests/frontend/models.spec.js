// [AI生成-人工修改] 在原有测试基础上由 AI 补充/修改部分用例，核心断言经人工复核。
import { describe, it, expect, vi } from 'vitest'
import { LINE_LABELS, LINE_ORDER, loadModelLines, loadOnlineModels } from '../src/utils/models'
import { getModels, getHealth } from '../src/api'

vi.mock('../src/api', () => ({
  getModels: vi.fn(),
  getHealth: vi.fn()
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

describe('在线模型清单（/api/health.model_names）', () => {
  it('loadOnlineModels 成功返回在线模型名集合', async () => {
    getHealth.mockResolvedValue({ model_names: ['lr_v1', 'rf_v1'] })
    const set = await loadOnlineModels(true)
    expect(set).toBeInstanceOf(Set)
    expect(set.has('lr_v1')).toBe(true)
    expect(set.has('semantic_v1')).toBe(false)
  })

  it('loadOnlineModels 失败返回 null（未知态，不误标离线）', async () => {
    getHealth.mockRejectedValue(new Error('health down'))
    expect(await loadOnlineModels(true)).toBeNull()
  })
})
