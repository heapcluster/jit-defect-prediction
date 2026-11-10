// [AI生成-人工修改] 在原有测试基础上由 AI 补充/修改部分用例，核心断言经人工复核。
// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RiskList from '../src/views/RiskList.vue'

const getCommits = vi.fn()
const postSync = vi.fn()
const getSyncStatus = vi.fn()
const getModels = vi.fn()

vi.mock('../src/api', () => ({
  getCommits: (...args) => getCommits(...args),
  postSync: (...args) => postSync(...args),
  getSyncStatus: (...args) => getSyncStatus(...args),
  getModels: (...args) => getModels(...args)
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }
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
  'el-input': true,
  'el-date-picker': true,
  'el-button': { template: '<button @click="$emit(\'click\')"><slot/></button>' },
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
  LineModelCascade: true,
  RiskTag: true
}

function bizErr(code) {
  const msgs = { 50000: '服务异常，请稍后重试', 40100: '登录已失效，请重新登录' }
  const err = new Error(msgs[code])
  err.code = code
  return err
}

describe('RiskList 三态与刷新', () => {
  beforeEach(() => {
    getCommits.mockReset()
    postSync.mockReset()
    getSyncStatus.mockReset()
    getModels.mockReset()
    getModels.mockResolvedValue({ lines: [{ line: 'expert', label: '专家特征', models: ['lr_v1'] }] })
    routeQuery = {}
  })

  it('正常加载：渲染提交列表', async () => {
    getCommits.mockResolvedValue({
      items: [
        {
          commit_hash: 'a'.repeat(40),
          author_name: 'dev',
          committed_at: '2026-08-01T00:00:00Z',
          message: 'fix',
          risk_score: 0.8,
          model_name: 'lr_v1',
          is_bug_inducing: 1
        }
      ],
      total: 1
    })
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(getCommits).toHaveBeenCalled()
    expect(wrapper.vm.items).toHaveLength(1)
  })

  it('空数据（带筛选）：显示空态文案（不是错误）', async () => {
    getCommits.mockResolvedValue({ items: [], total: 0 })
    routeQuery = { start_time: '2026-01-01', end_time: '2026-02-01' }
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('当前筛选条件下没有提交')
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

  it('刷新：POST /api/sync 提交后立即返回，轮询 status 完成后重新查询', async () => {
    getCommits.mockResolvedValue({ items: [], total: 0 })
    postSync.mockResolvedValue({ accepted: true })
    getSyncStatus.mockResolvedValue({ running: false, total: 0, done: 0 })
    const wrapper = mount(RiskList, { global: { stubs } })
    await flushPromises()

    await wrapper.vm.refresh()
    await flushPromises()

    expect(postSync).toHaveBeenCalledTimes(1)
    expect(getSyncStatus).toHaveBeenCalled()
    // 刷新完成后按查询栏当前条件重查
    const calls = getCommits.mock.calls.length
    expect(calls).toBeGreaterThanOrEqual(2)
  })
})
