import { beforeEach, describe, expect, it, vi } from 'vitest'

import request, { SYNC_TIMEOUT } from '../src/api/request'
import {
  getCommitDetail,
  getCommits,
  getPrDetail,
  getPrs,
  getTrends,
  postPredict,
  postSync,
  postSyncPrs
} from '../src/api/index'

// api 层的路径 / 方法 / 参数是前端与后端契约的映射点。
// 契约漂移（后端改了路径或参数名）在这里第一时间炸，而不是等到页面白屏。
// 2026-10-25 补：此前 api/index.js 无任何测试，是最便宜也最有效的一道闸。

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('api 层与后端契约的映射', () => {
  it('GET /commits 带分页与筛选参数', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({ items: [] })
    await getCommits({ page: 2, size: 20, model_name: 'xgb_v1', min_risk: 0.3 })
    expect(spy).toHaveBeenCalledTimes(1)
    const [url, config] = spy.mock.calls[0]
    expect(url).toBe('/commits')
    expect(config.params).toEqual({ page: 2, size: 20, model_name: 'xgb_v1', min_risk: 0.3 })
  })

  it('GET /commits/{hash} 把 hash 拼进路径', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({})
    await getCommitDetail('abc123')
    expect(spy.mock.calls[0][0]).toBe('/commits/abc123')
  })

  it('GET /trends 带粒度与时间范围', async () => {
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

  it('GET /prs 与 GET /prs/{number} 的路径正确', async () => {
    const spy = vi.spyOn(request, 'get').mockResolvedValue({})
    await getPrs({ limit: 30 })
    expect(spy.mock.calls[0][0]).toBe('/prs')
    expect(spy.mock.calls[0][1].params.limit).toBe(30)
    await getPrDetail(28147)
    expect(spy.mock.calls[1][0]).toBe('/prs/28147')
  })

  it('同步类端点走长超时（默认 10s 必然超时）', async () => {
    const spy = vi.spyOn(request, 'post').mockResolvedValue({})
    await postSyncPrs(30)
    const [url, , config] = spy.mock.calls[0]
    expect(url).toBe('/sync-prs')
    expect(config.params.limit).toBe(30)
    expect(config.timeout).toBe(SYNC_TIMEOUT)

    await postSync(100)
    const [url2, , config2] = spy.mock.calls[1]
    expect(url2).toBe('/sync')
    expect(config2.params.limit).toBe(100)
    expect(config2.timeout).toBe(SYNC_TIMEOUT)
  })
})
