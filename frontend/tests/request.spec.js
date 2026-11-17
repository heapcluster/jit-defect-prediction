// === AI 辅助说明 ===
// 本文件共 6 条测试用例
// [AI生成]：0 条
// [AI生成-人工修改]：0 条
// [手写]：6 条（核心业务断言由人工编写）
// 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
// 提示词见：docs/test/unit_test/prompts/README.md

import { AxiosError } from 'axios'
import { describe, expect, it } from 'vitest'

import request from '../src/api/request'

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
