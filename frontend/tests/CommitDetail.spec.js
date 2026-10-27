// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CommitDetail from '../src/views/CommitDetail.vue'
import { ElMessage } from 'element-plus'

const getCommitDetail = vi.fn()
const postPredict = vi.fn()
const getConfig = vi.fn()

// mock api：postPredict 是本次新增入口，必须走真实调用路径验证
vi.mock('../src/api', () => ({
  getCommitDetail: (...args) => getCommitDetail(...args),
  postPredict: (...args) => postPredict(...args),
  // 详情页 onMounted 会拉运行时阈值（utils/thresholds），少了这个导出会同步抛错
  getConfig: (...args) => getConfig(...args)
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

const HASH = 'a'.repeat(40)
const routerStub = { push: vi.fn(), back: vi.fn() }

describe('CommitDetail 重新预测（POST /api/predict 入口）', () => {
  beforeEach(() => {
    getCommitDetail.mockReset()
    postPredict.mockReset()
    getConfig.mockReset()
    getConfig.mockResolvedValue({ high_risk_threshold: 0.5, mid_risk_threshold: 0.2 })
  })

  it('未预测提交 → 点重新预测 → 刷新 risk_score/model_name/explanation', async () => {
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
    postPredict.mockResolvedValue({
      risk_score: 0.54,
      model_name: 'xgb_v1',
      explanation: [{ feature: 'ns', contribution: 0.1, direction: 'increase' }],
      features: { ns: 1 }
    })

    const wrapper = mount(CommitDetail, {
      props: { hash: HASH },
      global: {
        mocks: { $router: routerStub },
        stubs: {
          'el-button': { template: '<button><slot/></button>' },
          'el-select': true,
          'el-option': true,
          'el-tag': { template: '<span><slot/></span>' },
          'el-descriptions': { template: '<div><slot/></div>' },
          'el-descriptions-item': { template: '<div><slot/></div>' },
          'el-empty': true,
          'el-alert': true
        }
      }
    })

    await flushPromises()
    // 初始：未预测 → 只显示一次「未预测」（RiskTag 兜底文案）
    expect(wrapper.text()).toContain('未预测')

    // 触发重新预测
    await wrapper.vm.predict()
    await flushPromises()

    // postPredict 被真实调用（默认模型，model_name undefined）
    expect(postPredict).toHaveBeenCalledWith(HASH, undefined)
    // detail 刷新为预测结果
    expect(wrapper.vm.detail.risk_score).toBe(0.54)
    expect(wrapper.vm.detail.model_name).toBe('xgb_v1')
    expect(wrapper.text()).toContain('54.0%')
  })

  it('predict 非 2xx 失败 → 不刷新 detail，按业务错误提示', async () => {
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
    // 模拟后端 40001：带业务 code 的错误
    const bizErr = new Error('请求参数有误')
    bizErr.code = 40001
    bizErr.detail = 'commit_hash 需为 40 位十六进制'
    postPredict.mockRejectedValue(bizErr)

    const wrapper = mount(CommitDetail, {
      props: { hash: HASH },
      global: {
        mocks: { $router: routerStub },
        stubs: {
          'el-button': { template: '<button><slot/></button>' },
          'el-select': true,
          'el-option': true,
          'el-tag': { template: '<span><slot/></span>' },
          'el-descriptions': { template: '<div><slot/></div>' },
          'el-descriptions-item': { template: '<div><slot/></div>' },
          'el-empty': true,
          'el-alert': true
        }
      }
    })

    await flushPromises()
    await wrapper.vm.predict()
    await flushPromises()

    // 失败后 detail 仍是未预测（不被污染）
    expect(wrapper.vm.detail.risk_score).toBe(null)
    // 断言错误提示文案（防提示语回归）
    expect(ElMessage.error).toHaveBeenCalledWith('参数有误：commit_hash 需为 40 位十六进制')
  })

  it('40400：详情加载失败 → errorCode 40400、文案「该提交不存在」', async () => {
    const err = new Error('该提交不存在')
    err.code = 40400
    getCommitDetail.mockRejectedValue(err)
    const wrapper = mount(CommitDetail, {
      props: { hash: HASH },
      global: {
        mocks: { $router: routerStub },
        stubs: { 'el-button': true, 'el-select': true, 'el-option': true, 'el-tag': true, 'el-descriptions': true, 'el-descriptions-item': true, 'el-empty': true, 'el-alert': true }
      }
    })
    await flushPromises()
    expect(wrapper.vm.error).toBe('该提交不存在')
    expect(wrapper.vm.errorCode).toBe(40400)
  })

  it('解释为空：有分数但 explanation 空数组 → 显示「该模型未提供特征解释」', async () => {
    getCommitDetail.mockResolvedValue({
      commit_hash: HASH,
      author_name: 'dev',
      committed_at: '2026-08-01T00:00:00Z',
      message: 'fix',
      risk_score: 0.54,
      model_name: 'xgb_v1',
      features: {},
      explanation: []
    })
    const wrapper = mount(CommitDetail, {
      props: { hash: HASH },
      global: {
        mocks: { $router: routerStub },
        stubs: {
          'el-button': true,
          'el-select': true,
          'el-option': true,
          'el-tag': { template: '<span><slot/></span>' },
          'el-descriptions': true,
          'el-descriptions-item': true,
          'el-empty': { template: '<div><slot/><span>{{description}}</span></div>', props: ['description'] },
          'el-alert': true
        }
      }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('该模型未提供特征解释')
  })
})
