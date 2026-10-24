// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RiskList from '../src/views/RiskList.vue'

const getCommits = vi.fn()

vi.mock('../src/api', () => ({
  getCommits: (...args) => getCommits(...args)
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} })
}))

const stubs = {
  'el-form': { template: '<div><slot/></div>' },
  'el-form-item': { template: '<div><slot/></div>' },
  'el-select': true,
  'el-option': true,
  'el-input-number': true,
  'el-date-picker': true,
  'el-button': { template: '<button><slot/></button>' },
  'el-table': { template: '<div><slot/></div>' },
  'el-table-column': true,
  'el-tooltip': true,
  'el-empty': { template: '<div class="empty"><slot/><span>{{description}}</span></div>', props: ['description'] },
  'el-alert': { template: '<div class="alert"><slot/><span>{{title}}</span></div>', props: ['title'] },
  'el-pagination': true
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
  })

  it('空数据：无提交显示空态文案（不是错误）', async () => {
    getCommits.mockResolvedValue({ items: [], total: 0 })
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
})
