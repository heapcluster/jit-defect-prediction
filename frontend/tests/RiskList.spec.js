// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RiskList from '../src/views/RiskList.vue'

const getCommits = vi.fn()
// 页面首屏会同时拉「已预测覆盖」与「服务状态」，这两个旁路请求不该影响三态断言
const getCommitsCoverage = vi.fn()
const getHealth = vi.fn()
const postSync = vi.fn()
const postSyncCatchup = vi.fn()
const subscribeSyncProgress = vi.fn()

vi.mock('../src/api', () => ({
  getCommits: (...args) => getCommits(...args),
  getCommitsCoverage: (...args) => getCommitsCoverage(...args),
  getHealth: (...args) => getHealth(...args),
  postSync: (...args) => postSync(...args),
  postSyncCatchup: (...args) => postSyncCatchup(...args),
  subscribeSyncProgress: (...args) => subscribeSyncProgress(...args)
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

// routeQuery 供各用例注入路由参数（useRoute 的 mock 读取它）
let routeQuery = {}

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: routeQuery })
}))

const stubs = {
  'el-form': { template: '<div><slot/></div>' },
  'el-form-item': { template: '<div><slot/></div>' },
  'el-select': true,
  'el-option': true,
  'el-input-number': true,
  'el-date-picker': true,
  'el-switch': true,
  'el-button': { template: '<button><slot/></button>' },
  'el-table': { template: '<div><slot/></div>' },
  'el-table-column': true,
  'el-tooltip': true,
  'el-empty': {
    template: '<div class="empty"><slot/><span>{{description}}</span></div>',
    props: ['description']
  },
  'el-alert': {
    template: '<div class="alert"><slot/><span>{{title}}</span></div>',
    props: ['title']
  },
  'el-pagination': true,
  'el-card': { template: '<div class="card"><slot/></div>' },
  'el-progress': true
}

function bizErr(code) {
  const msgs = { 50000: '服务异常，请稍后重试', 40100: '登录已失效，请重新登录' }
  const err = new Error(msgs[code])
  err.code = code
  return err
}

describe('RiskList 三态', () => {
  beforeEach(() => {
    getCommits.mockReset()
    getCommitsCoverage.mockReset().mockResolvedValue({ items: [] })
    getHealth.mockReset().mockResolvedValue({ status: 'ok', models_loaded: 3, db: 'up' })
    postSync.mockReset()
    postSyncCatchup.mockReset()
    subscribeSyncProgress.mockReset().mockReturnValue({ abort: vi.fn() })
    routeQuery = {}
  })

  it('空库：显示同步加载台（按需现算的引导，不是错误）', async () => {
    getCommits.mockResolvedValue({ items: [], total: 0 })
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('还没有数据')
    expect(wrapper.text()).toContain('开始同步')
  })

  it('空数据（带筛选）：显示空态文案（不是错误）', async () => {
    getCommits.mockResolvedValue({ items: [], total: 0 })
    routeQuery = { start_time: '2026-01-01', end_time: '2026-02-01' }
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('当前筛选条件下没有提交')
  })

  it('所选模型从未预测过：区分「模型无数据」与「筛选没命中」，并给切回默认模型', async () => {
    getCommits.mockResolvedValue({ items: [], total: 0 })
    // 库里有 xgb_v1 的预测，但没有 lr_v1 的：切到 lr_v1 时空态必须换个说法
    getCommitsCoverage.mockResolvedValue({ items: [{ model_name: 'xgb_v1', start: null, end: null }] })
    routeQuery = { model_name: 'lr_v1' }
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('模型 lr_v1 还没有任何预测数据')
    expect(wrapper.text()).toContain('切回默认模型')
    expect(wrapper.text()).not.toContain('当前筛选条件下没有提交')
  })

  it('50000 服务错误：显示「服务异常，请稍后重试」', async () => {
    getCommits.mockRejectedValue(bizErr(50000))
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('服务异常，请稍后重试')
  })

  it('40100 鉴权失败：显示「登录已失效，请重新登录」', async () => {
    getCommits.mockRejectedValue(bizErr(40100))
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('登录已失效，请重新登录')
  })
})
