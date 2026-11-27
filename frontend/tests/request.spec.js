// === AI 辅助说明 ===
// 本文件共 11 条测试用例
// [AI生成]：0 条
// [AI生成-人工修改]：0 条
// [手写]：11 条（核心业务断言由人工编写）
// 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
// 提示词见：docs/test/unit_test/prompts/README.md

import { AxiosError } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import request, { fetchBinary, storageOptions } from '../src/api/request'

function rejectedHttpResponse(status, code, message) {
  return async (config) => {
    const response = {
      config,
      data: { code, message, data: null },
      headers: {},
      status,
      statusText: ''
    }
    throw new AxiosError('HTTP request failed', 'ERR_BAD_RESPONSE', config, null, response)
  }
}

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
    blob: async () => new Blob(['ok'])
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('HTTP 错误包络', () => {
  it('HTTP 200 的成功包络仍只返回 data', async () => {
    const data = { items: [] }
    await expect(request.get('/commits', {
      adapter: async (config) => ({
        config,
        data: { code: 0, message: 'ok', data },
        headers: {},
        status: 200,
        statusText: 'OK'
      })
    })).resolves.toBe(data)
  })

  it.each([
    [400, 40001, '参数非法：model_name', '请求参数有误'],
    [401, 40100, 'invalid token', '登录已失效，请重新登录'],
    [404, 40400, 'commit not found', '该提交不存在'],
    [500, 50000, 'private server path', '服务异常，请稍后重试']
  ])('HTTP %i 保留业务码 %i', async (status, code, detail, expectedMessage) => {
    await expect(request.get('/commits', {
      adapter: rejectedHttpResponse(status, code, detail)
    })).rejects.toMatchObject({ code, detail, message: expectedMessage })
  })

  it('无业务包络的网络错误仍按原错误传递', async () => {
    const networkError = new AxiosError('Network Error', 'ERR_NETWORK')
    await expect(request.get('/commits', {
      adapter: async () => { throw networkError }
    })).rejects.toBe(networkError)
  })
})

describe('二进制下载鉴权与错误归一化', () => {
  it('带 X-API-Key 请求并返回 blob', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, null))
    vi.stubGlobal('fetch', fetchMock)
    const blob = await fetchBinary('/api/predict/outputs/1/predictions.csv')
    expect(blob).toBeInstanceOf(Blob)
    expect(fetchMock).toHaveBeenCalledWith('/api/predict/outputs/1/predictions.csv', {
      headers: { 'X-API-Key': import.meta.env.VITE_API_KEY }
    })
  })

  it('401 映射为登录失效且保留业务码', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(401, { code: 40100, message: 'invalid token' })))
    await expect(fetchBinary('/api/predict/outputs/1/x.csv')).rejects.toMatchObject({
      code: 40100,
      message: '登录已失效，请重新登录'
    })
  })

  it('5xx 使用调用方指定的服务异常文案', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(500, { code: 50000, message: 'private stack' })))
    await expect(fetchBinary('/api/explain/outputs/1/x.csv', { serverError: '解释下载服务异常' })).rejects.toMatchObject({
      code: 50000,
      message: '解释下载服务异常'
    })
  })

  it('非 JSON 错误按 label 与状态码生成提示', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => { throw new Error('not json') }
    }))
    await expect(fetchBinary('/static/figures/a.png', { label: '图片加载', includeStatus: true })).rejects.toMatchObject({
      message: '图片加载失败：404'
    })
  })
})

describe('storage 响应选项', () => {
  it('把 40001 的结构化 detail 转成通用 message 字段', () => {
    const transform = storageOptions.transformResponse.at(-1)
    const result = transform({ code: 40001, error: { detail: '字段 xxx 非法' }, message: '请求参数有误' })
    expect(result.message).toBe('字段 xxx 非法')
  })
})
