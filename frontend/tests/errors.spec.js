// === AI 辅助说明 ===
// 本文件共 9 条测试用例
// [AI生成]：9 条（经人工审核修改后采纳）
// [AI生成-人工修改]：0 条
// [手写]：0 条
// 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
// 提示词见：docs/test/unit_test/prompts/README.md

import { describe, it, expect } from 'vitest'
import { errText, isRetryable } from '../src/utils/errors'

// 统一错误文案只定义一处（docs/frontend/pages.md 第 5 节三态口径）
describe('错误文案（utils/errors.js）', () => {
  it('40001 统一提示用户检查输入', () => {
    expect(errText({ code: 40001, detail: 'model_name', message: '参数非法' })).toBe(
      '填写有误，请检查输入'
    )
    expect(errText({ code: 40001, message: '参数非法' })).toBe('填写有误，请检查输入')
  })

  it.each([
    [40100, '登录已失效，请重新登录'],
    [40400, '该提交不存在'],
    [50000, '服务异常，请稍后重试']
  ])('业务错误码 %i → 固定人话', (code, expected) => {
    expect(errText({ code })).toBe(expected)
  })

  it('超时（ECONNABORTED 或 message 含 timeout）→ 超时文案', () => {
    expect(errText({ code: 'ECONNABORTED', message: 'timeout of 10000ms exceeded' })).toBe(
      '请求超时，请稍后重试'
    )
    expect(errText({ message: 'Timeout of 3000ms exceeded' })).toBe('请求超时，请稍后重试')
  })

  it('其它网络错误 → 统一兜底文案', () => {
    expect(errText({ message: 'Network Error' })).toBe('请求失败，请稍后重试')
  })

  it('无任何信息 → 兜底「请求失败」', () => {
    expect(errText({})).toBe('请求失败，请稍后重试')
    expect(errText(undefined)).toBe('请求失败，请稍后重试')
  })

  it('isRetryable 仅 50000 为真（40100 不给重试）', () => {
    expect(isRetryable({ code: 50000 })).toBe(true)
    expect(isRetryable({ code: 40001 })).toBe(false)
    expect(isRetryable({ code: 40100 })).toBe(false)
    expect(isRetryable({})).toBe(false)
    expect(isRetryable(undefined)).toBe(false)
  })
})
