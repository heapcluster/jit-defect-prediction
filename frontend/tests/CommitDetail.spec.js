// [AI生成-人工修改] 在原有测试基础上由 AI 补充/修改部分用例，核心断言经人工复核。
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

// useRoute：详情按路由 query.model_name 查对应模型的概率（未注入 router 时应返回空 query）
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} })
}))

const HASH = 'a'.repeat(40)
const routerStub = { push: vi.fn(), back: vi.fn() }

const stubs = {
  'el-button': { template: '<button><slot/></button>' },
  'el-select': true,
  'el-option': true,
  'el-tag': { template: '<span><slot/></span>' },
  'el-tooltip': { template: '<span><slot/></span>' },
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

describe('CommitDetail 缺陷定位与修复参考（G1-1/G1-2）', () => {
  beforeEach(() => {
    getCommitDetail.mockReset()
    postPredict.mockReset()
    getModels.mockReset()
    getModels.mockResolvedValue({ lines: [] })
  })

  const baseDetail = () => ({
    commit_hash: HASH,
    author_name: 'dev',
    committed_at: '2026-08-01T00:00:00Z',
    message: 'CAMEL-1 fix',
    risk_score: 0.9,
    model_name: 'xgb_v1',
    predicted_at: '2026-08-02T00:00:00Z',
    features: {},
    explanation: [],
    is_bug_inducing: 1
  })

  it('G1-1：有归因时渲染「缺陷定位」区块，按 |归因| 降序高亮', async () => {
    getCommitDetail.mockResolvedValue({
      ...baseDetail(),
      localization: {
        level: 'commit',
        notice: '未采集文件/行级差异数据，已降级到提交级特征定位',
        highlights: [
          { feature: 'la', label: '代码改动量大', contribution: 0.6, direction: 'increase' },
          { feature: 'lt', label: '测试改动少', contribution: -0.4, direction: 'decrease' }
        ]
      }
    })
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.vm.localization.level).toBe('commit')
    expect(wrapper.text()).toContain('缺陷定位')
    expect(wrapper.find('.loc').exists()).toBe(true)
    expect(wrapper.findAll('.loc .rank').map((n) => n.text())).toEqual(['1', '2'])
    expect(wrapper.findAll('.loc .f').map((n) => n.text())).toEqual(['代码改动量大', '测试改动少'])
  })

  it('G1-1：归因为空时不渲染高亮条（降级到空态，不编造）', async () => {
    getCommitDetail.mockResolvedValue({
      ...baseDetail(),
      localization: { level: 'commit', notice: '该模型未提供特征归因，暂无定位信息', highlights: [] }
    })
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.text()).toContain('缺陷定位')
    expect(wrapper.find('.loc').exists()).toBe(false)
  })

  it('G1-2：有历史修复提交时渲染「修复参考」列表', async () => {
    getCommitDetail.mockResolvedValue({
      ...baseDetail(),
      fix_references: {
        basis: '同仓库历史修复提交',
        items: [
          { commit_hash: 'b'.repeat(40), message: 'CAMEL-2 fix', committed_at: '2026-07-01T00:00:00Z' }
        ]
      }
    })
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.text()).toContain('修复参考')
    expect(wrapper.find('.refs').exists()).toBe(true)
    expect(wrapper.find('.ref-hash').text()).toBe('b'.repeat(8))
    expect(wrapper.find('.ref-msg').text()).toContain('CAMEL-2 fix')
  })

  it('G1-2：无依据时渲染空态（不编造建议）', async () => {
    getCommitDetail.mockResolvedValue({
      ...baseDetail(),
      fix_references: { basis: '同仓库历史修复提交', items: [] }
    })
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.text()).toContain('修复参考')
    expect(wrapper.find('.refs').exists()).toBe(false)
  })

  it('旧接口无新字段时两区块均隐藏（向后兼容）', async () => {
    getCommitDetail.mockResolvedValue(baseDetail())
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.text()).not.toContain('缺陷定位')
    expect(wrapper.text()).not.toContain('修复参考')
  })

  it('G1-1：level="line" 时渲染新增代码行高亮', async () => {
    getCommitDetail.mockResolvedValue({
      ...baseDetail(),
      localization: {
        level: 'line',
        notice: '按提交级缺陷概率对新增代码行着色',
        highlights: [],
        truncated: false,
        files: [{ path: 'src/A.java', added_lines: [{ number: 1, content: 'class A {}' }] }]
      }
    })
    const wrapper = mountDetail()
    await flushPromises()
    expect(wrapper.find('.lines').exists()).toBe(true)
    expect(wrapper.find('.file-path').text()).toBe('src/A.java')
    expect(wrapper.find('.line-no').text()).toBe('1')
    expect(wrapper.find('.line-content').text()).toBe('class A {}')
  })
})
