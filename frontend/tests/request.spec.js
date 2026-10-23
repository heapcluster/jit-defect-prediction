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
