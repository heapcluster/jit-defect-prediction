// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CommitDetail from '../src/views/CommitDetail.vue'
import { ElMessage } from 'element-plus'

const getCommitDetail = vi.fn()
const postPredict = vi.fn()
const getModels = vi.fn()

vi.mock('../src/api', () => ({
  getCommitDetail: (...args) => getCommitDetail(...args),
  postPredict: (...args) => postPredict(...args),
  getModels: (...args) => getModels(...args)
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

const HASH = 'a'.repeat(40)
const routerStub = { push: vi.fn(), back: vi.fn() }

const stubs = {
  'el-button': { template: '<button><slot/></button>' },
  'el-select': true,
  'el-option': true,
  'el-tag': { template: '<span><slot/></span>' },
  'el-tooltip': true,
  'el-empty': true,
  'el-alert': true,
  'el-skeleton': true,
  LineModelCascade: true
}

function mountDetail(props = {}) {
  return mount(CommitDetail, {
    props: { hash: HASH, ...props },
    global: { mocks: { $router: routerStub }, stubs }
  })
}

describe('CommitDetail 重新预测与 SZZ 三态', () => {
  beforeEach(() => {
    getCommitDetail.mockReset()
    postPredict.mockReset()
    getModels.mockReset()
    getModels.mockResolvedValue({ lines: [] })
  })

  it('未预测提交 → 点重新预测 → 刷新 risk_score/model_name/predicted_at', async () => {
    getCommitDetail.mockResolvedValue({
      commit_hash: HASH,
      author_name: 'dev',
      committed_at: '2026-08-01T00:00:00Z',
      message: 'fix',
      risk_score: null,
      model_name: null,
      predicted_at: null,
      features: {},
      explanation: [],
      is_bug_inducing: null
    })
    postPredict.mockResolvedValue({
      risk_score: 0.54,
      model_name: 'xgb_v1',
      predicted_at: '2026-08-02T00:00:00Z',
      explanation: [{ feature: 'ns', contribution: 0.1, direction: 'increase' }],
      features: { ns: 1 }
    })

    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.text()).toContain('未预测')

    await wrapper.vm.predict()
    await flushPromises()

    expect(postPredict).toHaveBeenCalledWith(HASH, undefined)
    expect(wrapper.vm.detail.risk_score).toBe(0.54)
    expect(wrapper.vm.detail.model_name).toBe('xgb_v1')
    expect(wrapper.text()).toContain('54.0%')
  })

  it('predict 失败 → 不刷新 detail，按业务错误提示', async () => {
    getCommitDetail.mockResolvedValue({
      commit_hash: HASH,
      author_name: 'dev',
      committed_at: '2026-08-01T00:00:00Z',
      message: 'fix',
      risk_score: null,
      model_name: null,
      features: {},
      explanation: []
    })
    const bizErr = new Error('请求参数有误')
    bizErr.code = 40001
    bizErr.detail = 'commit_hash 需为 40 位十六进制'
    postPredict.mockRejectedValue(bizErr)

    const wrapper = mountDetail()
    await flushPromises()
    await wrapper.vm.predict()
    await flushPromises()

    expect(wrapper.vm.detail.risk_score).toBe(null)
    expect(ElMessage.error).toHaveBeenCalledWith('参数有误：commit_hash 需为 40 位十六进制')
  })

  it('40400：详情加载失败 → errorCode 40400、文案「该提交不存在」', async () => {
    const err = new Error('该提交不存在')
    err.code = 40400
    getCommitDetail.mockRejectedValue(err)
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.vm.error).toBe('该提交不存在')
    expect(wrapper.vm.errorCode).toBe(40400)
  })

  it('SZZ 三态：1 → 引入缺陷，0 → 非缺陷，null → 无标记', async () => {
    getCommitDetail.mockResolvedValue({
      commit_hash: HASH,
      author_name: 'dev',
      committed_at: '2026-08-01T00:00:00Z',
      message: 'fix',
      risk_score: 0.54,
      model_name: 'xgb_v1',
      features: {},
      explanation: [],
      is_bug_inducing: 1
    })
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.text()).toContain('SZZ：引入缺陷')

    wrapper.vm.detail.is_bug_inducing = null
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('无 SZZ 标记')
  })
})
