import { describe, it, expect } from 'vitest'
import { errText, isRetryable } from '../src/utils/errors'

// 统一错误文案只定义一处（docs/frontend/pages.md 第 5 节三态口径）
describe('错误文案（utils/errors.js）', () => {
  it('40001 优先取 detail（参数名在 detail，message 是通用文案）', () => {
    expect(errText({ code: 40001, detail: 'model_name', message: '参数非法' })).toBe(
      '参数有误：model_name'
    )
  })

  it('40001 无 detail 时回退 message', () => {
    expect(errText({ code: 40001, message: '参数非法' })).toBe('参数有误：参数非法')
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

  it('其它网络错误 → 原 message 透传', () => {
    expect(errText({ message: 'Network Error' })).toBe('Network Error')
  })

  it('无任何信息 → 兜底「请求失败」', () => {
    expect(errText({})).toBe('请求失败')
    expect(errText(undefined)).toBe('请求失败')
  })

  it('isRetryable 仅 50000 为真（40100 不给重试）', () => {
    expect(isRetryable({ code: 50000 })).toBe(true)
    expect(isRetryable({ code: 40001 })).toBe(false)
    expect(isRetryable({ code: 40100 })).toBe(false)
    expect(isRetryable({})).toBe(false)
    expect(isRetryable(undefined)).toBe(false)
  })
})
