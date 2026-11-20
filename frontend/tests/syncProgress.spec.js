// === AI 辅助说明 ===
// 本文件共 6 条测试用例
// [AI生成]：0 条
// [AI生成-人工修改]：6 条（AI 生成骨架，人工补充核心断言）
// [手写]：0 条
// 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
// 提示词见：docs/test/unit_test/prompts/README.md

import { afterEach, describe, expect, it, vi } from 'vitest'

import { formatSyncMessage } from '../src/utils/syncProgress'

afterEach(() => {
  vi.useRealTimers()
})

describe('formatSyncMessage', () => {
  it('空闲不显示文案', () => {
    expect(formatSyncMessage({ running: false, phase: null })).toBe('')
  })

  it('拉取源仓库阶段', () => {
    expect(formatSyncMessage({ running: true, phase: 'fetch' })).toBe('正在拉取源仓库…')
  })

  it('计算待补提交阶段', () => {
    expect(formatSyncMessage({ running: true, phase: 'plan' })).toBe('正在计算待补提交…')
  })

  it('批量抽取特征阶段带条数', () => {
    expect(formatSyncMessage({ running: true, phase: 'extract', total: 10 })).toBe(
      '正在批量抽取特征（10 条）…'
    )
  })

  it('逐条预测阶段显示 done/total', () => {
    expect(
      formatSyncMessage({ running: true, phase: 'predict', done: 3, total: 10 })
    ).toBe('同步中 3/10')
  })

  it('带已耗时，避免长时间无进度', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-16T12:05:05Z'))
    expect(
      formatSyncMessage({
        running: true,
        phase: 'fetch',
        started_at: '2026-11-16T12:04:00Z'
      })
    ).toBe('正在拉取源仓库…（已 1 分 5 秒）')
  })
})
