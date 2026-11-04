import { beforeEach, describe, expect, it, vi } from 'vitest'

import request, { SYNC_TIMEOUT } from '../src/api/request'
import {
  getCommitDetail,
  getCommits,
  getFigures,
  getModels,
  getSyncStatus,
  getTrends,
  postPredict,
  postSync
} from '../src/api/index'

// api 层的路径 / 方法 / 参数是前端与后端契约的映射点。
// 契约漂移（后端改了路径或参数名）在这里第一时间炸，而不是等到页面白屏。

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('api 层与后端契约的映射', () => {
  it('GET /commits 带分页与筛选参数', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({ items: [] })
    await getCommits({ page: 2, size: 20, model_name: 'xgb_v1', with_features: '1', is_test: '1' })
    expect(spy).toHaveBeenCalledTimes(1)
    const [url, config] = spy.mock.calls[0]
    expect(url).toBe('/commits')
    expect(config.params).toEqual({
      page: 2,
      size: 20,
      model_name: 'xgb_v1',
      with_features: '1',
      is_test: '1'
    })
  })

  it('GET /commits/{hash} 把 hash 拼进路径', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({})
    await getCommitDetail('abc123')
    expect(spy.mock.calls[0][0]).toBe('/commits/abc123')
  })

  it('GET /trends 带粒度与模型', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({ series: [] })
    await getTrends({ granularity: 'week', model_name: 'xgb_v1' })
    const [url, config] = spy.mock.calls[0]
    expect(url).toBe('/trends')
    expect(config.params.granularity).toBe('week')
    expect(config.params.model_name).toBe('xgb_v1')
  })

  it('POST /predict 的请求体是 commit_hash + model_name', async () => {
    const spy = vi.spyOn(request, 'post').mockResolvedValue({})
    await postPredict('abc123', 'xgb_v1')
    const [url, body] = spy.mock.calls[0]
    expect(url).toBe('/predict')
    expect(body).toEqual({ commit_hash: 'abc123', model_name: 'xgb_v1' })
  })

  it('POST /predict 不传模型时不下发空 model_name 字段', async () => {
    const spy = vi.spyOn(request, 'post').mockResolvedValue({})
    await postPredict('abc123')
    expect(spy.mock.calls[0][1].model_name).toBeUndefined()
  })

  it('GET /models 支持按架构过滤', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({ lines: [] })
    await getModels('expert')
    expect(spy.mock.calls[0][0]).toBe('/models')
    expect(spy.mock.calls[0][1].params).toEqual({ line: 'expert' })
  })

  it('GET /figures 传 model_name', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({ figures: [] })
    await getFigures('xgb_v1')
    expect(spy.mock.calls[0][0]).toBe('/figures')
    expect(spy.mock.calls[0][1].params).toEqual({ model_name: 'xgb_v1' })
  })

  it('POST /sync 按 line / model_name / 时间区间补算并走长超时', async () => {
    const spy = vi.spyOn(request, 'post').mockResolvedValue({ accepted: true })
    await postSync({ line: 'expert', modelName: 'xgb_v1', startTime: '2026-01-01', endTime: '2026-01-31' })
    const [url, , config] = spy.mock.calls[0]
    expect(url).toBe('/sync')
    expect(config.params).toEqual({
      line: 'expert',
      model_name: 'xgb_v1',
      start_time: '2026-01-01',
      end_time: '2026-01-31'
    })
    expect(config.timeout).toBe(SYNC_TIMEOUT)
  })

  it('POST /sync 空筛选不下发空参数', async () => {
    const spy = vi.spyOn(request, 'post').mockResolvedValue({ accepted: true })
    await postSync()
    const [, , config] = spy.mock.calls[0]
    expect(config.params).toEqual({
      line: undefined,
      model_name: undefined,
      start_time: undefined,
      end_time: undefined
    })
  })

  it('GET /sync/status 取状态快照', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({ running: false })
    await getSyncStatus()
    expect(spy.mock.calls[0][0]).toBe('/sync/status')
  })
})
